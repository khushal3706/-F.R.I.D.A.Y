"""
╔══════════════════════════════════════════════════════════════╗
║      FRIDAY — Task Planner (core/planner.py)                ║
║  Breaks a high-level goal into ordered sub-tasks and        ║
║  executes them sequentially, with retry + self-correction   ║
║  FREE STACK: uses Gemini or Ollama for plan generation      ║
╚══════════════════════════════════════════════════════════════╝
"""

import json
import re
from core.logger   import get_logger
from core.safety   import is_killed
from core.executor import execute_code, ExecutionResult

log = get_logger("Planner")


# ─────────────────────────────────────────────────────────────
# ▸ PLAN DATA STRUCTURES
# ─────────────────────────────────────────────────────────────
class Step:
    """One step inside an agent plan."""

    def __init__(self, index: int, description: str, code: str | None = None):
        self.index       = index
        self.description = description
        self.code        = code
        self.result: ExecutionResult | None = None
        self.status      = "pending"   # pending | running | done | failed

    def __repr__(self):
        return f"Step({self.index}: {self.description!r}  [{self.status}])"


class Plan:
    """Ordered sequence of Steps to achieve a goal."""

    def __init__(self, goal: str, steps: list[Step]):
        self.goal  = goal
        self.steps = steps

    def summary(self) -> str:
        icons = {"pending": "...", "running": ">>", "done": "OK", "failed": "!!"}
        lines = [f"Plan: {self.goal}", "─" * 50]
        for s in self.steps:
            icon = icons.get(s.status, "?")
            lines.append(f"  [{icon}] [{s.index+1}] {s.description}")
        return "\n".join(lines)


# ─────────────────────────────────────────────────────────────
# ▸ PLAN PROMPT
# ─────────────────────────────────────────────────────────────
_PLAN_PROMPT = """
You are FRIDAY's planning module.
Break the following high-level goal into clear, ordered sub-tasks.

Goal: {goal}

Return a JSON array of objects. Each object must have:
  - "description": a one-sentence plain-English step description
  - "code": valid Python code to accomplish this step using FRIDAY tools, or null

Available FRIDAY tools you can call in the code:
  click(x, y)  |  type_text("...")  |  press_key("ctrl","c")
  open_app("chrome")  |  focus_window("Notepad")
  open_url_in_browser("https://...")
  take_screenshot()  |  describe_screen()
  search("query")  |  search_and_summarise("query")
  generate_image("prompt")
  run_shell_command("cmd")

Return ONLY the JSON array — no explanation, no markdown fences.

Example:
[
  {{"description": "Open Chrome", "code": "open_app('chrome')"}},
  {{"description": "Navigate to google.com", "code": "open_url_in_browser('https://google.com')"}}
]
""".strip()


def _parse_plan_json(raw: str) -> list[dict]:
    """Extract a JSON array from raw LLM output, stripping markdown fences."""
    raw = re.sub(r"```(?:json)?", "", raw).strip().rstrip("`").strip()
    try:
        data = json.loads(raw)
        if isinstance(data, list):
            return data
    except json.JSONDecodeError:
        match = re.search(r"\[.*\]", raw, re.DOTALL)
        if match:
            return json.loads(match.group())
    raise ValueError(f"LLM returned invalid plan JSON:\n{raw}")


# ─────────────────────────────────────────────────────────────
# ▸ LLM DISPATCH  (Gemini or Ollama — both free)
# ─────────────────────────────────────────────────────────────
def _llm_call_raw(prompt: str, provider: str) -> str:
    """
    Make a single stateless LLM call without using the brain's memory.
    Used exclusively for plan generation to avoid contaminating chat history.
    """
    from config import SYSTEM_PROMPT, GEMINI_API_KEY, GEMINI_MODEL, OLLAMA_BASE_URL, OLLAMA_MODEL

    if provider == "gemini":
        try:
            from google import genai
            from google.genai import types
        except ImportError:
            raise ImportError("Run: pip install google-genai")

        client = genai.Client(api_key=GEMINI_API_KEY)
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                temperature=0.1,
                max_output_tokens=2048,
            ),
        )
        return response.text.strip()

    elif provider == "ollama":
        import httpx
        url = f"{OLLAMA_BASE_URL}/api/chat"
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": prompt},
        ]
        resp = httpx.post(url, json={"model": OLLAMA_MODEL, "messages": messages,
                                     "stream": False, "options": {"temperature": 0.1}},
                          timeout=120)
        resp.raise_for_status()
        return resp.json()["message"]["content"].strip()

    else:
        raise ValueError(f"Unknown provider for planner: {provider!r}")


# ─────────────────────────────────────────────────────────────
# ▸ PLANNER CLASS
# ─────────────────────────────────────────────────────────────
class Planner:
    """
    Decomposes a natural-language goal into a Plan and executes it step-by-step.

    Usage:
        planner = Planner(brain)
        plan    = planner.make_plan("Open Chrome and search for Python AI news")
        planner.execute_plan(plan, confirm=True)
    """

    def __init__(self, brain):
        self.brain = brain

    # ── Plan creation ─────────────────────────────────────────
    def make_plan(self, goal: str) -> Plan:
        """Ask the LLM to decompose `goal` into ordered executable Steps."""
        log.info(f"Creating plan for: {goal!r}")
        prompt = _PLAN_PROMPT.format(goal=goal)

        try:
            raw = _llm_call_raw(prompt, self.brain.provider)
        except Exception as exc:
            log.error(f"Plan generation failed: {exc}")
            raise

        steps_data = _parse_plan_json(raw)
        steps = [
            Step(i, d.get("description", f"Step {i+1}"), d.get("code"))
            for i, d in enumerate(steps_data)
        ]
        plan = Plan(goal=goal, steps=steps)
        log.info(f"Plan ready: {len(steps)} step(s).")
        return plan

    # ── Plan execution ─────────────────────────────────────────
    def execute_plan(
        self,
        plan: Plan,
        confirm: bool = False,
        max_retries: int = 2,
        on_step_done=None,
    ) -> bool:
        """
        Execute all Steps in a Plan sequentially.

        Args:
            plan         : The Plan to execute.
            confirm      : Require y/N approval before each code step.
            max_retries  : Retry attempts on failure before giving up.
            on_step_done : Optional callback(Step) called after each step.

        Returns:
            True if all steps succeeded.
        """
        log.info(f"Executing plan: {plan.goal!r}  ({len(plan.steps)} steps)")
        print(plan.summary())
        print()
        all_ok = True

        for step in plan.steps:
            if is_killed():
                log.warning("Kill-switch active — plan halted.")
                break

            step.status = "running"
            log.info(f"Step [{step.index+1}/{len(plan.steps)}]: {step.description}")
            print(f"\n  >> [{step.index+1}] {step.description}")

            if not step.code:
                step.status = "done"
                log.debug("Informational step — no code.")
            else:
                success = False
                for attempt in range(1, max_retries + 2):
                    result = execute_code(step.code, confirm=confirm)
                    step.result = result

                    if result.success:
                        step.status = "done"
                        if result.output:
                            print(f"     >> {result.output[:200]}")
                        success = True
                        break
                    else:
                        log.warning(f"Step {step.index+1} attempt {attempt} failed.")
                        if attempt <= max_retries:
                            step.code = self._fix_step(step, result.error)
                        else:
                            step.status = "failed"
                            all_ok = False
                            print(f"     !! Failed: {result.error[:200]}")

            if on_step_done:
                on_step_done(step)

        print()
        print(plan.summary())
        return all_ok

    # ── Self-correction ───────────────────────────────────────
    def _fix_step(self, step: Step, error: str) -> str:
        """Ask the LLM to fix broken code for a failed step."""
        log.info(f"Asking {self.brain.provider.upper()} to fix step {step.index+1} …")
        fix_prompt = (
            f"This Python code for '{step.description}' raised an error.\n\n"
            f"Code:\n```python\n{step.code}\n```\n\n"
            f"Error:\n{error}\n\n"
            "Return ONLY the corrected Python in a ```python``` block."
        )
        _, new_code = self.brain.think(fix_prompt)
        if new_code:
            log.info("Corrected code received.")
            return new_code
        log.warning("No fix received — retrying with original code.")
        return step.code

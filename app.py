import os
from pathlib import Path
import sys

# Load .env
_env_path = Path(__file__).parent / ".env"
if _env_path.exists():
    for _line in _env_path.read_text(encoding="utf-8").splitlines():
        _line = _line.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            _k, _, _v = _line.partition("=")
            os.environ.setdefault(_k.strip(), _v.strip().strip('"').strip("'"))

from flask import Flask, render_template
from flask_socketio import SocketIO, emit
from core.llm_brain import FridayBrain
from core.executor import execute_code
import mimetypes

# Fix for Windows MIME type issue with CSS
mimetypes.add_type('text/css', '.css')

app = Flask(__name__)
app.config['SECRET_KEY'] = 'friday-secret!'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# Initialize the AI Brain
brain = FridayBrain()

@app.route('/')
def index():
    return render_template('index.html')

@socketio.on('user_message')
def handle_user_message(data):
    user_text = data.get('text', '')
    if not user_text:
        return
        
    print(f"User said: {user_text}")
    emit('status', {'msg': 'Thinking...'})
    
    try:
        reply, code = brain.think(user_text)
        
        emit('bot_message', {'text': reply, 'code': code})
        
        if code:
            emit('status', {'msg': 'Executing code...'})
            result = execute_code(code, confirm=False) # Auto-execute for web UI demo
            
            output_msg = ""
            if result.output:
                output_msg += f"Output:\n{result.output}\n"
            if result.error:
                output_msg += f"Error:\n{result.error}\n"
                brain.inject_context(f"The code raised an error:\n{result.error}\nPlease correct it.")
                
            if output_msg:
                emit('execution_result', {'output': output_msg})
                
    except Exception as e:
        emit('error', {'msg': str(e)})

    emit('status', {'msg': 'Online | Standing by'})

if __name__ == '__main__':
    print("Starting FRIDAY Web App on http://127.0.0.1:5000")
    socketio.run(app, debug=True, port=5000, allow_unsafe_werkzeug=True)

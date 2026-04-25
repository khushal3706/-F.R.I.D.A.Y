document.addEventListener('DOMContentLoaded', () => {
    const socket = io();
    const chatContainer = document.getElementById('chat-container');
    const textInput = document.getElementById('text-input');
    const sendBtn = document.getElementById('send-btn');
    const micBtn = document.getElementById('mic-btn');
    const statusText = document.getElementById('status-text');

    let isListening = false;
    let recognition = null;
    let synth = window.speechSynthesis;

    // Initialize Speech Recognition
    if ('webkitSpeechRecognition' in window) {
        recognition = new webkitSpeechRecognition();
        recognition.continuous = true; // Stay active to allow 'always listening'
        recognition.interimResults = false;
        recognition.lang = 'en-US';

        recognition.onstart = () => {
            isListening = true;
            micBtn.classList.add('listening');
            statusText.innerText = 'Status: Listening...';
        };

        recognition.onresult = (event) => {
            let finalTranscript = '';
            for (let i = event.resultIndex; i < event.results.length; ++i) {
                if (event.results[i].isFinal) {
                    finalTranscript += event.results[i][0].transcript;
                }
            }
            if (finalTranscript.trim()) {
                appendMessage(finalTranscript, 'user-msg');
                socket.emit('user_message', { text: finalTranscript });
            }
        };

        recognition.onerror = (event) => {
            console.error('Speech recognition error', event.error);
            if (event.error === 'not-allowed') {
                statusText.innerText = 'Status: Microphone access denied';
                stopListening();
            }
        };

        recognition.onend = () => {
            if (isListening) {
                // Auto restart for always listening feel, unless manually stopped
                try {
                    recognition.start();
                } catch(e) {
                    isListening = false;
                    micBtn.classList.remove('listening');
                    statusText.innerText = 'Status: Online | Standing by';
                }
            } else {
                micBtn.classList.remove('listening');
                statusText.innerText = 'Status: Online | Standing by';
            }
        };
    } else {
        statusText.innerText = 'Status: Speech recognition not supported';
        micBtn.style.display = 'none';
    }

    function toggleListening() {
        if (!recognition) return;
        if (isListening) {
            stopListening();
        } else {
            recognition.start();
        }
    }

    function stopListening() {
        isListening = false;
        recognition.stop();
        micBtn.classList.remove('listening');
        statusText.innerText = 'Status: Online | Standing by';
    }

    micBtn.addEventListener('click', toggleListening);

    function sendMessage() {
        const text = textInput.value.trim();
        if (text) {
            appendMessage(text, 'user-msg');
            socket.emit('user_message', { text: text });
            textInput.value = '';
        }
    }

    sendBtn.addEventListener('click', sendMessage);
    textInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') sendMessage();
    });

    socket.on('connect', () => {
        statusText.innerText = 'Status: Online | Connected to Core';
    });

    socket.on('disconnect', () => {
        statusText.innerText = 'Status: Offline | Core Unreachable';
    });

    socket.on('status', (data) => {
        statusText.innerText = `Status: ${data.msg}`;
    });

    socket.on('bot_message', (data) => {
        // Strip markdown code blocks from speech output
        let speechText = data.text.replace(/```[\s\S]*?```/g, '');
        speakText(speechText);

        let htmlContent = `<p>${data.text.replace(/\n/g, '<br>')}</p>`;
        if (data.code) {
            htmlContent += `<pre><code>${escapeHtml(data.code)}</code></pre>`;
        }
        
        appendMessageHTML(htmlContent, 'bot-msg');
    });

    socket.on('execution_result', (data) => {
        const resultDiv = document.createElement('div');
        resultDiv.className = 'execution-output';
        resultDiv.innerText = data.output;
        
        // Find last bot message and append result there
        const messages = document.querySelectorAll('.bot-msg');
        if (messages.length > 0) {
            messages[messages.length - 1].appendChild(resultDiv);
        } else {
            chatContainer.appendChild(resultDiv);
        }
        scrollToBottom();
    });

    socket.on('error', (data) => {
        appendMessage(`Error: ${data.msg}`, 'system-msg');
    });

    function appendMessage(text, className) {
        const div = document.createElement('div');
        div.className = `message ${className}`;
        div.innerText = text;
        chatContainer.appendChild(div);
        scrollToBottom();
    }
    
    function appendMessageHTML(html, className) {
        const div = document.createElement('div');
        div.className = `message ${className}`;
        div.innerHTML = html;
        chatContainer.appendChild(div);
        scrollToBottom();
    }

    function scrollToBottom() {
        chatContainer.scrollTop = chatContainer.scrollHeight;
    }

    function escapeHtml(unsafe) {
        return unsafe
             .replace(/&/g, "&amp;")
             .replace(/</g, "&lt;")
             .replace(/>/g, "&gt;")
             .replace(/"/g, "&quot;")
             .replace(/'/g, "&#039;");
    }

    function speakText(text) {
        if (!synth) return;
        synth.cancel(); // cancel current speech
        
        // Basic cleanup for speech
        let cleanText = text.replace(/[*_~`#]/g, ''); 

        const utterance = new SpeechSynthesisUtterance(cleanText);
        
        let voices = synth.getVoices();
        let selectedVoice = null;
        
        for (let i = 0; i < voices.length; i++) {
            if (voices[i].name.includes('Zira') || voices[i].name.includes('Female')) {
                selectedVoice = voices[i];
                break;
            }
        }
        
        if (selectedVoice) {
            utterance.voice = selectedVoice;
        }
        
        utterance.rate = 1.05;
        utterance.pitch = 1.0;
        
        // Pause listening while speaking to prevent echo
        if (isListening && recognition) {
            recognition.stop();
            utterance.onend = () => {
                if (isListening) recognition.start();
            };
        }
        
        synth.speak(utterance);
    }
    
    // Initial voice load workaround for Chrome
    if (speechSynthesis.onvoiceschanged !== undefined) {
      speechSynthesis.onvoiceschanged = () => synth.getVoices();
    }
});

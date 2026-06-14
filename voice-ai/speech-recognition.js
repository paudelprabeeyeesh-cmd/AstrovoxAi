// ============================================
// PRABESH PAUDEL — VOICE AI SYSTEMS
// Voice AI Developer | Speech Recognition
// ============================================

class VoiceAISystem {
    constructor() {
        this.recognition = null;
        this.synthesis = window.speechSynthesis;
        this.isListening = false;
        this.isSpeaking = false;
        this.init();
    }
    
    init() {
        if ('webkitSpeechRecognition' in window) {
            this.recognition = new webkitSpeechRecognition();
            this.recognition.continuous = false;
            this.recognition.interimResults = true;
            this.recognition.lang = 'en-US';
            
            this.recognition.onstart = () => {
                this.isListening = true;
                this.updateUI(true);
                console.log('🎤 Listening...');
            };
            
            this.recognition.onresult = (event) => {
                const result = event.results[event.results.length - 1];
                const text = result[0].transcript;
                const isFinal = result.isFinal;
                
                if (isFinal) {
                    document.getElementById('chat-input').value = text;
                    window.chat?.sendMessage();
                    this.stopListening();
                } else {
                    document.getElementById('chat-input').value = text;
                }
            };
            
            this.recognition.onerror = (event) => {
                console.error('Voice error:', event.error);
                this.stopListening();
            };
            
            this.recognition.onend = () => {
                this.stopListening();
            };
        }
    }
    
    startListening() {
        if (this.recognition && !this.isListening) {
            this.recognition.start();
        }
    }
    
    stopListening() {
        if (this.recognition && this.isListening) {
            this.recognition.stop();
        }
        this.isListening = false;
        this.updateUI(false);
    }
    
    speak(text) {
        if (!this.synthesis) return;
        
        this.synthesis.cancel();
        
        const utterance = new SpeechSynthesisUtterance(text);
        utterance.rate = 0.9;
        utterance.pitch = 1.0;
        
        utterance.onstart = () => {
            this.isSpeaking = true;
        };
        
        utterance.onend = () => {
            this.isSpeaking = false;
        };
        
        this.synthesis.speak(utterance);
    }
    
    updateUI(isListening) {
        const voiceBtn = document.getElementById('voice-btn');
        if (voiceBtn) {
            if (isListening) {
                voiceBtn.classList.add('active');
                voiceBtn.style.background = 'linear-gradient(135deg, #FF007F, #9B51E0)';
            } else {
                voiceBtn.classList.remove('active');
                voiceBtn.style.background = '';
            }
        }
    }
    
    toggle() {
        if (this.isListening) {
            this.stopListening();
        } else {
            this.startListening();
        }
    }
}

window.voiceAI = new VoiceAISystem();
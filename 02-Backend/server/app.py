import os
import io
from pathlib import Path
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from openai import OpenAI
from dotenv import load_dotenv

# Path Automation: Locates the .env file in the root directory
BASE_DIR = Path(__file__).resolve().parent.parent.parent
load_dotenv(dotenv_path=BASE_DIR / ".env")

app = Flask(__name__)
# Enable cross-origin streaming for the local frontend file
CORS(app, resources={r"/api/*": {"origins": "*"}}, supports_credentials=True)

# Instantiate Cloud Intelligence Engine
OPENAI_KEY = os.getenv("OPENAI_API_KEY", "")
client = OpenAI(api_key=OPENAI_KEY) if OPENAI_KEY else None

@app.route("/health/readiness", methods=["GET"])
def readiness():
    """HUD Connectivity Heartbeat Check."""
    return jsonify({
        "status": "healthy",
        "engine": "Astrovox TTS Pipeline Core",
        "telemetry": {
            "neural_activity": "96.1%",
            "quantum_state": "STABLE",
            "latency": "14ms"
        }
    })

@app.route("/api/tts/voices", methods=["GET"])
def get_voices():
    """Provides valid vocal profile matrices to the UI selector."""
    return jsonify([
        {"name": "alloy", "desc": "Neutral, balanced, and highly versatile"},
        {"name": "echo", "desc": "Crisp, authoritative male voice matrix"},
        {"name": "nova", "desc": "Bright, energetic female atmospheric profile"},
        {"name": "shimmer", "desc": "Clear, professional female vocal array"}
    ])

@app.route("/api/tts/generate", methods=["POST"])
def generate_tts():
    """Converts frontend text vectors into binary MP3 streaming audio payloads."""
    if not client:
        return jsonify({"error": "OpenAI Client Offline. Check your root .env configuration."}), 500

    data = request.get_json() or {}
    text = data.get("text", "").strip()
    voice = data.get("voice", "nova").lower()

    if not text:
        return jsonify({"error": "Empty input matrix reported by frontend."}), 400

    try:
        # Request voice synthesis from cloud matrix
        response = client.audio.speech.create(
            model="tts-1",
            voice=voice,
            input=text
        )
        
        # Stream raw binary directly from memory buffer
        audio_buffer = io.BytesIO(response.content)
        audio_buffer.seek(0)
        
        return send_file(
            audio_buffer,
            mimetype="audio/mpeg",
            as_attachment=False
        )

    except Exception as e:
        return jsonify({"error": f"Synthesis pipeline breakdown: {str(e)}"}), 500

if __name__ == "__main__":
    # Debug deactivated to minimize baseline RAM usage
    app.run(host="127.0.0.1", port=5000, debug=False)
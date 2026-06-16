import os
import io
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from openai import OpenAI
from dotenv import load_dotenv

# Load environmental configs
load_dotenv()

app = Flask(__name__)
# Enable CORS so your local 01-Frontend files can stream audio safely
CORS(app, resources={r"/api/*": {"origins": "*"}})

# Initialize OpenAI Client
OPENAI_KEY = os.getenv("OPENAI_API_KEY", "")
client = OpenAI(api_key=OPENAI_KEY) if OPENAI_KEY else None

@app.route("/health/readiness", methods=["GET"])
def readiness():
    """HUD Heartbeat check."""
    return jsonify({
        "status": "healthy",
        "engine": "Flask TTS Core",
        "telemetry": {
            "neural_activity": "96.1%",
            "latency": "14ms",
            "quantum_state": "STABLE"
        }
    })

@app.route("/api/tts/voices", methods=["GET"])
def get_voices():
    """Returns available high-fidelity vocal profiles."""
    return jsonify([
        {"name": "alloy", "gender": "neutral", "desc": "Balanced and versatile"},
        {"name": "echo", "gender": "male", "desc": "Crisp and authoritative"},
        {"name": "nova", "gender": "female", "desc": "Energetic and bright"},
        {"name": "shimmer", "gender": "female", "desc": "Professional and clear"}
    ])

@app.route("/api/tts/generate", methods=["POST"])
def generate_tts():
    """Converts cockpit instructions into live audio telemetry streams."""
    if not client:
        return jsonify({"error": "OpenAI client offline. Please configure your OPENAI_API_KEY."}), 500

    data = request.get_json() or {}
    text = data.get("text", "").strip()
    voice = data.get("voice", "nova").lower()

    if not text:
        return jsonify({"error": "Vocal transmission input buffer empty."}), 400

    try:
        # Request binary audio generation from OpenAI TTS Engine
        response = client.audio.speech.create(
            model="tts-1",
            voice=voice,
            input=text
        )
        
        # Read the raw byte data into memory
        audio_buffer = io.BytesIO(response.content)
        audio_buffer.seek(0)
        
        return send_file(
            audio_buffer,
            mimetype="audio/mpeg",
            as_attachment=False,
            download_name="transmission.mp3"
        )

    except Exception as e:
        return jsonify({"error": f"Vocal synthesis matrix failed: {str(e)}"}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
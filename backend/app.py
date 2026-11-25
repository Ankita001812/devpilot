
from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import os

app = Flask(__name__)
CORS(app)

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "llama3.2:3b"


@app.route("/health", methods=["GET"])
def health():
    return jsonify({
        "status": "DevPilot backend is running"
    })


@app.route("/analyze", methods=["POST"])
def analyze():
    data = request.get_json()

    if not data:
        return jsonify({"error": "Request body is required"}), 400

    code = data.get("code", "")
    mode = data.get("mode", "explain")

    if not code.strip():
        return jsonify({"error": "Please provide some code"}), 400

    prompt = f"""
    You are DevPilot, a helpful programming assistant.

    Task: {mode}

    Explain your answer in simple words.

    Code:
    {code}
    """

    try:
        response = requests.post(
            OLLAMA_URL,
            json={
                "model": MODEL,
                "prompt": prompt,
                "stream": False
            },
            timeout=180
        )

        response.raise_for_status()

        result = response.json()["response"]

        return jsonify({
            "result": result
        })

    except requests.RequestException as error:
        return jsonify({
            "error": f"Could not connect to Ollama: {error}"
        }), 502


if __name__ == "__main__":
    app.run(port=5001, debug=True)

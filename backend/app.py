
# from flask import Flask, request, jsonify
# from flask_cors import CORS
# import requests
# import os

# app = Flask(__name__)
# CORS(app)

# OLLAMA_URL = "http://localhost:11434/api/generate"
# MODEL = "llama3.2:3b"


# @app.route("/health", methods=["GET"])
# def health():
#     return jsonify({
#         "status": "DevPilot backend is running"
#     })


# @app.route("/analyze", methods=["POST"])
# def analyze():
#     data = request.get_json()

#     if not data:
#         return jsonify({"error": "Request body is required"}), 400

#     code = data.get("code", "")
#     mode = data.get("mode", "explain")

#     if not code.strip():
#         return jsonify({"error": "Please provide some code"}), 400

#     prompt = f"""
#     You are DevPilot, a helpful programming assistant.

#     Task: {mode}

#     Explain your answer in simple words.

#     Code:
#     {code}
#     """

#     try:
#         response = requests.post(
#             OLLAMA_URL,
#             json={
#                 "model": MODEL,
#                 "prompt": prompt,
#                 "stream": False
#             },
#             timeout=180
#         )

#         response.raise_for_status()

#         result = response.json()["response"]

#         return jsonify({
#             "result": result
#         })

#     except requests.RequestException as error:
#         return jsonify({
#             "error": f"Could not connect to Ollama: {error}"
#         }), 502


# if __name__ == "__main__":
#     app.run(port=5001, debug=True)


import os, re, requests
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434/api/generate")
MODEL = os.getenv("MODEL", "llama3.2:3b")
MOCK = os.getenv("MOCK", "0") == "1"

PROMPTS = {
    "explain": "Explain this Python code line by line in very simple English:\n{code}",
    "debug": "Find the root cause of this problem. Be short.\nCode:\n{code}\nErrors:\n{error}",
    "fix": "Return ONLY the full corrected Python code. No markdown, no talk.\nCode:\n{code}\nErrors:\n{error}",
    "tests": "Write pytest unit tests for this code. Return only code.\n{code}",
    "improve": "Suggest a cleaner, more maintainable version and say why:\n{code}",
}

def ask_llm(prompt):
    if MOCK:
        return "MOCK ANSWER for: " + prompt[:60]
    r = requests.post(OLLAMA_URL,
                      json={"model": MODEL, "prompt": prompt, "stream": False},
                      timeout=120)
    r.raise_for_status()
    return r.json()["response"]

def strip_fences(text):
    return re.sub(r"^```\w*\n|\n```$", "", text.strip())

@app.post("/analyze")
def analyze():
    data = request.get_json(silent=True) or {}
    mode = data.get("mode")
    code = (data.get("code") or "").strip()
    if mode not in PROMPTS or not code:
        return jsonify(error="Need a valid mode and some code"), 400
    if len(code) > 8000:
        return jsonify(error="Code too long (max 8000 characters)"), 413
    prompt = PROMPTS[mode].format(code=code, error=data.get("error", ""))
    try:
        result = ask_llm(prompt)
    except Exception as e:
        return jsonify(error="AI failed: " + str(e)), 502
    if mode in ("fix", "tests"):
        result = strip_fences(result)
    return jsonify(result=result)

if __name__ == "__main__":
    app.run(port=5001, debug=True)
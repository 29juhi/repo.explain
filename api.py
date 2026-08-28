"""Local API for explaining repository files."""

from flask import Flask, jsonify, request
from flask_cors import CORS

from llm_explainer import explain_chunk


app = Flask(__name__)
CORS(app)


@app.post("/api/explain")
def explain_file():
    payload = request.get_json(silent=True) or {}
    code = payload.get("code", "")
    file_path = payload.get("file_path", "source file")
    if not isinstance(code, str) or not code.strip():
        return jsonify({"error": "File code is required."}), 400

    explanation = explain_chunk(code, chunk_type=f"source file ({file_path})")
    if explanation.startswith("Error:"):
        return jsonify({"error": explanation}), 502
    return jsonify({"explanation": explanation})


if __name__ == "__main__":
    app.run(port=5000, debug=True)

"""Generate concise code explanations with Hugging Face Inference API."""

from __future__ import annotations

import os
from argparse import ArgumentParser
from pathlib import Path

from dotenv import load_dotenv
from huggingface_hub import InferenceClient


MODEL_ID = "Qwen/Qwen2.5-Coder-7B-Instruct"
load_dotenv()
HF_API_KEY = os.getenv("HF_API_KEY")
client = InferenceClient(model=MODEL_ID, token=HF_API_KEY)


def _error_message(error: Exception) -> str:
    """Convert common API failures into a useful message for the caller."""
    message = str(error).lower()
    if "auth" in message or "token" in message or "401" in message or "403" in message:
        return "Error: Hugging Face authentication failed. Check HF_API_KEY in .env."
    if "timeout" in message or "timed out" in message:
        return "Error: Hugging Face request timed out. Please try again."
    if "rate" in message or "429" in message:
        return "Error: Hugging Face rate limit reached. Please try again later."
    if "model_not_supported" in message or "not supported by any provider" in message:
        return (
            "Error: This model is not deployed by any Hugging Face Inference Provider. "
            "Use a provider-supported model, run it locally with Transformers/vLLM, "
            "or use the DeepSeek API."
        )
    return f"Error: Hugging Face API call failed: {error}"


def explain_chunk(code: str, chunk_type: str = "function") -> str:
    """Explain a code chunk in two or three short bullet points."""
    if not HF_API_KEY:
        return "Error: HF_API_KEY is missing. Add it to your .env file."

    prompt = f"""Explain this {chunk_type} in exactly 2-3 short bullet points.
Use bullet points only, with no paragraphs. Focus on what it does, its inputs, and its outputs.

Code:
```python
{code}
```"""
    try:
        response = client.chat_completion(
            messages=[
                {"role": "system", "content": "You explain code clearly and concisely."},
                {"role": "user", "content": prompt},
            ],
            max_tokens=150,
            temperature=0.2,
        )
        return response.choices[0].message.content.strip()
    except Exception as error:
        return _error_message(error)


def get_file_context(chunks: list[dict[str, str]]) -> str:
    """Build compact file context from extracted code chunks."""
    lines = []
    for chunk in chunks:
        code = chunk.get("code", "").splitlines()
        if code:
            lines.append(code[0])
        for line in code[1:]:
            stripped = line.strip()
            if stripped.startswith(('"""', "'''")):
                lines.append(stripped)
                break
    return "\n".join(lines)


def summarize_file(function_names: list[str], file_context: str) -> str:
    """Summarize a file's overall purpose using a fixed template."""
    if not HF_API_KEY:
        return "Error: HF_API_KEY is missing. Add it to your .env file."

    functions = ", ".join(function_names) if function_names else "No named functions found"
    prompt = f"""You are documenting a code file for another developer.

Functions in this file: {functions}

File context:
{file_context}


Fill in this exact template with your answer, nothing else:

Purpose: <one line, what this file is for>
Key functions: <one line, which functions matter most and why>
Used by: <one line, how/where this file likely gets used, or "Unclear from file alone" if you can't tell>
"""
    try:
        response = client.chat_completion(
            messages=[{"role": "user", "content": prompt}],
            max_tokens=120,
            temperature=0.2,
        )
        return response.choices[0].message.content.strip()
    except Exception as error:
        return _error_message(error)


if __name__ == "__main__":
    parser = ArgumentParser(description="Explain a source file with Hugging Face.")
    parser.add_argument("file", nargs="?", help="Path to the source file to explain")
    args = parser.parse_args()
    raw_path = args.file or input("Enter the path to a source file: ").strip()
    file_path = Path(raw_path.strip().strip('"').strip("'")).expanduser()

    try:
        file_code = file_path.read_text(encoding="utf-8")
        print(explain_chunk(file_code, chunk_type="file"))
    except FileNotFoundError:
        print(f"Error: File not found: {file_path}")
    except IsADirectoryError:
        print(f"Error: Please provide a file path, not a directory: {file_path}")
    except UnicodeDecodeError:
        print(f"Error: Could not read {file_path} as a UTF-8 text file.")
    except OSError as error:
        print(f"Error: Could not read file: {error}")
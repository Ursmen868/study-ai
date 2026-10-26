
import os
import json
from pathlib import Path
from flask import Flask, render_template, request, jsonify
from openai import OpenAI

app = Flask(__name__)
BASE = Path(__file__).resolve().parent
DATA = BASE / "data"
DATA.mkdir(exist_ok=True)

SUBJECTS = {
    "Science": [
        "Physics", "Chemistry", "Mathematics", "Biology",
        "Computer Science", "English"
    ],
    "Commerce": [
        "Accountancy", "Business Studies", "Economics",
        "Mathematics", "English", "Informatics Practices"
    ],
    "Arts": [
        "History", "Geography", "Political Science", "Psychology",
        "Sociology", "Economics", "English"
    ]
}

MODES = {
    "tutor": "Explain the topic clearly, step by step, with examples.",
    "short": "Give a concise CBSE-style exam answer with key points.",
    "notes": "Create organised chapter notes with headings and definitions.",
    "quiz": "Create 5 multiple-choice questions, options, answers and explanations.",
    "solve": "Solve the supplied academic question step by step and verify the result.",
    "revision": "Create a revision sheet with key facts and practice questions.",
    "exam": "Give a model answer suitable for a CBSE Class 12 exam. Mention marks if supplied."
}

def load_saved():
    path = DATA / "saved.json"
    if not path.exists():
        return []
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return []

def save_items(items):
    (DATA / "saved.json").write_text(
        json.dumps(items[-100:], ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

@app.get("/")
def home():
    return render_template("index.html", subjects=SUBJECTS)

@app.get("/api/saved")
def saved():
    return jsonify(load_saved())

@app.post("/api/save")
def save():
    data = request.get_json(silent=True) or {}
    question = str(data.get("question", "")).strip()[:2000]
    answer = str(data.get("answer", "")).strip()[:12000]
    if not question or not answer:
        return jsonify(error="Nothing to save."), 400

    items = load_saved()
    items.append({"question": question, "answer": answer})
    save_items(items)
    return jsonify(ok=True)

@app.post("/api/ask")
def ask():
    if not os.environ.get("OPENAI_API_KEY"):
        return jsonify(error="API key missing. Set OPENAI_API_KEY in Termux."), 503

    data = request.get_json(silent=True) or {}
    stream = str(data.get("stream", "Science"))
    subject = str(data.get("subject", ""))
    mode = str(data.get("mode", "tutor"))
    language = str(data.get("language", "English"))
    question = str(data.get("question", "")).strip()[:6000]
    chapter = str(data.get("chapter", "")).strip()[:200]

    if stream not in SUBJECTS:
        return jsonify(error="Please choose a valid stream."), 400
    if subject not in SUBJECTS[stream]:
        return jsonify(error="Please choose a subject for your stream."), 400
    if mode not in MODES:
        return jsonify(error="Please choose a valid study mode."), 400
    if language not in ("English", "Marathi", "English and Marathi"):
        return jsonify(error="Please choose a valid language."), 400
    if not question:
        return jsonify(error="Enter a question or topic first."), 400

    instructions = f"""
You are Study AI, a patient tutor for CBSE Class 12 students.
Stream: {stream}
Subject: {subject}
Chapter or topic: {chapter or "Not specified"}
Answer language: {language}
Task: {MODES[mode]}

Teach accurately at the appropriate school level.
Use clear headings and examples when helpful.
For calculations, show working and units.
Never invent textbook quotations or claim an answer is official.
If information is uncertain, say so.
If the user asks for bilingual answers, explain in English and Marathi.
Use readable plain text and numbered lists where helpful.
"""

    try:
        client = OpenAI()
        response = client.responses.create(
            model=os.environ.get("OPENAI_MODEL", "gpt-5.5"),
            instructions=instructions,
            input=question,
            max_output_tokens=1800
        )
        answer = response.output_text.strip()
        if not answer:
            return jsonify(error="The AI returned an empty answer. Try again."), 502
        return jsonify(answer=answer)
    except Exception as exc:
        # Avoid sending secrets or full internal exception details to the browser.
        print("AI request failed:", type(exc).__name__)
        return jsonify(
            error="AI request failed. Check your internet, API key, model access, and API billing."
        ), 502

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8000, debug=False)

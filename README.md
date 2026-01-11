<!-- filepath: /f:/eval/agents/README.md -->

# PDF Analyzer (Groq + Flask)

A simple Flask web app that lets you upload a PDF and ask questions about it.  
It extracts text from the PDF, chunks it, retrieves the most relevant chunks, and sends only that context to a Groq-hosted LLM to generate an answer.

## Features
- Upload a PDF from the browser
- Ask questions on a chat-like page
- Lightweight local retriever (`vector_store.py`) using cosine similarity over token counts
- Groq LLM integration (`groq_qa_agent.py`)
- Avoids storing large text in cookies by persisting extracted text to `uploads/*.txt`
- Debug endpoint to inspect the current session state: `/debug/session` (disable in production)

---

## Project structure
- `app.py` — Flask web server (upload + chat + ask routes)
- `templates/` — HTML templates (`upload.html`, `chat.html`)
- `static/styles.css` — UI styles
- `document_loader.py` — PDF text extraction using `PyPDF2`
- `vector_store.py` — simple chunking + similarity retriever
- `groq_qa_agent.py` — Groq client + retrieval augmentation
- `requirements.txt` — dependencies

---

## Requirements
- Python 3.10+ recommended
- A Groq API key

Install dependencies:
```bash
pip install -r requirements.txt

Notes:

GROQ_API_KEY is required.
FLASK_SECRET_KEY should be set for production so sessions are stable.

Run the web app
python app.py
Workflow:

Upload a .pdf
You will be redirected to /chat
Ask questions using the input box
To reset session state:

Hit /reset (also available as a button in the UI)
Run the CLI (optional)
There is also a simple CLI runner:

It prompts for a PDF path, then you can ask questions in the terminal.

Troubleshooting
1) Upload “works” but chat redirects back to upload
If Flask session cookies get too large, the browser may ignore them.
This project avoids that by NOT storing extracted PDF text in the session cookie and instead storing it in uploads/<file>.txt.

If you reintroduced storing large text in session[...], you will see warnings like:

The 'session' cookie is too large ...

2) “Couldn't extract text from this PDF”
PyPDF2 can only extract real text, not images. Common cases where extraction returns empty:

scanned PDFs (image-only)
some protected/encrypted PDFs
unusual encodings
Fix:

Use OCR (e.g., Tesseract) and replace document_loader.py with an OCR-based extractor.
3) Model errors / decommissioned model
groq_qa_agent.py tries multiple model candidates. If one is not available, it falls back to others.

You can set:

GROQ_MODEL to a known working model in your Groq account.
Security / repo hygiene
This repo ignores:

.env (API keys)
uploads/ (uploaded PDFs and extracted text)
OS/editor junk
Check .gitignore before pushing.

check the work at link : https://www.loom.com/share/395cae40bd844351816d08b152f0573d

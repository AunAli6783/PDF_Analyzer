import os
from pathlib import Path
from flask import Flask, render_template, request, redirect, url_for, session
import uuid
import logging

from dotenv import load_dotenv
from document_loader import load_pdf
from vector_store import create_vector_store
from groq_qa_agent import create_qa_agent

UPLOAD_DIR = Path("uploads")
ALLOWED_EXTENSIONS = {".pdf"}

def _is_allowed(filename: str) -> bool:
    return Path(filename).suffix.lower() in ALLOWED_EXTENSIONS

def _ensure_upload_dir() -> None:
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# Use the same extractor everywhere (PyPDF2 via document_loader.load_pdf)
def extract_pdf_text(pdf_path: Path) -> str:
    try:
        return (load_pdf(str(pdf_path)) or "").strip()
    except Exception:
        return ""

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "dev-secret-change-me")

# NEW: basic logging (prints to console)
logging.basicConfig(level=logging.INFO)
log = logging.getLogger("pdf-qa")

def _ensure_groq_key():
    if not os.getenv("GROQ_API_KEY"):
        raise RuntimeError("Missing GROQ_API_KEY. Set it in environment or .env.")

@app.after_request
def add_no_cache_headers(resp):
    # Prevent browser/proxy from serving a cached /chat page after a new upload
    resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    resp.headers["Pragma"] = "no-cache"
    resp.headers["Expires"] = "0"
    return resp

@app.route("/", methods=["GET", "POST"])
def upload():
    if request.method == "POST":
        _ensure_upload_dir()

        if "pdf" not in request.files:
            return render_template("upload.html", error="No file field named 'pdf'.")

        f = request.files["pdf"]
        if not f or f.filename is None or f.filename.strip() == "":
            return render_template("upload.html", error="No file selected.")

        if not _is_allowed(f.filename):
            return render_template("upload.html", error="Please upload a .pdf file.")

        original_name = os.path.basename(f.filename)
        unique_name = f"{Path(original_name).stem}_{uuid.uuid4().hex}{Path(original_name).suffix.lower()}"
        save_path = UPLOAD_DIR / unique_name

        try:
            # Log what we received (size may be None depending on server/client)
            log.info("UPLOAD: original_name=%s content_type=%s content_length=%s",
                     original_name, getattr(f, "content_type", None), request.content_length)

            # Save
            f.save(save_path)
            saved_bytes = save_path.stat().st_size if save_path.exists() else -1
            log.info("UPLOAD: saved_path=%s saved_bytes=%s", str(save_path), saved_bytes)

            if saved_bytes <= 0:
                return render_template(
                    "upload.html",
                    error="Upload saved 0 bytes. The request may be blocked or file too large.",
                )

            # Force app to use THIS pdf going forward (store only small values in session)
            session["pdf_path"] = str(save_path)
            session["pdf_name"] = original_name

            session.pop("messages", None)
            session.pop("last_q", None)
            session.pop("last_a", None)

            # Extract and persist to disk (DON'T put in session cookie)
            extracted = extract_pdf_text(save_path)
            txt_path = save_path.with_suffix(".txt")
            txt_path.write_text(extracted or "", encoding="utf-8", errors="ignore")
            session["txt_path"] = str(txt_path)
            log.info("UPLOAD: txt_path=%s txt_chars=%s", str(txt_path), len(extracted or ""))

            return redirect(url_for("chat", v=uuid.uuid4().hex))

        except Exception as e:
            log.exception("UPLOAD FAILED: %s", e)
            # show a readable error in the UI so you can report it back
            return render_template("upload.html", error=f"Upload failed: {type(e).__name__}: {e}"), 500

    return render_template("upload.html")

# NEW: debug helper to see what server stored in session (don’t expose in production)
@app.get("/debug/session")
def debug_session():
    return {
        "pdf_name": session.get("pdf_name"),
        "pdf_path": session.get("pdf_path"),
        "txt_path": session.get("txt_path"),
        "last_q": session.get("last_q"),
    }

@app.route("/reset")
def reset():
    session.pop("pdf_path", None)
    session.pop("pdf_name", None)
    session.pop("pdf_text", None)
    session.pop("messages", None)
    return redirect(url_for("upload"))

@app.route("/chat")
def chat():
    pdf_path = session.get("pdf_path")
    if not pdf_path:
        return redirect(url_for("upload"))

    pdf_name = session.get("pdf_name") or os.path.basename(str(pdf_path))
    return render_template("chat.html", pdf_name=pdf_name)

# NEW: if someone navigates to /ask in the browser, send them to /chat
@app.get("/ask")
def ask_get():
    return redirect(url_for("chat"))

@app.post("/ask")
def ask():
    _ensure_groq_key()

    # If no PDF was uploaded in this session, then go to upload
    pdf_path = session.get("pdf_path")
    if not pdf_path:
        return redirect(url_for("upload"))

    # Load extracted text from disk (not from session)
    txt_path = session.get("txt_path")
    text = ""
    if txt_path and os.path.exists(txt_path):
        text = Path(txt_path).read_text(encoding="utf-8", errors="ignore").strip()
    else:
        # fallback: extract again and persist
        extracted = extract_pdf_text(Path(pdf_path))
        txt_path2 = Path(pdf_path).with_suffix(".txt")
        txt_path2.write_text(extracted or "", encoding="utf-8", errors="ignore")
        session["txt_path"] = str(txt_path2)
        text = (extracted or "").strip()

    # If extraction still produced nothing, stay on chat with an error (don't redirect)
    if not text:
        return (
            render_template(
                "chat.html",
                pdf_name=session.get("pdf_name") or os.path.basename(str(pdf_path)),
                error="Couldn't extract text from this PDF. Try a different PDF or add OCR/text extraction.",
            ),
            400,
        )

    question = (request.form.get("question") or "").strip()
    if not question:
        return (
            render_template(
                "chat.html",
                pdf_name=session.get("pdf_name") or os.path.basename(str(pdf_path)),
                error="Enter a question.",
            ),
            400,
        )

    vector_store = create_vector_store([text])
    qa = create_qa_agent(vector_store)
    answer = qa(question)

    session["last_q"] = question
    session["last_a"] = answer

    return render_template(
        "chat.html",
        pdf_name=session.get("pdf_name") or os.path.basename(str(pdf_path)),
        question=question,
        answer=answer,
    )

if __name__ == "__main__":
    app.run(host=os.getenv("HOST", "127.0.0.1"), port=int(os.getenv("PORT", "5000")), debug=True)
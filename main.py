import os
from dotenv import load_dotenv

from document_loader import load_pdf
from vector_store import create_vector_store
from groq_qa_agent import create_qa_agent

load_dotenv()

def _prompt_pdf_path(default_path: str) -> str:
    while True:
        user_in = input(f"Enter PDF file path [{default_path}]: ").strip().strip('"')
        path = user_in or default_path
        if os.path.isfile(path):
            return path
        print("Invalid path. Please enter a valid PDF file path.")

def main():
    if not os.getenv("GROQ_API_KEY"):
        raise ValueError("Please set the GROQ_API_KEY environment variable.")

    print("Tip: For the web UI, run: python app.py")

    default_path = r"F:\eval\agents\AUN_ALI_RESUME.pdf"
    file_path = _prompt_pdf_path(default_path)

    document_text = load_pdf(file_path)
    vector_store = create_vector_store([document_text])

    qa_agent = create_qa_agent(vector_store)

    print("AI Research Assistant is ready. Ask your questions!")
    while True:
        query = input("You: ").strip()
        if query.lower() in ["exit", "quit"]:
            print("Goodbye!")
            break
        if not query:
            continue
        response = qa_agent(query)
        print(f"AI: {response}")

if __name__ == "__main__":
    main()

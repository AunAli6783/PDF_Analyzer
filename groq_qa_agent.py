import os

from groq import Groq

def create_qa_agent(vector_store):
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError("Missing GROQ_API_KEY environment variable.")

    model_candidates = [
        os.getenv("GROQ_MODEL"),
        "llama-3.1-8b-instant",
        "llama-3.1-70b-versatile",
        "mixtral-8x7b-32768",
    ]
    model_candidates = [m for m in model_candidates if m]

    client = Groq(api_key=api_key)
    retriever = vector_store.as_retriever(search_kwargs={"k": int(os.getenv("RETRIEVE_K", "4"))})
    max_context_chars = int(os.getenv("MAX_CONTEXT_CHARS", "8000"))

    def _build_context(question: str) -> str:
        docs = retriever.get_relevant_documents(question)
        parts = []
        total = 0
        for d in docs:
            chunk = getattr(d, "page_content", str(d)) or ""
            if not chunk:
                continue
            remaining = max_context_chars - total
            if remaining <= 0:
                break
            if len(chunk) > remaining:
                chunk = chunk[:remaining]
            parts.append(chunk)
            total += len(chunk)
        return "\n\n".join(parts) or "(no matching context found)"

    def ask(question: str) -> str:
        context = _build_context(question)

        if context.strip() == "(no matching context found)":
            return "I couldn't find relevant content in the uploaded document for that question."

        messages = [
            {"role": "system", "content": "Answer the user's question using only the provided context."},
            {"role": "system", "content": f"Context:\n{context}"},
            {"role": "user", "content": question},
        ]

        last_err = None
        for model in model_candidates:
            try:
                resp = client.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=float(os.getenv("TEMPERATURE", "0.2")),
                )
                return resp.choices[0].message.content or ""
            except Exception as e:
                last_err = e
                msg = str(e)
                if (
                    "model_decommissioned" in msg
                    or "decommissioned" in msg
                    or "invalid_request_error" in msg
                ):
                    continue
                raise
        raise last_err or RuntimeError("Groq request failed")

    return ask

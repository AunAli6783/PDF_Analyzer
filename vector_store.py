# vector_store.py
import math
import re
from dataclasses import dataclass
from collections import Counter

@dataclass(frozen=True)
class Document:
    page_content: str

_WORD_RE = re.compile(r"[A-Za-z0-9_]+")

def _tokenize(text: str):
    return [t.lower() for t in _WORD_RE.findall(text or "")]

def _cosine(a: Counter, b: Counter) -> float:
    if not a or not b:
        return 0.0
    dot = sum(v * b.get(k, 0) for k, v in a.items())
    na = math.sqrt(sum(v * v for v in a.values()))
    nb = math.sqrt(sum(v * v for v in b.values()))
    return dot / (na * nb) if na and nb else 0.0

class SimpleTextRetriever:
    def __init__(self, docs: list[Document], k: int = 4):
        self.docs = docs
        self.k = k
        self._vecs = [Counter(_tokenize(d.page_content)) for d in docs]

    def get_relevant_documents(self, query: str):
        qv = Counter(_tokenize(query))
        scored = [(_cosine(qv, dv), d) for dv, d in zip(self._vecs, self.docs)]
        scored.sort(key=lambda x: x[0], reverse=True)
        return [d for s, d in scored[: self.k] if s > 0]

class SimpleVectorStore:
    def __init__(self, docs: list[Document]):
        self.docs = docs

    def as_retriever(self, search_kwargs=None):
        k = (search_kwargs or {}).get("k", 4)
        return SimpleTextRetriever(self.docs, k=k)

def _chunk_text(text: str, chunk_size: int = 1200, chunk_overlap: int = 200):
    text = text or ""
    if chunk_size <= 0:
        return [text]
    step = max(1, chunk_size - max(0, chunk_overlap))
    chunks = []
    for i in range(0, len(text), step):
        chunk = text[i : i + chunk_size]
        if chunk.strip():
            chunks.append(chunk)
    return chunks

def create_vector_store(texts: list[str]):
    docs = []
    for t in texts:
        for chunk in _chunk_text(t, chunk_size=1200, chunk_overlap=200):
            docs.append(Document(page_content=chunk))
    return SimpleVectorStore(docs)
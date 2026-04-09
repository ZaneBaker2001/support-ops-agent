from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import math
import re
from collections import Counter

from app.config import get_settings


TOKEN_RE = re.compile(r"\b[a-zA-Z0-9_-]+\b")


def tokenize(text: str) -> list[str]:
    return [t.lower() for t in TOKEN_RE.findall(text)]


@dataclass
class DocumentChunk:
    source: str
    text: str


class LocalKnowledgeBase:
    """
    Lightweight lexical retriever over local markdown/txt files.
    This avoids extra infrastructure while still demonstrating a real retrieval tool.
    """

    def __init__(self, directory: str):
        self.directory = Path(directory)
        self.chunks: list[DocumentChunk] = []
        self._index()

    def _index(self) -> None:
        self.directory.mkdir(parents=True, exist_ok=True)
        files = list(self.directory.glob("**/*.md")) + list(self.directory.glob("**/*.txt"))

        chunks: list[DocumentChunk] = []
        for file in files:
            text = file.read_text(encoding="utf-8", errors="ignore")
            for block in self._split_text(text, chunk_size=900):
                chunks.append(DocumentChunk(source=file.name, text=block))
        self.chunks = chunks

    @staticmethod
    def _split_text(text: str, chunk_size: int = 900) -> list[str]:
        text = re.sub(r"\n{3,}", "\n\n", text.strip())
        if not text:
            return []
        chunks = []
        current = []
        size = 0
        for para in text.split("\n\n"):
            if size + len(para) > chunk_size and current:
                chunks.append("\n\n".join(current))
                current = [para]
                size = len(para)
            else:
                current.append(para)
                size += len(para)
        if current:
            chunks.append("\n\n".join(current))
        return chunks

    def search(self, query: str, k: int = 3) -> list[DocumentChunk]:
        q_tokens = tokenize(query)
        if not q_tokens or not self.chunks:
            return []

        q_counter = Counter(q_tokens)
        scored: list[tuple[float, DocumentChunk]] = []

        for chunk in self.chunks:
            d_tokens = tokenize(chunk.text)
            if not d_tokens:
                continue
            d_counter = Counter(d_tokens)
            score = cosine_counter_similarity(q_counter, d_counter)
            if score > 0:
                scored.append((score, chunk))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [chunk for _, chunk in scored[:k]]


def cosine_counter_similarity(a: Counter, b: Counter) -> float:
    dot = sum(a[token] * b[token] for token in set(a) & set(b))
    norm_a = math.sqrt(sum(v * v for v in a.values()))
    norm_b = math.sqrt(sum(v * v for v in b.values()))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


_knowledge_base: LocalKnowledgeBase | None = None


def get_knowledge_base() -> LocalKnowledgeBase:
    global _knowledge_base
    if _knowledge_base is None:
        settings = get_settings()
        _knowledge_base = LocalKnowledgeBase(settings.knowledge_dir)
    return _knowledge_base
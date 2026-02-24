from __future__ import annotations

import json
import math
import os
from typing import List, Dict

from .models import Chunk


class InMemoryVectorStore:
    def __init__(self):
        # list of chunks
        self.chunks: List[Chunk] = []
        # vocabulary: token -> index
        self.vocab: Dict[str, int] = {}
        # embeddings: chunk_id -> dense vector (list[float])
        self.embeddings: Dict[str, List[float]] = {}
        # storage path for persistence (optional)
        self.storage_path = os.path.join("storage", "chunks.jsonl")
        # attempt to load existing data
        self._load_from_disk()

    # Public API
    def add_chunks(self, chunks: List[Chunk]):
        if not chunks:
            return
        self.chunks.extend(chunks)
        # Rebuild vocab and embeddings to ensure consistency
        self._rebuild_vocab_and_embeddings()
        self._persist()

    def search(self, query_text: str, top_k: int = 5) -> List[Dict]:
        if not self.embeddings or not self.chunks:
            return []
        q_vec = self._text_to_vector(query_text)
        if not any(q_vec):
            return []
        results = []
        for ch in self.chunks:
            emb = self.embeddings.get(ch.id)
            if emb is None:
                continue
            score = self._cosine_similarity(q_vec, emb)
            if score <= 0:
                continue
            results.append({"chunk": ch, "score": score})
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:top_k]

    # Persistence helpers
    def _persist(self):
        # Ensure directory exists
        os.makedirs(os.path.dirname(self.storage_path), exist_ok=True)
        # Append all chunks as jsonl (overwrite for simplicity in MVP)
        with open(self.storage_path, "w", encoding="utf-8") as f:
            for ch in self.chunks:
                record = {
                    "id": ch.id,
                    "source_type": ch.source_type,
                    "source_id": ch.source_id,
                    "chunk_text": ch.chunk_text,
                    "created_at": ch.created_at,
                    "metadata": ch.metadata,
                }
                f.write(json.dumps(record, ensure_ascii=True) + "\n")

        # embeddings persisted in memory for MVP; could be extended to disk

    def _load_from_disk(self):
        # Load existing chunks if available
        self.chunks = []
        self.embeddings = {}
        if not os.path.exists(self.storage_path):
            return
        try:
            with open(self.storage_path, "r", encoding="utf-8") as f:
                for line in f:
                    if not line.strip():
                        continue
                    rec = json.loads(line)
                    ch = Chunk(
                        id=rec["id"],
                        source_type=rec["source_type"],
                        source_id=rec["source_id"],
                        chunk_text=rec["chunk_text"],
                        created_at=rec["created_at"],
                        metadata=rec.get("metadata", {}),
                    )
                    self.chunks.append(ch)
            # After loading, rebuild embeddings to reflect current chunks
            self._rebuild_vocab_and_embeddings()
        except Exception:
            # If the format is invalid, start fresh
            self.chunks = []
            self.embeddings = {}

    def _rebuild_vocab_and_embeddings(self):
        self.vocab = {}
        self.embeddings = {}
        # Build vocabulary from all chunk_texts, then compute embeddings
        for ch in self.chunks:
            self._add_text_to_vocab(ch.chunk_text)
        for ch in self.chunks:
            vec = self._text_to_vector(ch.chunk_text)
            self.embeddings[ch.id] = vec

    def _add_text_to_vocab(self, text: str):
        tokens = self._tokenize(text)
        for t in tokens:
            if t not in self.vocab:
                self.vocab[t] = len(self.vocab)

    def _tokenize(self, text: str) -> List[str]:
        # simple whitespace punctuation tokenizer
        import re
        return re.findall(r"[a-zA-Z0-9']+", text.lower())

    def _text_to_vector(self, text: str) -> List[float]:
        vec = [0.0] * (len(self.vocab) if self.vocab else 0)
        if not self.vocab:
            return vec
        for t in self._tokenize(text):
            idx = self.vocab.get(t)
            if idx is not None:
                vec[idx] += 1.0
        # L2 normalize
        norm = math.sqrt(sum(v * v for v in vec))
        if norm > 0:
            vec = [v / norm for v in vec]
        return vec

    def _cosine_similarity(self, a: List[float], b: List[float]) -> float:
        # both are same length
        if len(a) != len(b) or not a:
            return 0.0
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(x * x for x in b))
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)


def get_default_store() -> InMemoryVectorStore:
    # Lightweight helper to obtain a singleton-like store
    global _DEFAULT_STORE
    try:
        return _DEFAULT_STORE
    except NameError:
        _DEFAULT_STORE = InMemoryVectorStore()
        return _DEFAULT_STORE

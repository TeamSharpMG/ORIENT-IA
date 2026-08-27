"""RAG basique : chunking + recherche par mots-clés (BM25).

Pas d'embeddings, pas de vector store : le document est découpé en chunks,
puis une recherche lexicale (BM25) sélectionne les chunks les plus pertinents
pour une requête donnée. Simple à installer (aucune dépendance ML lourde),
suffisant comme première version.
"""

import re

from langchain_text_splitters import (
    MarkdownHeaderTextSplitter,
    RecursiveCharacterTextSplitter,
)
from rank_bm25 import BM25Okapi

from . import config

_TOKEN_RE = re.compile(r"\w+", re.UNICODE)


def _tokenize(text: str) -> list[str]:
    return _TOKEN_RE.findall(text.lower())


def load_and_chunk_documents() -> list[str]:
    text = (config.DOCUMENTS_DIR / "ispm-edu.md").read_text(encoding="utf-8")

    # Un chunk par section/sous-section (ex : une filière = un chunk).
    header_splitter = MarkdownHeaderTextSplitter(
        headers_to_split_on=[("##", "h2"), ("###", "h3"), ("####", "h4")],
        strip_headers=False,
    )
    sections = header_splitter.split_text(text)

    # Filet de sécurité si une section dépasse la taille cible.
    char_splitter = RecursiveCharacterTextSplitter(
        chunk_size=config.CHUNK_SIZE,
        chunk_overlap=config.CHUNK_OVERLAP,
    )
    return [chunk.page_content for chunk in char_splitter.split_documents(sections)]


class BM25Retriever:
    def __init__(self, chunks: list[str]):
        self.chunks = chunks
        self.bm25 = BM25Okapi([_tokenize(chunk) for chunk in chunks])

    def search_with_scores(self, query: str, k: int = config.RETRIEVER_K) -> list[tuple[str, float]]:
        """Comme search(), mais renvoie aussi le score BM25 de chaque chunk — utile pour
        les traces d'observabilité (score de recherche exigé par le protocole d'évaluation)."""
        scores = self.bm25.get_scores(_tokenize(query))
        ranked = sorted(range(len(self.chunks)), key=lambda i: scores[i], reverse=True)
        return [(self.chunks[i], float(scores[i])) for i in ranked[:k] if scores[i] > 0]

    def search(self, query: str, k: int = config.RETRIEVER_K) -> list[str]:
        return [chunk for chunk, _score in self.search_with_scores(query, k)]


def build_retriever() -> BM25Retriever:
    return BM25Retriever(load_and_chunk_documents())

"""
RAG (Retrieval-Augmented Generation) service backed by ChromaDB.

Why RAG?
Financial summaries benefit from background knowledge — e.g., understanding
that "Fed funds rate" is a monetary policy tool, or that "Chapter 11" means
bankruptcy. Injecting grounded context reduces hallucination risk.

Architecture:
- We use ChromaDB's EphemeralClient (pure-Python in-memory store) to avoid
  the Rust/DLL dependency that PersistentClient requires. Documents are
  re-seeded from the built-in list on every startup — acceptable for this
  use-case since the seed set is small and static.
- Embeddings are generated via OpenAI's text-embedding-3-small model
  (cheap, fast, high quality for semantic search).
- A curated set of ~10 sample financial documents is seeded at startup.
- At inference time, we retrieve the top-3 most relevant passages.
"""

import os
import logging
from typing import List


import chromadb
from chromadb.utils import embedding_functions

logger = logging.getLogger(__name__)

# Collection name in ChromaDB
_COLLECTION_NAME = "financial_knowledge_base"

# Number of documents to retrieve per query
_TOP_K = 3

# ---------------------------------------------------------------------------
# Sample seed documents
# ---------------------------------------------------------------------------

SAMPLE_DOCUMENTS = [
    {
        "id": "doc_001",
        "text": (
            "The Federal Reserve (Fed) controls US monetary policy primarily through "
            "the federal funds rate — the interest rate at which banks lend to each other overnight. "
            "Raising rates increases borrowing costs, slowing inflation. "
            "Cutting rates stimulates growth but risks inflation."
        ),
        "metadata": {"topic": "monetary_policy"},
    },
    {
        "id": "doc_002",
        "text": (
            "Earnings per share (EPS) measures a company's profit divided by its outstanding shares. "
            "A 'beat' means the company exceeded analyst consensus estimates. "
            "A 'miss' means it fell short. EPS beats typically drive stock price increases."
        ),
        "metadata": {"topic": "earnings"},
    },
    {
        "id": "doc_003",
        "text": (
            "Chapter 11 bankruptcy allows a company to restructure its debts while continuing operations. "
            "It differs from Chapter 7, which involves liquidation. "
            "Equity holders typically receive little to nothing in Chapter 11 proceedings."
        ),
        "metadata": {"topic": "bankruptcy"},
    },
    {
        "id": "doc_004",
        "text": (
            "Yield curve inversion occurs when short-term Treasury yields exceed long-term yields. "
            "Historically, an inverted yield curve has preceded recessions by 6-18 months. "
            "It signals that investors expect lower future interest rates."
        ),
        "metadata": {"topic": "macroeconomics"},
    },
    {
        "id": "doc_005",
        "text": (
            "Mergers and acquisitions (M&A) involve one company purchasing or merging with another. "
            "Acquirers typically pay a premium above the current market price. "
            "The deal can be cash-based, stock-based, or a combination. "
            "Regulatory approval (e.g., antitrust review) may be required."
        ),
        "metadata": {"topic": "m_and_a"},
    },
    {
        "id": "doc_006",
        "text": (
            "Inflation is the rate at which the general price level of goods and services rises. "
            "The Consumer Price Index (CPI) and the Personal Consumption Expenditures (PCE) index "
            "are the two primary measures used by the Fed. PCE is the Fed's preferred gauge."
        ),
        "metadata": {"topic": "inflation"},
    },
    {
        "id": "doc_007",
        "text": (
            "A stock buyback (share repurchase) is when a company buys its own shares from the market, "
            "reducing outstanding share count. This typically boosts EPS and signals management's "
            "confidence in the company's future. Buybacks are often viewed as bullish signals."
        ),
        "metadata": {"topic": "corporate_actions"},
    },
    {
        "id": "doc_008",
        "text": (
            "Quantitative easing (QE) is when a central bank purchases government bonds or other "
            "financial assets to inject liquidity into the economy. QE lowers long-term interest rates "
            "and encourages lending and investment. Tapering QE (reducing purchases) can tighten "
            "financial conditions."
        ),
        "metadata": {"topic": "monetary_policy"},
    },
    {
        "id": "doc_009",
        "text": (
            "Credit ratings from agencies like Moody's, S&P, and Fitch indicate the creditworthiness "
            "of a bond issuer. Investment-grade ratings (BBB- and above) signal low default risk. "
            "Junk bonds (below BBB-) offer higher yields but carry significantly higher default risk."
        ),
        "metadata": {"topic": "credit_markets"},
    },
    {
        "id": "doc_010",
        "text": (
            "Oil prices are driven by supply (OPEC+ production decisions) and demand (global economic growth). "
            "Higher oil prices increase costs for energy-intensive sectors (airlines, shipping, manufacturing) "
            "and act as an inflation tax on consumers. Energy stocks typically benefit from rising oil prices."
        ),
        "metadata": {"topic": "commodities"},
    },
]


# ---------------------------------------------------------------------------
# RAGService
# ---------------------------------------------------------------------------

class RAGService:
    """Wraps ChromaDB for document storage and semantic retrieval."""

    def __init__(self):
        # EphemeralClient = pure-Python in-memory store; no Rust DLL required.
        # To persist across restarts, swap to chromadb.PersistentClient(path=...)
        # once the Visual C++ runtime / Rust bindings are available.
        self._client = chromadb.EphemeralClient()

        # Using Chroma's default local embeddings (all-MiniLM-L6-v2) 
        # since OpenRouter does not provide an embeddings endpoint.
        self._embedding_fn = embedding_functions.DefaultEmbeddingFunction()

        self._collection = self._client.get_or_create_collection(
            name=_COLLECTION_NAME,
            embedding_function=self._embedding_fn,
            metadata={"hnsw:space": "cosine"},
        )

    # ------------------------------------------------------------------
    # Seeding
    # ------------------------------------------------------------------

    def seed_sample_documents(self) -> None:
        """
        Insert sample documents into ChromaDB on first run.
        Skips documents that already exist (idempotent).
        Gracefully handles OpenAI quota/auth errors so server startup is not blocked.
        """
        existing_ids = set(self._collection.get()["ids"])
        to_add = [doc for doc in SAMPLE_DOCUMENTS if doc["id"] not in existing_ids]

        if not to_add:
            logger.info("RAG: All sample documents already seeded.")
            return

        try:
            self._collection.add(
                ids=[d["id"] for d in to_add],
                documents=[d["text"] for d in to_add],
                metadatas=[d["metadata"] for d in to_add],
            )
            logger.info(f"RAG: Seeded {len(to_add)} new document(s).")
        except Exception as exc:
            logger.warning(f"RAG seeding failed unexpectedly: {exc}. Continuing without seed data.")

    # ------------------------------------------------------------------
    # Adding custom documents (for extensibility)
    # ------------------------------------------------------------------

    def add_documents(self, texts: List[str], ids: List[str], metadatas: List[dict] = None) -> None:
        """Add new documents to the knowledge base."""
        try:
            self._collection.add(
                ids=ids,
                documents=texts,
                metadatas=metadatas or [{} for _ in texts],
            )
        except Exception as exc:
            logger.warning(f"RAG add_documents failed: {exc}")
            raise

    # ------------------------------------------------------------------
    # Retrieval
    # ------------------------------------------------------------------

    def retrieve_context(self, query: str, top_k: int = _TOP_K) -> str:
        """
        Retrieve the top-k most relevant documents for *query*.

        Returns a single string with numbered passages ready to inject
        into the prompt. Returns empty string if the collection is empty.
        """
        count = self._collection.count()
        if count == 0:
            return ""

        results = self._collection.query(
            query_texts=[query],
            n_results=min(top_k, count),
        )

        passages = results.get("documents", [[]])[0]
        if not passages:
            return ""

        formatted = "\n\n".join(
            f"[Context {i+1}]: {passage}" for i, passage in enumerate(passages)
        )
        return formatted

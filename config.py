"""
Settings for The Unofficial Guide.

Everything you're likely to change lives here, at the top, on purpose.
You'll edit THRESHOLD in Milestone 4 and the chunking numbers in Milestone 3.

Anything you set in your .env file wins over the defaults here.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).parent
load_dotenv(ROOT / ".env")


# ─── The corpus you're working with ──────────────────────────────────────────
# Change this to switch corpora, or pass --corpus on the command line.
# Options are the folder names inside corpora/. See corpora/README.md.

CORPUS = os.getenv("AI201_CORPUS", "campus_life")


# ─── Chunking (Milestone 3) ──────────────────────────────────────────────────
# `chunker.py::split_documents` splits city_guides on its `##` headings, one
# chunk per section. So CHUNK_SIZE is a CEILING, not a window: a section longer
# than this gets cut at paragraph breaks and then at sentence ends. The longest
# section in this corpus is 708 characters, so nothing reaches it.
#
# 1100 rather than 800 because 800 would start cutting sections that are single
# complete thoughts, which is the whole thing I am trying to stop.
CHUNK_SIZE = 1100      # ceiling per chunk, in characters

# 0 because sections do not overlap. Overlap exists to stop a thought being cut
# in half; splitting at headings already guarantees that. Keeping the starter's
# 120 would duplicate text and let near-duplicate chunks compete for the same
# TOP_K slots.
CHUNK_OVERLAP = 0

# The starter's numbers, kept so unit 2 can reproduce the baseline:
#   fallback_split(docs, chunk_size=800, overlap=120)
#   -> 51 chunks, 650 avg, shortest 24, longest 800


# ─── Retrieval (Milestone 4) ─────────────────────────────────────────────────

TOP_K = 5               # how many chunks to pull back per question

# The relevance gate. If the best chunk is further away than this, the system
# refuses to answer instead of handing the model thin material.
#
# LOWER IS BETTER: 0.3 is a close match, 0.9 is unrelated.
#
# Measured in Milestone 4 (see README "Relevance Cutoff"). Two groups:
#   my 5 test questions      0.158 - 0.386
#   loosely phrased but
#     still answerable       0.349 - 0.639   <- the group that set this number
#   OUT_OF_SCOPE (far)       0.810 - 0.963
#
# 0.72 is the midpoint of 0.639 and 0.810. The starter's 0.6 refused five of
# ten legitimate questions, including "Do I need cash?" (0.637) and "How bad is
# the parking?" (0.639), both of which the corpus answers.
#
# What this number CANNOT do: near-miss travel questions this corpus can't
# answer score 0.311 - 0.576, overlapping the legitimate range. No cutoff
# separates those. GROUNDING_INSTRUCTION in generate.py is the layer that has
# to catch them.
THRESHOLD = 0.72


# ─── Models ──────────────────────────────────────────────────────────────────
# Embeddings run on your own machine and cost no API quota.
# Only generation calls out to a service.

# This is the model Chroma bundles, and leaving it alone is the fast path: it
# downloads about 80 MB from Chroma's own CDN and needs nothing else installed.
#
# Setting it to any other name — unit 2's "try a second embedding model"
# stretch option — switches to loading that model from Hugging Face instead,
# which needs `pip install 'sentence-transformers>=3.4,<3.5'` first. store.py
# says so with a real error message rather than a stack trace if you forget.
EMBEDDING_MODEL = "all-MiniLM-L6-v2"
MODEL = os.getenv("AI201_MODEL", "gemini-3.5-flash-lite")


# ─── Rate limiting and quota guards ──────────────────────────────────────────
# You should not need to touch these. They exist so that a runaway loop costs
# you a warning instead of your whole day's allowance.

REQUESTS_PER_MINUTE = 30       # outgoing calls the limiter will allow per minute
SESSION_REQUEST_BUDGET = 300   # stop and warn rather than draining the daily quota
MAX_RETRIES = 4                # on 429 / resource-exhausted, with backoff

CACHE_ENABLED = os.getenv("AI201_CACHE", "1") != "0"
CACHE_DIR = ROOT / ".cache"


# ─── Paths ───────────────────────────────────────────────────────────────────

CORPORA_DIR = ROOT / "corpora"
CHROMA_DIR = ROOT / "chroma_db"
RESULTS_DIR = ROOT / "results"


def corpus_path(name: str | None = None) -> Path:
    """Folder holding the documents for a corpus."""
    return CORPORA_DIR / (name or CORPUS) / "documents"


def collection_name(name: str | None = None, variant: str = "default") -> str:
    """
    Name of the vector-store collection for a corpus.

    `variant` lets you index the same corpus two different ways and query both
    without deleting anything — you'll want that in unit 2 when you compare
    chunking strategies.

    Chroma is fussy about collection names: 3 to 63 characters, starting and
    ending with a letter or digit, and nothing but letters, digits, underscores
    and hyphens in between. If you bring your own corpus and name the folder
    something Chroma won't accept, this cleans it up rather than failing.
    """
    import re

    raw = f"{name or CORPUS}__{variant}"
    cleaned = re.sub(r"[^A-Za-z0-9_-]", "-", raw)
    cleaned = cleaned.strip("_-")          # must start and end alphanumeric
    if not cleaned or not cleaned[0].isalnum():
        cleaned = f"c{cleaned}"
    if not cleaned[-1].isalnum():
        cleaned = f"{cleaned}0"
    return cleaned[:63].rstrip("_-") or "collection"

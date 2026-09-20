"""
Stage 2 of the pipeline: splitting documents into chunks.

Milestone 3. `split_documents` splits on the `##` headings the guides are
already written with, one chunk per section, no overlap.

WHAT THE STARTER DID, measured before replacing it (`city_guides`, 800-char
windows with 120 of overlap):

    51 chunks, 650 characters on average (shortest 24, longest 800)
    37 of 51 chunks spanned more than one heading
    15 of 51 started at a heading
    18 of 51 ended at a sentence end

The 24-character chunk was `'d Sundays and after 5pm.'` — the tail of a
document that did not divide evenly. `guide_elder_ness.md#0` ended mid-word, on
`## Eat and drin`, and held four topics at once.

WHY SECTIONS:

1. The 14 guides are already divided into 84 `##` sections — "Getting there",
   "Eat and drink", "When to go". Median 294 characters, longest 708, none over
   800. The author already chunked these documents; the starter was overriding
   that with an arbitrary character count.

2. Sections are topically self-contained but NOT referentially self-contained.
   `guide_elder_ness.md` "Where to stay" begins "The pub has four rooms" and
   never names Elder Ness. A bare section is a complete thought about nowhere
   in particular, so every chunk carries a `Town — Section` label. Without it
   this strategy would retrieve the right kind of paragraph about the wrong
   town.

3. Overlap is 0. Overlap exists to stop a thought being cut in half, and
   splitting at headings already guarantees that. Keeping 120 characters of it
   would duplicate text and let near-identical chunks compete for the same five
   top-k slots.

CHUNK_SIZE is now a ceiling rather than a window: a section longer than it gets
cut at paragraph breaks, then at sentence ends, never mid-word. On this corpus
nothing is long enough to trigger that — it is there so the strategy degrades
sensibly rather than producing one enormous chunk on a corpus that needs it.

`fallback_split` below is the starter's original, kept for the before/after
comparison in unit 2. Reproduce the baseline above by calling it explicitly:
`fallback_split(docs, chunk_size=800, overlap=120)` — the config defaults it
otherwise reads are now this strategy's numbers, not the starter's.
"""

import re
from dataclasses import dataclass
from pathlib import Path

import config
from ingest import Document


@dataclass
class Chunk:
    """One piece of one document."""

    text: str
    source: str        # which file it came from
    index: int         # which chunk within that file, starting at 0
    produced_by: str   # the function that made it — cite this in your README

    @property
    def label(self) -> str:
        return f"{self.source}#{self.index}"


def fallback_split(
    documents: list[Document],
    chunk_size: int | None = None,
    overlap: int | None = None,
) -> list[Chunk]:
    """
    The starter's original chunker. Fixed-size character windows with overlap.

    Keep this function. Milestone 3's stop rule points back at it, and having
    something to compare your own strategy against is useful in unit 2.
    """
    chunk_size = chunk_size or config.CHUNK_SIZE
    overlap = overlap or config.CHUNK_OVERLAP

    if overlap >= chunk_size:
        raise ValueError("overlap has to be smaller than chunk_size")

    chunks: list[Chunk] = []
    for doc in documents:
        start = 0
        index = 0
        while start < len(doc.text):
            piece = doc.text[start : start + chunk_size].strip()
            if piece:
                chunks.append(
                    Chunk(
                        text=piece,
                        source=doc.source,
                        index=index,
                        produced_by="chunker.py::fallback_split",
                    )
                )
                index += 1
            start += chunk_size - overlap

    return chunks


_TITLE_RE = re.compile(r"^#\s+(.+?)\s*$", re.M)
_HEADING_RE = re.compile(r"^##\s+(.+?)\s*$", re.M)


def _document_title(text: str, source: str) -> str:
    """
    The name of the place this document is about.

    Prefer the `# Title` line. Fall back to the filename, since the provided
    `.txt` corpora have no headings at all and still need a label.
    """
    match = _TITLE_RE.search(text)
    if match:
        return match.group(1).strip()

    stem = re.sub(r"^(guide|thread|admin|course|advising)_", "", Path(source).stem)
    return stem.replace("_", " ").strip().title()


def _sections(text: str) -> list[tuple[str, str]]:
    """
    Cut a document at its `##` headings into (heading, body) pairs.

    The title line and opening paragraph — everything before the first `##` —
    come back as ("Overview", ...), because on these guides that paragraph
    holds the population and the one-line description of the town and is worth
    retrieving on its own.

    A document with no `##` headings comes back as one ("", body) pair, which
    `_fit` then cuts on paragraph breaks. Headings with nothing under them are
    dropped rather than becoming empty chunks.
    """
    headings = list(_HEADING_RE.finditer(text))

    if not headings:
        return [("", _TITLE_RE.sub("", text, count=1).strip())]

    sections: list[tuple[str, str]] = []

    preamble = _TITLE_RE.sub("", text[: headings[0].start()], count=1).strip()
    if preamble:
        sections.append(("Overview", preamble))

    for i, match in enumerate(headings):
        end = headings[i + 1].start() if i + 1 < len(headings) else len(text)
        body = text[match.end() : end].strip()
        if body:
            sections.append((match.group(1).strip(), body))

    return sections


def _sentences(paragraph: str, budget: int) -> list[str]:
    """
    One paragraph too long to fit, packed at sentence ends.

    Packing greedily up to `budget` leaves an orphan tail — a 456-character
    paragraph against a 400 budget comes out as 379 + 75, and a 75-character
    fragment is exactly what I replaced the starter's chunker to stop producing.
    So aim for equal pieces instead: work out how many are needed, then pack to
    that share of the text rather than to the ceiling.
    """
    needed = -(-len(paragraph) // budget)          # ceiling division
    target = -(-len(paragraph) // needed) if needed else budget

    pieces: list[str] = []
    current = ""
    for sentence in re.split(r"(?<=[.!?])\s+", paragraph):
        if not current:
            current = sentence
        elif len(current) + 1 + len(sentence) <= target:
            current = f"{current} {sentence}"
        else:
            pieces.append(current)
            current = sentence
    if current:
        pieces.append(current)
    return pieces


def _fit(body: str, budget: int) -> list[str]:
    """
    One section, cut only if it does not fit in `budget` characters.

    Cuts at paragraph breaks first, sentence ends second, and never mid-word.
    On `city_guides` this returns `[body]` every time: the longest section is
    708 characters and the budget is larger than that.
    """
    if len(body) <= budget:
        return [body]

    pieces: list[str] = []
    current = ""

    for paragraph in re.split(r"\n\s*\n", body):
        paragraph = paragraph.strip()
        if not paragraph:
            continue

        units = [paragraph] if len(paragraph) <= budget else _sentences(paragraph, budget)
        for unit in units:
            if not current:
                current = unit
            elif len(current) + 2 + len(unit) <= budget:
                current = f"{current}\n\n{unit}"
            else:
                pieces.append(current)
                current = unit

    if current:
        pieces.append(current)
    return pieces


def split_documents(documents: list[Document]) -> list[Chunk]:
    """
    One chunk per `##` section, labelled with the town it belongs to.

    See the module docstring for what the starter did and why this replaces it.
    The short version: these guides arrive pre-divided into 84 topical sections
    that all fit inside one chunk, so the sections are the chunks — and each one
    gets a `Town — Section` first line, because a section body on its own never
    names its own town.
    """
    chunks: list[Chunk] = []

    for doc in documents:
        title = _document_title(doc.text, doc.source)
        index = 0

        for heading, body in _sections(doc.text):
            label = f"{title} — {heading}" if heading else title
            # The label is part of the chunk, so it comes out of the ceiling.
            budget = max(config.CHUNK_SIZE - len(label) - 2, 200)

            for piece in _fit(body, budget):
                chunks.append(
                    Chunk(
                        text=f"{label}\n\n{piece}",
                        source=doc.source,
                        index=index,
                        produced_by="chunker.py::split_documents",
                    )
                )
                index += 1

    return chunks


def describe(chunks: list[Chunk]) -> str:
    """A one-line summary, printed after indexing."""
    if not chunks:
        return "0 chunks"
    lengths = [len(c.text) for c in chunks]
    return (
        f"{len(chunks)} chunks, "
        f"{sum(lengths) // len(lengths)} characters on average "
        f"(shortest {min(lengths)}, longest {max(lengths)}), "
        f"produced by {chunks[0].produced_by}"
    )


if __name__ == "__main__":
    from ingest import load_documents

    chunks = split_documents(load_documents())
    print(describe(chunks))

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


def _place_names(documents: list[Document]) -> set[str]:
    """
    Which document titles are places, worked out from the corpus itself.

    A place guide's title gets talked about by other documents — `guide_seasons.md`
    talks about Halden Bay, `guide_walking.md` about Kestrelford. A topic
    guide's title never does: nothing in this corpus says "When to visit the
    region" in a sentence. So a title that shows up in another document's text
    is a place, and one that doesn't is a topic.

    Other documents' title lines do not count, which is not a detail I would
    have predicted. `guide_regional_transport.md` is titled "Getting around the
    region", and that is a prefix of `guide_accessibility.md`'s title, "Getting
    around the region with limited mobility". Counting title lines made the
    transport guide look like a place, so it was the one topic guide that never
    got split.

    Derived rather than hardcoded because a list of nine town names would be a
    list about `city_guides` living in a file that also has to chunk three
    other corpora.
    """
    titles = {_document_title(doc.text, doc.source): doc.source for doc in documents}
    bodies = {
        doc.source: _TITLE_RE.sub("", doc.text, count=1) for doc in documents
    }
    return {
        title
        for title, source in titles.items()
        if any(title in body for name, body in bodies.items() if name != source)
    }


def _clauses(sentence: str, places: list[str]) -> list[tuple[str, str]]:
    """
    One sentence about several places, cut into (place, text) at its commas.

    This is the ugly part of the strategy and it is worth being honest about
    why it exists. `guide_seasons.md` "Summer" contains:

        July and August split: Halden Bay becomes very busy and the parking
        problem dominates, Kestrelford fills with walkers, and Brightwater goes
        quiet to the point of dullness with the university empty.

    Three towns, one sentence. Keeping it whole and filing it under all three
    towns scores 0.4765 against my Brightwater question — better than the 0.5185
    it scores inside the full section, and still outside the top five. Cutting
    it at the commas scores 0.3398. So a sentence boundary is not a fine enough
    cut for a sentence built this way, and nothing less than the comma moves
    this question into retrieval.

    Each piece carries the sentence's lead-in — "July and August split:" — so
    the Brightwater clause does not arrive detached from the months it is about.
    """
    positions = sorted((sentence.index(p), p) for p in places)
    lead = sentence[: positions[0][0]].strip()
    if len(lead) > 80:                      # a clause of its own, not a lead-in
        lead = ""

    groups: list[tuple[list[str], list[str]]] = []
    waiting_places: list[str] = []
    waiting_text: list[str] = []

    for piece in re.split(r"(?<=[,;])\s+", sentence):
        piece = piece.strip()
        if not piece:
            continue

        named = [p for p in places if p in piece]
        remainder = piece
        for place in named:
            remainder = remainder.replace(place, " ")
        remainder = re.sub(r"\b(and|or)\b|[\s,;.:]+", " ", remainder).strip()

        if named and not remainder:
            # A bare name in a list: "Kestrelford," on its own says nothing.
            # It is waiting for the predicate the whole list shares.
            waiting_places.extend(named)
            waiting_text.append(piece)
        elif named:
            groups.append((waiting_places + named, waiting_text + [piece]))
            waiting_places, waiting_text = [], []
        elif groups and not waiting_places:
            groups[-1][1].append(piece)     # a continuation of the last place
        else:
            waiting_text.append(piece)      # lead-in, already captured above

    if waiting_places:
        if groups:
            groups[-1][0].extend(waiting_places)
            groups[-1][1].extend(waiting_text)
        else:
            groups.append((waiting_places, waiting_text))

    out: list[tuple[str, str]] = []
    for i, (group_places, parts) in enumerate(groups):
        text = re.sub(r"^and\s+", "", " ".join(parts)).rstrip(",;").strip()
        if i and lead:
            text = f"{lead} {text}"
        if not text.endswith((".", "!", "?")):
            text += "."
        for place in dict.fromkeys(group_places):
            out.append((place, text))
    return out


def _by_place(body: str, places: set[str]) -> dict[str, list[str]] | None:
    """
    One topic-guide section, split into the places it talks about.

    Returns `{place: [text, ...]}`, or None if the section is about fewer than
    two places and the section-sized chunk is already the right unit.

    Sentences that name no place are attributed to the last place named in the
    same paragraph — "It is flat, compact" belongs to whichever town the
    paragraph opened with, and filing it anywhere else would produce a chunk
    that states a fact about the wrong town, which is worse than the dilution
    this is here to fix. Attribution resets at every paragraph break, because
    in these guides a new paragraph is a new town as often as not.

    That leaves two kinds of place-free sentence and they are not the same
    thing:

    - Before any place in the section has been named, it is framing. "June is
      excellent everywhere" belongs in all three of that section's chunks, and
      the Brightwater chunk needs it to keep "July and August" attached to the
      answer.
    - After that, at the head of a later paragraph, it belongs to nothing in
      particular. `guide_seasons.md` "Winter" opens its second paragraph with
      "The coastal path is dramatic and frequently shut", which is about the
      coast and not about Brightwater. Copying it into every town's chunk puts
      a coast fact under a Brightwater label, which is the cross-town error my
      grounding rules exist to stop. It comes back under the `None` key and
      becomes a chunk of its own, keeping the sentence in the index without
      pinning it on a town.
    """
    found = {p for p in places if p in body}
    if len(found) < 2:
        return None

    shared: list[str] = []
    leftover: list[str] = []
    per: dict[str, list[str]] = {}

    for paragraph in re.split(r"\n\s*\n", body):
        paragraph = " ".join(paragraph.split())
        if not paragraph:
            continue

        current: str | None = None
        for sentence in re.split(r"(?<=[.!?])\s+", paragraph):
            named = sorted((sentence.index(p), p) for p in places if p in sentence)

            if not named:
                if current:
                    per[current].append(sentence)
                elif per:
                    leftover.append(sentence)
                else:
                    shared.append(sentence)
            elif len(named) == 1:
                current = named[0][1]
                per.setdefault(current, []).append(sentence)
            else:
                for place, text in _clauses(sentence, [p for _, p in named]):
                    per.setdefault(place, []).append(text)
                    current = place

    if len(per) < 2:
        return None

    out: dict[str | None, list[str]] = {
        place: shared + text for place, text in per.items()
    }
    if leftover:
        out[None] = leftover
    return out


def split_documents(documents: list[Document]) -> list[Chunk]:
    """
    One chunk per `##` section — and, in the topic guides, one per place.

    See the module docstring for what the starter did and why this replaced it.
    The short version: these guides arrive pre-divided into topical sections
    that all fit inside one chunk, so the sections are the chunks, and each gets
    a `Place — Section` first line because a section body never names its own
    town.

    UNIT 2 CHANGE. That rule fits nine of my fourteen documents. The other five
    — seasons, walking, eating, accessibility, regional transport — are one
    topic swept across many towns, and 19 of the 22 chunks they produced named
    two or more. One chunk is one vector, so those vectors stood for three or
    four towns at once and sat too far from a question about any single one:
    the sentence answering my Brightwater question ranked 12th of 94 inside its
    section and 1st on its own (`tools/measure_dilution.py`).

    So a section of a guide that is not about a place is now split into the
    places it names, labelled `Topic — Section — Place`. Sections of place
    guides are untouched, and so are topic sections that only name one place.
    """
    chunks: list[Chunk] = []
    places = _place_names(documents)

    for doc in documents:
        title = _document_title(doc.text, doc.source)
        index = 0

        for heading, body in _sections(doc.text):
            label = f"{title} — {heading}" if heading else title

            by_place = None if title in places else _by_place(body, places)
            parts = (
                [
                    (f"{label} — {place}" if place else label, " ".join(text))
                    for place, text in by_place.items()
                ]
                if by_place
                else [(label, body)]
            )

            for part_label, part_body in parts:
                # The label is part of the chunk, so it comes out of the ceiling.
                budget = max(config.CHUNK_SIZE - len(part_label) - 2, 200)
                for piece in _fit(part_body, budget):
                    chunks.append(
                        Chunk(
                            text=f"{part_label}\n\n{piece}",
                            source=doc.source,
                            index=index,
                            produced_by=(
                                "chunker.py::_by_place"
                                if by_place
                                else "chunker.py::split_documents"
                            ),
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

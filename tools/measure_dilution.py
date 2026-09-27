#!/usr/bin/env python3
"""
Is the Brightwater miss the embedding model, or the chunk it lives in?

    python tools/measure_dilution.py

Two of my questions retrieve badly, and both answers live in a `##` section
that covers several towns at once. One section is one chunk is one vector, so
that vector has to stand for every town in the section. This asks whether that
is what is actually happening, by embedding the same answer twice with the same
model `store.py` indexes with: once inside the section as indexed, and once as
the town-specific excerpt a town-aware chunker would have produced.

If the excerpt scores much closer than the section, the model understands the
sentence fine and my chunking is what buried it. If both score about the same,
the model is the problem and chunking is not.

The excerpts below are cut by hand — they are the hypothesis, not output.
Nothing here changes the index; it is a measurement, not a fix.
"""

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import config

# question, the chunk's label line, and the town-specific excerpt from inside it
CASES = [
    (
        "Why does Brightwater get quiet in July and August when the rest of the region is busy?",
        "When to visit the region — Summer, June to August",
        "Brightwater goes quiet to the point of dullness with the university empty.",
    ),
    (
        "Which town in the region is easiest to get around with limited mobility?",
        "Getting around the region with limited mobility — Straightforward",
        "**Thornby Wells** is the easiest town in the region. It is flat, compact, and\n"
        "everything is within three minutes of everything else. Parking is free for two\n"
        "hours anywhere in town and the station is central. The pump room and gardens\n"
        "are level throughout.",
    ),
]


# The nine town guides are one place per document; these five are one topic
# swept across many places. The split is the point of the second measurement.
REGIONAL_GUIDES = {
    "guide_accessibility.md",
    "guide_eating.md",
    "guide_regional_transport.md",
    "guide_seasons.md",
    "guide_walking.md",
}

TOWNS = [
    "Brightwater", "Corry Vale", "Elder Ness", "Givens Mill", "Halden Bay",
    "Kestrelford", "Marchwood", "Pellew Sands", "Thornby Wells",
]


def corpus_shape(chunks):
    """How many chunks are about more than one town, and where they come from.

    The dilution above is two questions. This says whether those two are a
    coincidence or the shape of five of my fourteen documents.
    """
    import statistics

    regional = [c for c in chunks if c.source in REGIONAL_GUIDES]
    town = [c for c in chunks if c.source not in REGIONAL_GUIDES]
    multi = lambda cs: [c for c in cs if sum(t in c.text for t in TOWNS) >= 2]

    print("# Where the multi-town chunks are\n")
    print(f"  {len(chunks)} chunks: {len(regional)} from the 5 regional guides, "
          f"{len(town)} from the 9 town guides")
    print(f"  naming 2+ towns   regional {len(multi(regional))} of {len(regional)}"
          f"   |   town guides {len(multi(town))} of {len(town)}")
    print(f"  median characters regional {statistics.median(len(c.text) for c in regional):.0f}"
          f"        |   town guides {statistics.median(len(c.text) for c in town):.0f}")

    worst = sorted(
        ((sum(t in c.text for t in TOWNS), c.source, c.text.split("\n", 1)[0]) for c in regional),
        reverse=True,
    )
    print("\n  the most crowded sections:")
    for n, source, label in worst[:4]:
        print(f"    {n} towns  {source:<28} {label}")


def cosine_distance(embed, a, b):
    """Same metric the index uses — store.py builds the collection with cosine."""
    x, y = embed([a, b])
    dot = sum(p * q for p, q in zip(x, y))
    norm = math.sqrt(sum(p * p for p in x)) * math.sqrt(sum(q * q for q in y))
    return 1 - dot / norm


def sections(documents):
    """Every `##` section in the corpus as {label: text}, however it is chunked.

    Read from the documents rather than from the chunks, because the whole
    point of the improvement is that these sections are no longer single
    chunks. Taking them from `split_documents` would mean this script stopped
    running the moment its own finding was acted on.
    """
    from chunker import _document_title, _sections

    out = {}
    for doc in documents:
        title = _document_title(doc.text, doc.source)
        for heading, body in _sections(doc.text):
            label = f"{title} — {heading}" if heading else title
            out[label] = (f"{label}\n\n{body}", doc.source)
    return out


def main():
    import argparse

    from chromadb.utils.embedding_functions import ONNXMiniLM_L6_V2

    from ingest import load_documents
    from chunker import split_documents
    from store import search

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--variant",
        default="default",
        help="index to take ranks from (default is the pre-improvement index)",
    )
    args = parser.parse_args()

    embed = ONNXMiniLM_L6_V2()
    documents = load_documents(config.CORPUS)
    chunks = split_documents(documents)
    by_label = sections(documents)

    print("# Dilution: the whole section vs the town-specific excerpt inside it")
    print(f"# embedding {config.EMBEDDING_MODEL} via ONNXMiniLM_L6_V2, cosine, lower is better")
    print(f"# ranks from the '{args.variant}' index\n")

    for question, label, excerpt in CASES:
        section_text, source = by_label[label]
        labelled_excerpt = f"{label}\n\n{excerpt}"

        whole = cosine_distance(embed, question, section_text)
        alone = cosine_distance(embed, question, labelled_excerpt)

        results = search(question, top_k=len(chunks), corpus=config.CORPUS, variant=args.variant)
        rank = next(
            (i for i, r in enumerate(results, 1) if r.text.split("\n", 1)[0] == label),
            None,
        )
        beats = sum(1 for r in results[:5] if r.distance > alone)

        print(question)
        print(f"  {label}  ({source})")
        if rank:
            print(f"    whole section, as indexed : {whole:.4f}   rank {rank} of {len(results)}")
            print(f"    town excerpt alone        : {alone:.4f}   "
                  f"would beat {beats} of the 5 retrieved")
            print(f"    top-k is {config.TOP_K}, so the section "
                  f"{'was retrieved' if rank <= config.TOP_K else 'was NOT retrieved'}")
        else:
            print(f"    whole section             : {whole:.4f}   "
                  f"not a chunk in this index any more")
            print(f"    town excerpt alone        : {alone:.4f}   "
                  f"would beat {beats} of the 5 retrieved")
        print()

    corpus_shape(chunks)


if __name__ == "__main__":
    main()

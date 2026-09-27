#!/usr/bin/env python3
"""
The two criteria `run_eval.py` cannot measure for me.

    python tools/verify_criteria.py

Criterion 1 is about the retrieved CHUNKS, not the answer, and criterion 4 is
about chunk boundaries and never reaches retrieval at all — so neither shows up
in the run log `run_eval.py` writes. This prints both, with the chunk text, so
the numbers in my run log have something behind them.

Criteria 2, 3 and 5 are already in results/: 2 is read off the answers, 3 is
`run_eval.py::check_out_of_scope`, and 5 is arithmetic on the best distances
that run log prints for both groups.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import config
import questions as qs


def criterion_1(corpus=None, variant="default", top_k=None):
    """For how many questions do the retrieved chunks contain the answer?

    top_k comes from config, not a number I picked. Criterion 1 says "the
    retrieved chunks", and what the system retrieves is TOP_K — testing the
    top 3 would be measuring a stricter criterion than the one I wrote.
    """
    from store import search

    corpus = corpus or config.CORPUS
    top_k = top_k or config.TOP_K

    print(f"# Criterion 1 — retrieved chunks contain the answer")
    print(f"# corpus {corpus}, top-k {top_k} (from config.TOP_K)\n")

    hits = 0
    for item in qs.answered():
        question, expects = item["question"], item["expects"]
        results = search(question, top_k=top_k, corpus=corpus, variant=variant)

        found_at = None
        for rank, r in enumerate(results, 1):
            if expects.lower() in r.text.lower():
                found_at = rank
                break

        hits += found_at is not None
        verdict = f"FOUND at rank {found_at}" if found_at else "NOT FOUND"
        print(f"{question}")
        print(f"  expects {expects!r}: {verdict}")
        for rank, r in enumerate(results, 1):
            mark = "*" if rank == found_at else " "
            first_line = r.text.split("\n", 1)[0][:70]
            print(f"  {mark} {rank}. {r.distance:.4f}  {r.source:<28} {first_line}")
        if found_at:
            print("\n  the chunk that contains it:")
            print("  " + results[found_at - 1].text.replace("\n", "\n  "))
        print()

    print(f"-> {hits} of {len(qs.answered())} questions had the answer in the retrieved chunks")
    return hits


def criterion_4(corpus=None, n=10):
    """Do the sampled chunks start at a heading and end at a sentence end?

    Criterion 4 asks two things of a 10-chunk sample: no chunk holds text from
    more than one `##` section, and every one begins at a heading and ends at a
    sentence boundary. Chunks carry a `Town — Section` label rather than a raw
    `##` line, so "begins at a heading" means the label is the first line and
    the body starts at the section it names.
    """
    from ingest import load_documents
    from chunker import split_documents

    corpus = corpus or config.CORPUS
    chunks = split_documents(load_documents(corpus))
    step = max(len(chunks) // n, 1)
    sample = chunks[::step][:n]

    print(f"\n# Criterion 4 — one section per chunk, clean boundaries")
    print(f"# {len(chunks)} chunks total, sampling {len(sample)} spread across the corpus\n")

    ok = 0
    for i, chunk in enumerate(sample, 1):
        body = chunk.text.split("\n", 1)
        label = body[0]
        rest = body[1] if len(body) > 1 else ""
        one_section = "\n##" not in chunk.text
        starts_at_heading = "—" in label and not rest.lstrip().startswith("#")
        ends_at_sentence = chunk.text.rstrip().endswith((".", "!", "?", ":", '."', ".)"))
        good = one_section and starts_at_heading and ends_at_sentence
        ok += good
        print(
            f"{i:>2}. {chunk.source}#{chunk.index:<3} "
            f"one section: {'yes' if one_section else 'NO':<3} "
            f"starts at heading: {'yes' if starts_at_heading else 'NO':<3} "
            f"ends at sentence: {'yes' if ends_at_sentence else 'NO':<3} "
            f"| {label}"
        )

    print(f"\n-> {ok} of {len(sample)} sampled chunks pass all three checks")
    print(f"-> produced by chunker.py::split_documents")
    return ok


if __name__ == "__main__":
    criterion_1()
    criterion_4()

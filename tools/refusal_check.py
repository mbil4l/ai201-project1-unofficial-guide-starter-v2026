#!/usr/bin/env python3
"""
Does a refusal name a source?

    python tools/refusal_check.py --variant by_place

Criterion 2 caught this once, by accident, on a question that was supposed to
be answerable. The question below is not one of my five. It passes the
relevance gate, so it reaches the model, and the corpus does not answer it: the
guides say the overflow lot at Halden Bay is a 12-minute walk up a hill and
never say what it costs. That is the shape of question that lands in the
refusal branch of GROUNDING_INSTRUCTION, which asks the model to name a file
for each claim and says nothing about naming one when there are no claims.

Three runs, caching off, so the answers are three real answers. Reading them is
the measurement.
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import config

QUESTION = "How much does it cost to park in the overflow lot at Halden Bay?"


def main():
    import gate
    from store import search
    from generate import answer_from_chunks

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--variant", default="by_place")
    parser.add_argument("--runs", type=int, default=3)
    parser.add_argument("--question", default=QUESTION)
    args = parser.parse_args()

    print(f"{args.question}\n")

    for run in range(1, args.runs + 1):
        results = search(
            args.question, top_k=config.TOP_K, corpus=config.CORPUS, variant=args.variant
        )
        decision = gate.check(results, threshold=config.THRESHOLD)

        if not decision.passed:
            print(f"run {run}: the gate refused at {decision.best_distance:.4f}, "
                  f"so the model was never asked")
            continue

        answer = answer_from_chunks(args.question, results, cache=False)
        named = sorted({r.source for r in results if r.source in answer})
        print(f"run {run} (best distance {decision.best_distance:.4f}, "
              f"sources named: {', '.join(named) or 'none'})")
        print(f"  {answer}\n")


if __name__ == "__main__":
    main()

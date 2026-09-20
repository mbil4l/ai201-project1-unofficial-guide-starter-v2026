"""
Your test questions.

Milestone 2 asks you to write five questions your system should be able to
answer from your corpus, specific enough to have a right answer.

  ✗ "What are good dining halls?"          — no right answer
  ✓ "What do students say about wait times at Commons during lunch?"

Fill in `QUESTIONS` below. `expects` is a word or short phrase you'd expect a
correct answer to contain — you'll use it in unit 2 when you build a scorer,
and having written it now means you decided what "correct" meant before you saw
any results.

`OUT_OF_SCOPE` holds five questions your documents clearly don't cover. You
need these in Milestone 4 to find where your relevance cutoff belongs, and
again in unit 2, where `run_eval.py` runs them through the gate and writes what
happened into your run log — that's the evidence for criterion 3.

Swap them for your own if you like. Keep five of them either way: criterion 3
names a target of "4 of 5", and four of three is not a thing.
"""

QUESTIONS = [
    # guide_halden_bay.md, and repeated in guide_regional_transport.md and
    # guide_seasons.md — three documents say it, so this one should be easy.
    {
        "question": "By what time do the car parks in Halden Bay fill up on a summer weekend?",
        "expects": "10am",
    },
    # guide_kestrelford.md and guide_eating.md. Two serving windows, so a
    # correct answer has to give the evening one and not just "lunchtime".
    {
        "question": "What hours do the pubs in Kestrelford serve food?",
        "expects": "8:30",
    },
    # guide_accessibility.md names it "the easiest town in the region";
    # guide_walking.md calls it "the region's most accessible town on foot".
    # Phrased as a recommendation, but the corpus gives it one right answer.
    {
        "question": "Which town in the region is easiest to get around with limited mobility?",
        "expects": "Thornby Wells",
    },
    # guide_elder_ness.md "Getting there", echoed in guide_walking.md. One
    # sentence buried in a paragraph about a village of 300 — this is the one I
    # expect to miss, which is why criterion 1 says 4 of 5 and not 5 of 5.
    {
        "question": "How often does the access road to the Elder Ness headland flood, and for how long?",
        "expects": "Six times a year",
    },
    # guide_seasons.md plus guide_brightwater.md "When to go". A why question
    # rather than a lookup: the answer is the university emptying out, which
    # inverts the usual summer pattern for the rest of the region.
    {
        "question": "Why does Brightwater get quiet in July and August when the rest of the region is busy?",
        "expects": "students",
    },
]

# Questions from a different world entirely. Your gate should refuse all five.
#
# There are five of these because criterion 3 in criteria.md names a target of
# "at least 4 of 5" — you need five things to try before you can report 4 of 5.
# `run_eval.py` runs these through retrieval and the gate on every eval and
# records what happened, so criterion 3 has evidence in the run log alongside
# the others. They cost no model calls: a refusal never reaches the model.
OUT_OF_SCOPE = [
    "What is the capital of Mongolia?",
    "How do I change the oil in a diesel engine?",
    "Who won the 1992 World Cup?",
    "What is the recommended dosage of ibuprofen for a headache?",
    "How do I write a for loop in Rust?",
]


def answered() -> list[dict]:
    """The questions you've actually filled in."""
    return [q for q in QUESTIONS if q.get("question", "").strip()]

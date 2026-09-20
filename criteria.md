# Acceptance criteria — The Unofficial Guide

Five criteria that say what "working" means for this system, written in unit 1
**before** any results existed.

An acceptance criterion names a target: a number, a count, a rate, or something
a person could plainly observe. *"Retrieval works"* is an opinion. *"For at
least 4 of my 5 test questions, the top results include a chunk containing the
answer"* is a criterion.

Under each one, write a sentence or two on **why that target** and not a
stricter or looser one. A reason that says something about your corpus or your
pipeline earns credit; *"80% seemed reasonable"* does not.

> Missing your own targets next unit costs you nothing. Setting a target so
> easy you can't miss it does.

---

## 1. Retrieved chunks contain the answer

For at least 4 of my 5 test questions, the retrieved chunks include one that
contains the answer.

**Why this target:**
4 of 5 rather than 5 of 5 because one of my questions is deliberately harder
than the rest. "How often does the access road to the Elder Ness headland
flood?" rests on a single sentence in the "Getting there" paragraph of
`guide_elder_ness.md` — a guide to a village of 300 — and is echoed in only one
other document. At the starter's 800-character chunk size that sentence sits
mid-window, surrounded by unrelated transport detail about bus services and
parking. I expect it to be the one that misses. My other four questions are
each stated in two or more documents.

---

## 2. Every answer names a source

Every answer the system produces names at least one source document.

**Why this target:**
All five, because attribution here does not depend on retrieval being good —
only on the model following an instruction. `generate.py::build_prompt` labels
every chunk it passes in as `[from <filename>]`, and the filename is asked for
twice: once in `GROUNDING_INSTRUCTION` and again in the prompt's closing line.
The model never has to infer a source, it only has to repeat one it was handed.
So the only way this fails is the model dropping the citation from otherwise
sound prose, and a target of 4 of 5 would just be excusing that in advance.

---

## 3. The relevance gate stops out-of-corpus questions

When I ask a question my documents clearly don't cover, the relevance gate
stops it and the system returns "I don't have enough information about that" —
in at least 4 of 5 tries.

<!-- The five questions are the ones in `OUT_OF_SCOPE` at the bottom of
     `questions.py`, and `run_eval.py` puts them through the gate and writes
     what happened into your run log. Swap them for your own if you'd rather —
     just keep five of them, or the "4 of 5" above has nothing to be 4 of. -->

**Why this target:**
I have not measured my distances yet — that is Milestone 4, and `THRESHOLD` is
still the starter's default of 0.6. I am writing 4 of 5 rather than 5 of 5
because one of my out-of-scope questions is not as far out as the other four:
"What is the recommended dosage of ibuprofen for a headache?" shares vocabulary
with the practical-notes section that closes almost every guide in my corpus,
which talks about the nearest full hospital and minor injuries units with
limited hours. I expect that question to land closest to my documents and to be
the one that slips through.

---

## 4. Each chunk holds exactly one section

No chunk contains text from more than one `##` section of a guide, and in a
sample of 10 chunks printed by `app.py chunks`, all 10 begin at a heading and
end at a sentence boundary — no sentence cut in half at either end.

**Why this target:**
My 14 guides are already divided into 84 `##` sections — "Getting there", "Eat
and drink", "When to go" — and I measured them before writing this: the longest
is 708 characters, the median is 294, and not one reaches 800. So every section
already fits inside a single chunk at the current chunk size, and the sections
are the units the documents were actually written in. All five of my test
questions are answered inside one section rather than across two.

The starter's fixed 800-character window ignores that structure completely: a
2,100-character guide becomes three windows that each straddle two or three
section boundaries, so the Elder Ness flooding sentence ends up in the same
chunk as unrelated parking detail. "Right size" for this corpus therefore means
one section, and the observable version of that claim is where the boundaries
land.

I am asking for 10 of 10 rather than 8 of 10 because once the split is on
headings it is deterministic — if a chunk straddles a boundary, the rule is not
actually the rule, and a near miss would tell me I had a bug rather than a
tuning problem.

One thing I considered and rejected: a minimum chunk length. Five of my 84
sections are under 200 characters — `guide_thornby_wells.md` "Where to stay" is
173 — and each is a complete, answerable thought. A length floor would be the
wrong rule for this corpus, and I would rather say so now than discover it in
Milestone 3.


---

## 5. A clear margin between in-scope and out-of-scope questions

All five of my in-scope questions pass the relevance gate, and the *largest*
best-distance among them is at least 0.10 below the *smallest* best-distance
among my five `OUT_OF_SCOPE` questions.

**Why this target:**
Criterion 3 only pushes in one direction. A cutoff of 0.0 would refuse all five
out-of-scope questions, score a perfect 5 of 5, and leave me with a system that
answers nothing. This is the criterion that pushes back the other way, and the
two of them together are what Milestone 4 means by putting the cutoff in the
gap rather than at a number I liked.

I am asking for a margin rather than just "all five pass" because a threshold
that works with 0.002 of room is one I got lucky with, not one I measured. On a
distance scale where 0.3 is a close match and 0.9 is unrelated, 0.10 is enough
room for the cutoff to sit in the middle of the gap instead of balanced on the
edge of it.

This is measurable straight off the run log: `run_eval.py` already prints
`best_distance` for every in-scope question and for every out-of-scope one, in
the same file. And it can genuinely be missed — my corpus is 14 documents about
travel logistics in one region, so the two groups are not guaranteed to
separate cleanly, and the ibuprofen question in particular is not obviously far
away from a paragraph about minor injuries units.


---

<!-- ─────────────────────────────────────────────────────────────────────────
     UNIT 2 — read this before you change anything above.

     If a criterion turns out to be BROKEN rather than merely unmet, you can
     revise it, and that earns credit. But never delete or edit the original
     line. Add the revision underneath it, like this:

         ## 1. Retrieved chunks contain the answer

         For at least 4 of my 5 test questions, the retrieved chunks include
         one that contains the answer.

         **Why this target:** ...

         > **Revised in unit 2:** For at least 4 of 5 questions, the top three
         > results contain the answer.
         >
         > **Why revised:** I couldn't judge "the chunks include one that
         > contains the answer" the same way twice — I scored two questions
         > differently on Monday than on Wednesday. The new version is
         > something I can actually check.

     That's a revision because the criterion couldn't be MEASURED.

     Lowering a target because you missed it is not a revision, and it costs
     you the point:

         ✗ "I said 4 of 5 but got 2 of 5, so 2 of 5 is more realistic."

     A number you missed stays where it is, gets diagnosed, and gets a fix
     attempted. That's where the points are.

     The whole reason the originals stay visible is so someone can see what you
     said before you knew the answer.
     ───────────────────────────────────────────────────────────────────────── -->

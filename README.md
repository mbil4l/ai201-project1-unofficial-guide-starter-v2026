# The Unofficial Guide

<!-- Replace this line with your name and which corpus you picked. -->

> **This file is your submission.** Fill it in as you go — most sections get
> written during the milestone that produces them, not at the end.
>
> How the starter works, and every command you'll need, is in `RUNNING.md`.
> Leave that file alone.
>
> **Paste everything as text.** No screenshots, no video. A typed table gets
> full credit; a picture of the same table gets none.
>
> Delete these instruction blocks as you replace them. The `<!-- -->` comments
> are notes to you and don't show up when the page renders — you can leave them
> or remove them.

---

# Unit 1

## What This Does

<!-- Three or four sentences. Which corpus you picked, and the kinds of
     questions your system answers. Write it for someone who has never seen
     this repo.

     Milestone 5. -->

## Chunking Strategy

**Chunk size:** one `##` section per chunk — 183 to 758 characters, 319 on
average. `CHUNK_SIZE = 1100` is a ceiling, not a window.
**Overlap:** 0.

My 14 documents are sectioned guides, not posts. Each one is a town or a theme
divided under `##` headings — "Getting there", "Eat and drink", "When to go" —
and when I measured them there were 84 such sections with a median of 294
characters and a longest of 708. Not one reached 800. The author had already
chunked these documents; the starter's 800-character window was overriding that
with an arbitrary number.

What that cost, measured before I changed anything:

| | starter (`fallback_split`, 800/120) | mine (`split_documents`) |
|---|---|---|
| chunks | 51 | 94 |
| average length | 650 | 319 |
| shortest | 24 | 183 |
| longest | 800 | 758 |
| spanning more than one heading | 37 of 51 | **0 of 94** |
| ending at a sentence end | 18 of 51 | **94 of 94** |

The 24-character chunk was `'d Sundays and after 5pm.'`, the leftover tail of a
document that didn't divide evenly. `guide_elder_ness.md#0` ended mid-word on
`## Eat and drin` and held four topics at once, including the road-flooding
sentence one of my test questions depends on.

**The part I got wrong first time.** My initial plan was just "split on `##`",
and reading the output showed that isn't enough. `guide_elder_ness.md` "Where
to stay" reads *"The pub has four rooms and the observatory has dormitory
accommodation…"* — it never says Elder Ness. Sections in these guides are
topically self-contained but not *referentially* self-contained, so a bare
section is a complete thought about nowhere in particular and retrieval would
happily return the right kind of paragraph about the wrong town. Every chunk
therefore starts with a `Town — Section` label. That label is the difference
between a chunk that stands alone and one that only looks like it does.

Overlap is 0 because overlap exists to stop a thought being cut in half, and
splitting at headings already guarantees that. Keeping the starter's 120
characters would duplicate text and let near-identical chunks compete for the
same five `TOP_K` slots.

`CHUNK_SIZE` is a ceiling so the strategy degrades sensibly on a corpus that
needs it: a section over 1100 characters is cut at paragraph breaks, then at
sentence ends, never mid-word. On `city_guides` nothing triggers it.

**Effect on retrieval.** All five test questions now retrieve a chunk
containing the answer within `TOP_K=5`, against a criterion-1 target of 4 of 5.
The Elder Ness question I had predicted would be the one to miss went from
buried mid-window to rank 1 at distance 0.289.

## Sample Chunks

Printed by `python app.py chunks -n 5`, spread across the corpus. Read against
the question "could someone answer a question using only this?" — four yes, one
no, discussed underneath.

**Chunk 1** — source: `guide_accessibility.md#0` — produced by: `chunker.py::split_documents`

```
Getting around the region with limited mobility — Overview

An honest assessment rather than a promotional one. Some of these places are
difficult and it is better to know in advance.
```

**Chunk 2** — source: `guide_corry_vale.md#5` — produced by: `chunker.py::split_documents`

```
Corry Vale — Where to stay

Perhaps thirty beds in the entire valley, spread across two pubs and a handful of farmhouse rooms. In summer these are booked months ahead. Camping is permitted on two marked fields and nowhere else.
```

**Chunk 3** — source: `guide_givens_mill.md#2` — produced by: `chunker.py::split_documents`

```
Givens Mill — Getting around

Everything is on one street along the river. The mill is at one end and the church at the other, eight minutes apart. The riverside path continues in both directions for as far as you want to walk.
```

**Chunk 4** — source: `guide_kestrelford.md#4` — produced by: `chunker.py::split_documents`

```
Kestrelford — What to see

The market square on a Saturday morning is the main event and has run continuously since the 1400s. The parish church has a 13th-century tower you can climb for £2. The old trackbed walk runs six miles to the next village along an easy gradient and is the best half-day here.
```

**Chunk 5** — source: `guide_pellew_sands.md#6` — produced by: `chunker.py::split_documents`

```
Pellew Sands — When to go

June and September for the beach without the crowds. July and August are busy and the town is at its most itself, for better and worse. Winter is bleak, largely closed, and has a following among people who like that sort of thing.
```

### Reading them

Chunks 2 through 5 pass. Each names its own place, holds one topic, and carries
facts someone could answer from — thirty beds across two pubs; eight minutes
end to end; £2 for the tower; June and September for the beach.

**Chunk 1 fails, and it is the interesting one.** It is a complete thought and
it ends at a sentence boundary, so it satisfies criterion 4 — but it answers no
question at all. It is editorial framing, not content. It exists because my
chunker turns the paragraph before a document's first `##` into an "Overview"
chunk, which is right for the ten town guides (*"Elder Ness is a headland with
a village of 300 on it, a lighthouse, a bird observatory"* — population and
description, worth retrieving) and wrong for a thematic guide whose opening
paragraph is just a preface.

It does measurable harm. On my third test question — *"Which town in the region
is easiest to get around with limited mobility?"* — this framing chunk ranks
**1st at distance 0.386**, while `guide_accessibility.md#1`, the chunk that
actually names Thornby Wells as the easiest town, ranks **4th at 0.549**. The
question still passes criterion 1 because rank 4 is inside `TOP_K=5`, but a
content-free chunk is taking the top slot and would beat the real answer
outright at `TOP_K=3`.

I chose not to fix it in this milestone. The obvious rule — merge a preamble
shorter than about 150 characters into the section after it — would work: this
preamble is 123 characters and the next shortest of the ten is 187. But it
would be a rule fitted to a single outlier, which is the same mistake I talked
myself out of when I rejected a 200-character minimum length in `criteria.md`.
It is written down here instead as the candidate for unit 2's "fix one thing
and re-run", where I already have the before-number to beat: answer chunk at
rank 4, framing chunk at rank 1.

## Sample Answer

<!-- One complete question and answer, pasted as text, with the source line
     visible. Milestone 4. -->

**Question:**

**Answer:**

```
```

**My relevance cutoff:**

<!-- The number you set in config.py, and how you got there.

     You ran five questions your corpus covers and the five in OUT_OF_SCOPE
     that it clearly doesn't, and wrote down the best distance for each. What
     did those two groups look like? Where was the gap? Put the actual numbers
     here — the table below wants all ten rows.

     Milestone 4. -->

| Question | In corpus? | Best distance |
|---|---|---|
|  |  |  |

## How I Used AI

<!-- Two specific moments. For each: what you asked for, what came back, and
     what you changed about it.

     "I asked Claude to write the chunking function from my notes. It ignored
     the overlap, so I added that myself" is the level of detail we're after.
     "I used AI to help me code" is not.

     Milestone 5. -->

**1.**

**2.**

<!-- ── Stretch features ─────────────────────────────────────────────────────
     Doing one? Say so here BEFORE you start. A feature this README never
     claims earns nothing.
     ───────────────────────────────────────────────────────────────────────── -->

---

# Unit 2

<!-- These sections get ADDED to what's already above. Don't delete or rewrite
     unit 1 — the point is that someone can see what you said before you knew
     how it went. -->

## Run Log — Before

<!-- Your five criteria, three runs each. `python run_eval.py --label before`
     runs the questions, puts the OUT_OF_SCOPE ones through the gate, and
     writes it all into results/ for you. Targets come from criteria.md; the
     verdict column is your call.

     Criterion 3 is measured in one deterministic pass rather than three, so
     the same number goes in all three run columns. That's correct, not lazy.

     Milestone 1. -->

| Criterion | Target | Run 1 | Run 2 | Run 3 | Verdict |
|---|---|---|---|---|---|
| 1. Retrieved chunk contains the answer | 4 of 5 |  |  |  |  |
| 2. Every answer names a source | 5 of 5 |  |  |  |  |
| 3. Gate stops out-of-corpus questions | 4 of 5 |  |  |  |  |
| 4. | | | | | |
| 5. | | | | | |

<!-- Underneath, paste the REAL output for each criterion from one of your
     runs — the actual text your system produced, not a description of it.
     Name the file and function that produced it. -->

## Verdicts

<!-- MET or MISSED for each of the five, against the target you wrote last
     unit — not a new one. Plus a sentence on how you decided. That sentence
     matters most where it was close.

     If your target said 4 of 5 and your runs came out 4, 3, 4, that's a MISS.
     The target has to hold, not show up occasionally.

     Milestone 2. -->

| # | Criterion | Verdict | How I decided |
|---|---|---|---|
| 1 |  |  |  |
| 2 |  |  |  |
| 3 |  |  |  |
| 4 |  |  |  |
| 5 |  |  |  |

## Diagnoses

<!-- For each miss: which stage caused it, and how. The stage alone isn't
     enough — you need the mechanism.

     Not a diagnosis: "Question 3 didn't work."
     A diagnosis:     "Question 3 asks about laundry costs. The answer is in
                       one sentence that got split across two chunks, so
                       neither chunk on its own contains it."

     The five stages: loading → chunking → embedding → retrieval → generation.

     Look for a pattern. If three misses all ask about numbers, that's one
     problem, not three.

     Missed nothing? Say so, then say honestly whether your targets were set
     low, and which one you'd tighten and to what.

     Milestone 3. -->

## The Improvement

**What I changed:**

**Why I picked it:**

<!-- Connect it to a specific diagnosis above in one sentence. If you can't,
     you picked a fix because it sounded impressive. -->

### Run Log — After

<!-- Same format, same five criteria, three runs each.
     `python run_eval.py --label after` -->

| Criterion | Target | Run 1 | Run 2 | Run 3 | Verdict |
|---|---|---|---|---|---|
| 1. Retrieved chunk contains the answer | 4 of 5 |  |  |  |  |
| 2. Every answer names a source | 5 of 5 |  |  |  |  |
| 3. Gate stops out-of-corpus questions | 4 of 5 |  |  |  |  |
| 4. | | | | | |
| 5. | | | | | |

**Did it help?**

<!-- Say plainly whether it did, and how you know. If it made things worse,
     say that — a change that backfired, honestly reported, earns full credit
     and is more interesting than one that worked. What matters is that you can
     tell.

     Milestone 4. -->

## What's Still Broken

<!-- For each criterion still missed after your fix: what you'd do about it,
     and why you stopped where you did.

     "I ran out of time" is fine if it's true. Pretending nothing is left is
     not.

     Milestone 5. -->

## What I'd Do Differently

<!-- Knowing what you know now — which of your five criteria would you write
     differently, and why?

     Milestone 5. -->

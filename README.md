# The Unofficial Guide

**YOUR NAME HERE** — corpus: `city_guides`

<!-- ^ replace the name; the corpus is filled in. -->

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

This is a question-answering system over the `city_guides` corpus: 14 travel
guides to one fictional region, covering ten towns — Brightwater, Halden Bay,
Kestrelford, Elder Ness and others — plus four region-wide guides on eating,
walking, seasons, transport and accessibility. Ask it a specific logistical
question about the region and it retrieves the relevant sections and answers
from them, naming the file each claim came from.

It handles questions with a definite answer somewhere in the documents: what
hours the pubs in Kestrelford serve food, by what time the Halden Bay car parks
fill on a summer weekend, how often the Elder Ness access road floods. It is
not a recommendation engine — "where should I go on holiday?" has no answer in
these documents, and the system is built to say so rather than improvise. When
retrieval comes back with nothing close enough, a relevance gate refuses the
question before the model ever sees it.

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

**Question:** How often does the access road to the Elder Ness headland flood, and for how long?

**Answer:**

```
  (best distance 0.289, cutoff 0.72)

The access road to the Elder Ness headland floods roughly six times a year at
the highest spring tides, for about two hours either side of high water
(*guide_elder_ness.md* and *guide_walking.md*).

Sources retrieved: guide_elder_ness.md, guide_walking.md
```

Grounded: every number in it — six times a year, two hours either side — is in
the retrieved chunks, and both files that carry the fact are named rather than
just the first one.

**Top-k:** 5, unchanged, but now on measurement. Across my five questions the
deepest rank at which the answer chunk appears is 4 (the accessibility
question), so 5 leaves one slot of headroom. Going to 6-8 adds only loosely
related material — on my Brightwater question, ranks 6, 7 and 8 are other
Brightwater sections at 0.45-0.50 that share the town name and nothing else.
Dropping to 4 would leave zero headroom on the question that already needs the
deepest reach.

**My relevance cutoff:** `THRESHOLD = 0.72`.

| Question | In corpus? | Best distance |
|---|---|---|
| What hours do the pubs in Kestrelford serve food? | yes | 0.158 |
| By what time do the car parks in Halden Bay fill up on a summer weekend? | yes | 0.283 |
| How often does the access road to the Elder Ness headland flood, and for how long? | yes | 0.289 |
| Why does Brightwater get quiet in July and August when the rest of the region is busy? | yes | 0.314 |
| Which town in the region is easiest to get around with limited mobility? | yes | 0.386 |
| What is the capital of Mongolia? | no | 0.810 |
| What is the recommended dosage of ibuprofen for a headache? | no | 0.835 |
| How do I write a for loop in Rust? | no | 0.861 |
| How do I change the oil in a diesel engine? | no | 0.881 |
| Who won the 1992 World Cup? | no | 0.963 |

Two clean groups — 0.158-0.386 and 0.810-0.963 — with a gap of 0.42 between
them. The starter's 0.6 sits inside it, and if I had stopped here I would have
kept 0.6 and called the milestone done.

**Why I didn't.** My five questions are a sample I wrote myself, using the
corpus's own vocabulary, so they are unrepresentatively easy. I ran ten more
questions the corpus genuinely answers, phrased the way a visitor would ask:

| Loosely phrased, still answerable | Best distance |
|---|---|
| Can I get a train to Kestrelford? | 0.349 |
| Which places close out of season? | 0.461 |
| Is it worth visiting in winter? | 0.540 |
| Is the region wheelchair friendly? | 0.544 |
| What time do things shut? | 0.585 |
| What's the food like? | 0.601 |
| Somewhere quiet with good walks and no cars | 0.611 |
| Where should I go if I want to avoid crowds? | 0.625 |
| Do I need cash? | 0.637 |
| How bad is the parking? | 0.639 |

**At 0.6, five of those ten are refused** — including "Do I need cash?", which
nine of my guides answer in their Practical notes, and "How bad is the
parking?", which is the defining feature of a visit to Halden Bay. That is the
"too low" column of the trade-off table happening on real questions, and my
five test questions could never have shown it to me.

So the real in-scope range is 0.158-0.639 and the out-of-corpus range is
0.810-0.963. **0.72 is the midpoint of 0.639 and 0.810.** It keeps all ten
loose questions and still refuses all five out-of-corpus ones with 0.09 to
spare.

### What the cutoff cannot do

The gap above only exists because `OUT_OF_SCOPE` is from a different world
entirely. I tested eight travel questions in the *same* domain that these 14
documents cannot answer:

| Near-miss out-of-scope | Best distance | Top chunk retrieved |
|---|---|---|
| Does Elder Ness have a hospital on the headland? | 0.311 | Elder Ness — Where to stay |
| Is there a cinema in Kestrelford? | 0.366 | Kestrelford — Where to stay |
| How do I get to the airport at Halden Bay? | 0.427 | Halden Bay — Getting around |
| What are the opening hours of the Brightwater aquarium? | 0.437 | Brightwater — Getting there |
| Where is the best pub in Brighton? | 0.478 | Corry Vale — Eat and drink |
| How much is a taxi from Marchwood to Heathrow? | 0.482 | Marchwood — Getting there |
| What time does the train to Edinburgh leave? | 0.543 | Kestrelford — Getting there |
| Which beach in Cornwall has the best surfing? | 0.576 | Getting around the region — Walking and cycling |

These run 0.311-0.576, which is *inside* the legitimate in-scope range and
mostly *below* it. "Does Elder Ness have a hospital on the headland?" scores
0.311 — closer than four of my five real test questions, and there is no
aquarium in Brightwater, no cinema in Kestrelford and no airport at Halden Bay.

**No cutoff separates these from real questions,** because distance measures
topical similarity, not whether the answer is present. A question about the
right town in the right region retrieves that town's chunks whatever it asks.
Lowering the cutoff to catch them would refuse most of the legitimate questions
above first. This is the line in the brief made concrete: the gate catches the
clear misses, and the near ones have to be caught by the second layer.

### Grounding

`GROUNDING_INSTRUCTION` in `generate.py` was not strict enough, and it took a
targeted probe to show it. The cinema question it handled correctly — *"there is
no mention of a cinema in Kestrelford, so I don't have enough information
(guide_kestrelford.md)"*. The failure is on disagreement.

Nine of my 14 guides repeat the same Practical-notes boilerplate, *"The nearest
full hospital is in Brightwater"* — including `guide_brightwater.md` itself,
which is nonsense — while `guide_accessibility.md` says *"The nearest full
hospital is in Marchwood."* The corpus contradicts itself, and the original
instruction had no rule for that.

Asked "Where is the nearest full hospital if I am staying in Kestrelford?", with
both files among the retrieved chunks:

```
Before:
According to `guide_kestrelford.md`, the nearest full hospital is in Brightwater.

After:
If you are staying in Kestrelford, the nearest full hospital is in Brightwater
(according to `guide_kestrelford.md`). However, `guide_accessibility.md` states
that the nearest full hospital is in Marchwood.
```

The "before" is the dangerous kind of wrong: fluent, correctly formatted, citing
a real file that really does say that, and hiding the fact that the corpus does
not agree with itself. Nothing in the output marks it as a problem.

I added four rules, each answering a failure I measured rather than a general
worry:

- **Name the file for each claim, and both files if there are two.** The
  "before" answer cited one file while drawing on four.
- **A fact about one place is not a fact about another.** Ten town guides carry
  identically-named sections, so retrieval reliably returns the right town for a
  topic that town's guide never covers.
- **If the documents name the place but never mention the thing asked about, say
  so rather than substituting the closest related fact.** This is the near-miss
  table above, turned into a rule instead of luck.
- **If two excerpts disagree, say they disagree and give both.** The hospital
  case.

## How I Used AI

Mostly for drafting code and measurement scripts from what I had already
decided I wanted. The two moments worth writing down are both ones where what
came back looked correct and wasn't.

**1. The chunker that split on headings and lost the town name.**

I asked for a replacement for `split_documents` based on what I had found
reading the corpus: the guides are already divided into `##` sections, 84 of
them, median 294 characters, none over 800, so the sections should be the
chunks. What came back did exactly that, and the summary line looked like a
clear win — 94 chunks, nothing cut mid-sentence, no chunk spanning two
headings, against the starter's 51 chunks of which 37 straddled a heading.

Then I printed five chunks and read them, which is what Milestone 3 actually
asks for. `guide_elder_ness.md` "Where to stay" reads *"The pub has four rooms
and the observatory has dormitory accommodation…"* and never says Elder Ness.
Nor does "Where to stay" in any of the other nine town guides. Splitting on
headings had produced 94 complete thoughts about nowhere in particular, and
because every town guide uses the same section names, a question about one town
would have happily matched another town's paragraph.

What I changed: every chunk now starts with a `Town — Section` label, taken
from the document's `# Title` line, and the character budget subtracts the
label so the ceiling still holds. That one line is the difference between a
chunk that stands alone and one that only looks like it does, and the summary
statistics could not have told me which I had.

**2. A verification script that was stricter than my own criterion.**

I asked for a script to check criterion 1 — "for at least 4 of my 5 test
questions, the retrieved chunks include one that contains the answer" — against
the `expects` strings I had written in Milestone 2. What came back tested
whether `expects` appeared in the **top 3** results and reported my
accessibility question as a failure, 4 of 5.

I nearly wrote that down. But criterion 1 says "the retrieved chunks", and what
the system actually retrieves is `TOP_K`, which is 5. The script had invented a
stricter standard than the criterion it claimed to be measuring, and I would
have recorded a MISS that my own target does not call a miss.

What I changed: the script now reads `config.TOP_K` instead of a hard-coded 3.
The real result is 5 of 5, with the accessibility question passing at rank 4.
The underlying weakness was real and I kept it in the write-up — a content-free
chunk holds rank 1 on that question while the chunk naming Thornby Wells sits
at rank 4 — but it is a rank-ordering problem, not a criterion-1 failure, and
those get diagnosed differently. Since then I have checked measurement scripts
against the wording of the criterion they are supposed to be testing, not
against what sounds rigorous.

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

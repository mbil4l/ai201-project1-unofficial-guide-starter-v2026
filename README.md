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

Three runs, caching off, `python run_eval.py --label before`. Everything below
comes from [`results/run_2026-09-27_1611_before.md`](results/run_2026-09-27_1611_before.md)
except criteria 1 and 4, which are not in that file because neither is about
the generated answer — those come from `tools/verify_criteria.py`.

| Criterion | Target | Run 1 | Run 2 | Run 3 | Verdict |
|---|---|---|---|---|---|
| 1. Retrieved chunk contains the answer | 4 of 5 | 4/5 | 4/5 | 4/5 | MET |
| 2. Every answer names a source | 5 of 5 | 5/5 | 4/5 | 5/5 | MISSED |
| 3. Gate stops out-of-corpus questions | 4 of 5 | 5/5 | 5/5 | 5/5 | MET |
| 4. Each chunk holds exactly one section | 10 of 10 | 10/10 | 10/10 | 10/10 | MET |
| 5. Margin between in-scope and out-of-scope | at least 0.10 | 0.425 | 0.425 | 0.425 | MET |

Four of the five come out identical in all three columns, and only criterion 2
moves. That is the shape of the system rather than a shortcut: chunking,
embedding and retrieval are deterministic here, and the gate is a comparison
against a fixed number, so criteria 1, 3, 4 and 5 are measured once and the
number goes in all three columns. Criterion 2 is the only one that depends on
what the model writes, and it is the only one that varied — which is also why
it is the one that missed.

### Criterion 1 — retrieved chunks contain the answer · 4/5 · MET

`tools/verify_criteria.py::criterion_1`, which searches with `store.py::search`
at `config.TOP_K` = 5, looks for each question's `expects` string in the
retrieved chunk text, and prints the chunk so the match can be read rather than
trusted. Real output for the three questions worth looking at:

```
How often does the access road to the Elder Ness headland flood, and for how long?
  expects 'Six times a year': FOUND at rank 1
  * 1. 0.2890  guide_elder_ness.md          Elder Ness — Getting there
    2. 0.3825  guide_elder_ness.md          Elder Ness — Getting around
    3. 0.4071  guide_walking.md             Walking in the region — Serious, and weather-dependent
    4. 0.4347  guide_elder_ness.md          Elder Ness — When to go
    5. 0.4707  guide_elder_ness.md          Elder Ness — What to see

  the chunk that contains it:
  Elder Ness — Getting there

  A single road in, which floods at the highest spring tides roughly six times a year for about two hours either side of high water. Tide tables are posted at the turning and are worth reading. No public transport of any kind. Nearest station is Pellew Sands, 40 minutes by road.

Which town in the region is easiest to get around with limited mobility?
  expects 'Thornby Wells': FOUND at rank 4
    1. 0.3855  guide_accessibility.md       Getting around the region with limited mobility — Overview
    2. 0.4997  guide_accessibility.md       Getting around the region with limited mobility — Difficult
    3. 0.5348  guide_corry_vale.md          Corry Vale — Getting around
  * 4. 0.5491  guide_accessibility.md       Getting around the region with limited mobility — Straightforward
    5. 0.5526  guide_walking.md             Walking in the region — Moderate, with hills

Why does Brightwater get quiet in July and August when the rest of the region is busy?
  expects 'students': string matched at rank 1, REJECTED on reading
  why: `guide_brightwater.md` — When to go matches on 'students', but it says the
  students are gone in MAY AND JUNE and that July and August are 'quiet to the
  point of being dull'. It never connects the two. The chunk that does —
  `guide_seasons.md` — Summer, 'Brightwater goes quiet to the point of dullness
  with the university empty' — is at rank 12, distance 0.5185, nowhere near top-k.
    1. 0.3136  guide_brightwater.md         Brightwater — When to go
    2. 0.3513  guide_seasons.md             When to visit the region — Autumn, September to November
    3. 0.3974  guide_regional_transport.md  Getting around the region — The railway
    4. 0.4218  guide_seasons.md             When to visit the region — Winter, December to February
    5. 0.4370  guide_brightwater.md         Brightwater — Getting there

-> 4 of 5 questions had the answer in the retrieved chunks
```

The Elder Ness question is the one criterion 1 was written around — I said in
unit 1 that it was the one I expected to miss, and after the heading-split
chunker it comes back at rank 1. The question that misses instead is
Brightwater, and it took reading to see it.

**The rejected match is the part worth reporting.** My first pass at this
scored 5 of 5, because `expects` for the Brightwater question is the single
word `students` and a retrieved chunk contains it. Reading that chunk says
otherwise: it puts the students leaving in *May and June*, calls July and
August dull, and never joins the two into a reason. The sentence that is
actually the answer — *"Brightwater goes quiet to the point of dullness with
the university empty"* in `guide_seasons.md` "Summer" — sits at rank 12, and
`Brightwater — Overview` ("roughly doubling in term time … the answer turned
out to be the university") at rank 8. Neither is within top-k, so neither
reached the model, which is why all three runs answered that the documents do
not explain it.

`expects` is a proxy for "contains the answer", written in Milestone 2 before I
had seen any results, and on this question the proxy and the criterion
disagree. The criterion wins. `tools/verify_criteria.py` now carries that
judgement in `READ_AND_REJECTED` with the reason, so re-running it reproduces 4
of 5 rather than quietly going back to 5.

The accessibility question is the other one worth watching, and it passes:
the chunk naming Thornby Wells is at rank 4, behind an overview section that
names no town at all. Inside the criterion as written, but a rank-ordering
weakness rather than a clean pass.

### Criterion 2 — every answer names a source · 5/5, 4/5, 5/5 · MISSED

`generate.py::answer_from_chunks`, logged by `run_eval.py::main`. Fourteen of
fifteen answers named a file. The one that did not is run 2 of the Brightwater
question:

```
### Why does Brightwater get quiet in July and August when the rest of the region is busy? — run 2

- Best distance: 0.3136 (passed the gate)
- Sources retrieved: guide_brightwater.md, guide_regional_transport.md, guide_seasons.md

The provided documents do not explain why Brightwater gets quiet in July and August, nor do they state that the rest of the region is busy during those months.
```

Runs 1 and 3 of the same question refuse in the same way but do cite the file:

```
### Why does Brightwater get quiet in July and August when the rest of the region is busy? — run 3

The provided documents do not mention why the rest of the region is busy, nor do they state that the rest of the region is busy during July and August; they only state that July and August in Brightwater are "quiet to the point of being dull" (*guide_brightwater.md*).
```

Against a target of 5 of 5 that is a miss, and 4/5 in one run out of three is
exactly the case criteria.md said a target of 4 of 5 would have excused in
advance. For contrast, a passing answer from the same run:

```
### What hours do the pubs in Kestrelford serve food? — run 2

The pubs in Kestrelford serve food between 12 and 2 and again between 6 and 8:30 (guide_kestrelford.md and guide_eating.md).
```

### Criterion 3 — the gate stops out-of-corpus questions · 5/5 · MET

`run_eval.py::check_out_of_scope`, cutoff 0.72, one deterministic pass:

```
Out-of-scope questions (the gate should refuse these):
  refused  (best distance 0.810)  What is the capital of Mongolia?
  refused  (best distance 0.881)  How do I change the oil in a diesel engine?
  refused  (best distance 0.963)  Who won the 1992 World Cup?
  refused  (best distance 0.835)  What is the recommended dosage of ibuprofen for a headache?
  refused  (best distance 0.861)  How do I write a for loop in Rust?
  -> gate refused 5 of 5
```

The ibuprofen question is the one I named in unit 1 as the likely leak, on the
grounds that it shares vocabulary with the minor-injuries paragraphs. It came
back at 0.835 — closer than the World Cup question at 0.963, so the reasoning
held, but nowhere near the 0.72 cutoff.

### Criterion 4 — each chunk holds exactly one section · 10/10 · MET

`tools/verify_criteria.py::criterion_4` over the chunks from
`chunker.py::split_documents`, the same 10-chunk sample `app.py chunks` prints:

```
# 94 chunks total, sampling 10 spread across the corpus

 1. guide_accessibility.md#0   one section: yes  starts at heading: yes  ends at sentence: yes  | Getting around the region with limited mobility — Overview
 2. guide_brightwater.md#4     one section: yes  starts at heading: yes  ends at sentence: yes  | Brightwater — What to see
 3. guide_corry_vale.md#5      one section: yes  starts at heading: yes  ends at sentence: yes  | Corry Vale — Where to stay
 4. guide_elder_ness.md#1      one section: yes  starts at heading: yes  ends at sentence: yes  | Elder Ness — Getting there
 5. guide_givens_mill.md#2     one section: yes  starts at heading: yes  ends at sentence: yes  | Givens Mill — Getting around
 6. guide_halden_bay.md#3      one section: yes  starts at heading: yes  ends at sentence: yes  | Halden Bay — Eat and drink
 7. guide_kestrelford.md#4     one section: yes  starts at heading: yes  ends at sentence: yes  | Kestrelford — What to see
 8. guide_marchwood.md#5       one section: yes  starts at heading: yes  ends at sentence: yes  | Marchwood — Where to stay
 9. guide_pellew_sands.md#6    one section: yes  starts at heading: yes  ends at sentence: yes  | Pellew Sands — When to go
10. guide_seasons.md#3         one section: yes  starts at heading: yes  ends at sentence: yes  | When to visit the region — Winter, December to February

-> 10 of 10 sampled chunks pass all three checks
```

### Criterion 5 — a clear margin between the two groups · 0.425 · MET

Both numbers are printed by `run_eval.py` into the same file — in-scope best
distances from `run_eval.py::run_once`, out-of-scope ones from
`run_eval.py::check_out_of_scope`:

```
By what time do the car parks in Halden Bay fill up on a summer weekend?   0.283
What hours do the pubs in Kestrelford serve food?                          0.158
Which town is easiest to get around with limited mobility?                 0.386   <- largest in-scope
How often does the access road to the Elder Ness headland flood?           0.289
Why does Brightwater get quiet in July and August?                         0.314

What is the capital of Mongolia?                                           0.810   <- smallest out-of-scope
What is the recommended dosage of ibuprofen for a headache?                0.835
How do I change the oil in a diesel engine?                                0.881
How do I write a for loop in Rust?                                         0.861
Who won the 1992 World Cup?                                                0.963
```

All five in-scope questions passed the gate, and the margin is 0.810 − 0.386 =
**0.425**, against a target of at least 0.10. The 0.72 cutoff sits inside that
gap with 0.334 of room below it and 0.090 above. The gap is wider than the
0.639/0.810 pair I set the cutoff from in Milestone 4, because the loosely
phrased questions that produced 0.639 are not among these five.

## Verdicts

<!-- MET or MISSED for each of the five, against the target you wrote last
     unit — not a new one. Plus a sentence on how you decided. That sentence
     matters most where it was close.

     If your target said 4 of 5 and your runs came out 4, 3, 4, that's a MISS.
     The target has to hold, not show up occasionally.

     Milestone 2. -->

Four MET, one MISSED, against the targets in `criteria.md` as written in unit 1.
No criterion is revised — all five measured what I meant them to measure, and
the one I missed I missed on the result, not on the measurement.

| # | Criterion | Verdict | How I decided |
|---|---|---|---|
| 1 | Retrieved chunks contain the answer — 4 of 5 | **MET** | 4 of 5, the same 4 in every run because retrieval is deterministic. Judged by `tools/verify_criteria.py::criterion_1`, which looks for each question’s `expects` string in the `config.TOP_K` = 5 chunks actually retrieved — but the string match is only a candidate, and reading the chunk it found for the Brightwater question overturned it: the match is on ‘students’ in a chunk that puts them gone in May and June and never says why July and August are quiet. Met at exactly the target, and only because Elder Ness — the question I named in unit 1 as the expected miss — now returns at rank 1. |
| 2 | Every answer names a source — 5 of 5 | **MISSED** | 14 of 15 answers named a file: 5/5, 4/5, 5/5. Run 2 of the Brightwater question produced two sentences of prose with no filename anywhere in them. Target was all five, every run, so one run at 4 of 5 is a miss — and it is the exact failure criteria.md predicted ("the model dropping the citation from otherwise sound prose"). The argument for calling it a MET instead is below the table. |
| 3 | Gate stops out-of-corpus questions — 4 of 5 | **MET** | 5 of 5 refused by `run_eval.py::check_out_of_scope` at the 0.72 cutoff. Not close: the nearest out-of-scope question was the ibuprofen one at 0.835, which is the one I predicted would be nearest, and it is still 0.115 clear of the cutoff. |
| 4 | Each chunk holds exactly one section — 10 of 10 | **MET** | 10 of 10 on the sample, and I checked the whole corpus rather than only the sample for the part of the criterion that covers it: 0 of 94 chunks contain a `##` marker, so no chunk holds text from more than one section, and 94 of 94 end in `.`, `!` or `?` — no sentence cut in half anywhere, not just in the ten I read. "Begins at a heading" I read as the `Town — Section` label being the first line, since Milestone 3's chunker replaces the raw `##` line with that label; on the literal `##` reading the count would be 0 of 10, and that reading would make the criterion untestable against my own chunker. |
| 5 | Margin between in-scope and out-of-scope — at least 0.10 | **MET** | All five in-scope questions passed the gate, and 0.810 − 0.386 = 0.425, over four times the margin I asked for. Both numbers come from the same run log, so this is arithmetic rather than judgement. |

**The closest call, on criterion 2.** The answer that dropped its source
was not a wrong answer — it was the model declining to answer, saying the
documents do not explain why Brightwater is quiet in July. So there is an
argument that criterion 2 is about *answers* and a refusal is not one, which
would make this 5 of 5 and a MET.

I am not taking it, for two reasons. The criterion says "every answer the
system produces", and the system produced that text and showed it to a user;
nothing in it marks it as a refusal, and `gate.REFUSAL` — the thing the system
actually returns when it declines — never ran, because this question passed the
gate at 0.314. And the whole point of the unit-1 reasoning was that attribution
here is cheap: the filename is handed to the model in the prompt and asked for
twice. Carving out a class of answers that need not cite anything, invented
after seeing which answer failed, is the lowering-the-bar move the rubric warns
about wearing a different hat.

What is genuinely interesting is that runs 1 and 3 refused in the same way and
*did* cite the file. Same question, same chunks, same prompt — so this is not a
rule the model doesn't know, it is one it applies inconsistently when the answer
turns negative. That belongs in the diagnosis, not in the verdict.

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

One criterion missed — criterion 2 — and one question failed inside a criterion
that passed: the Brightwater question, which criterion 1 counts as its one
allowed miss. Both come back to the same question, and the second one turned
out to be the more useful of the two.

### 1. Criterion 2 — generation. The citation rule has no refusal branch.

Run 2 of the Brightwater question returned *"The provided documents do not
explain why Brightwater gets quiet in July and August, nor do they state that
the rest of the region is busy during those months."* — no filename anywhere in
it.

The mechanism is in `generate.py::GROUNDING_INSTRUCTION`. Two of its rules
apply to this answer and they do not overlap:

```
- If the documents don't cover the question, say you don't have enough information. Do not guess.
- Name the document each claim came from, using the filename given in each excerpt.
```

The citation rule attaches a filename **to a claim**. An answer that says the
documents do not cover something makes no claim drawn from a document, so
there is nothing for the rule to bind to, and the refusal rule above it never
asks for a file. The prompt's closing line — *"name the file each claim came
from"* (`generate.py::build_prompt`) — repeats the same phrasing and the same
gap. So on a refusal the model is free either way, and across three runs it
went both ways: runs 1 and 3 cited `guide_brightwater.md` voluntarily, run 2
did not.

That is why this shows up as 5/5, 4/5, 5/5 rather than a clean failure. It is
not a rule the model is ignoring; it is a rule that does not cover the case.
Fourteen of fifteen answers cited a file, and the fifteenth is the only one of
the fifteen that refused.

### 2. The Brightwater question — retrieval, caused upstream in chunking.

The corpus answers this question. `guide_seasons.md` "Summer, June to August"
says *"Brightwater goes quiet to the point of dullness with the university
empty"*, and `guide_brightwater.md` "Overview" says the town roughly doubles in
term time. Neither was retrieved. They rank **12th (0.5185)** and **8th
(0.4835)** against a `TOP_K` of 5.

The mechanism is what my Milestone 3 chunker does to a section that is about
several places at once. The whole "Summer" section is one chunk, and it covers
three towns:

```
When to visit the region — Summer, June to August

June is excellent everywhere. July and August split: Halden Bay becomes very
busy and the parking problem dominates, Kestrelford fills with walkers, and
Brightwater goes quiet to the point of dullness with the university empty.

If you are going to Halden Bay in August, arrive before 10am or plan to use the
overflow lot.
```

One chunk is one vector, so that vector has to stand for Halden Bay parking,
Kestrelford walkers *and* Brightwater emptying out. The Brightwater clause is
roughly a quarter of the text, and the embedding lands between the three rather
than on any of them.

I measured the dilution rather than assuming it.
`tools/measure_dilution.py::main` embeds the same answer twice with the same
model `store.py` indexes with — once inside the section as indexed, once as the
town-specific excerpt a town-aware chunker would have produced — and asks where
each would rank:

```
# Dilution: the whole section vs the town-specific excerpt inside it
# embedding all-MiniLM-L6-v2 via ONNXMiniLM_L6_V2, cosine, lower is better

Why does Brightwater get quiet in July and August when the rest of the region is busy?
  When to visit the region — Summer, June to August  (guide_seasons.md)
    whole section, as indexed : 0.5185   rank 12 of 94
    town excerpt alone        : 0.3066   would beat 5 of the 5 retrieved
    top-k is 5, so the section was NOT retrieved

Which town in the region is easiest to get around with limited mobility?
  Getting around the region with limited mobility — Straightforward  (guide_accessibility.md)
    whole section, as indexed : 0.5491   rank 4 of 94
    town excerpt alone        : 0.3233   would beat 5 of the 5 retrieved
    top-k is 5, so the section was retrieved
```

The same sentence the model never saw scores 0.3066 on its own — ahead of the
chunk that actually took rank 1 (0.3136). So this is not the embedding model
failing to understand "quiet in summer" means "the university is empty". It
understands that sentence fine. It is the company the sentence keeps.

### The pattern: my chunking rule fits nine of my fourteen documents.

Both of my weak retrieval results are in the same five files, and it is not a
coincidence — it is a shape my corpus has and my chunker does not know about.

- **Nine town guides** (`guide_brightwater.md`, `guide_halden_bay.md`, …) are
  one place per document, and a `##` section in them is one topic about one
  place. Splitting on headings is exactly right here, and this is where my
  three clean passes come from: Kestrelford at 0.158, Halden Bay at 0.283,
  Elder Ness at 0.289, all rank 1 or 2.
- **Five regional guides** (`guide_seasons.md`, `guide_accessibility.md`,
  `guide_eating.md`, `guide_walking.md`, `guide_regional_transport.md`) are one
  *topic* per document, and a `##` section in them sweeps across many towns.

From `tools/measure_dilution.py::corpus_shape`:

```
# Where the multi-town chunks are

  94 chunks: 22 from the 5 regional guides, 72 from the 9 town guides
  naming 2+ towns   regional 19 of 22   |   town guides 20 of 72
  median characters regional 444        |   town guides 278

  the most crowded sections:
    7 towns  guide_accessibility.md       Getting around the region with limited mobility — Practical
    4 towns  guide_walking.md             Walking in the region — Easy, on good surfaces
    4 towns  guide_eating.md              Eating across the region — The pattern worth knowing
    4 towns  guide_eating.md              Eating across the region — Opening hours
```

Nineteen of the twenty-two regional chunks name two or more towns, against 20
of 72 from the town guides — and those twenty are mostly one-line cross
references ("nearest station is Pellew Sands, 40 minutes by road") rather than
sections that genuinely cover two places.

My criterion 4 reasoning in unit 1 — "the author already chunked these
documents, the starter was overriding that with an arbitrary character count" —
was right about nine documents and wrong about five. In the regional guides the
author's unit is the section, but the unit a *question* asks about is the town,
and those are not the same thing. A one-section chunk from `guide_seasons.md`
is a complete thought about the region and a quarter of a thought about
Brightwater.

That is one problem, not two. It produced the criterion 1 miss outright, and it
is also why the accessibility question passes criterion 1 on a chunk at rank 4
behind an overview section that names no town at all.

### What I ruled out, and how

- **Loading.** The answer sentence is in the corpus and arrives intact:
  `guide_seasons.md:16`. Nothing was dropped or mangled on the way in.
- **A chunk boundary splitting the answer.** This is the failure the milestone
  describes — one sentence cut across two chunks so neither is enough — and it
  is *not* what happened. The sentence sits whole inside one chunk. My problem
  is the opposite one: a chunk holding too much, not too little. Worth writing
  down, because the two failures look identical from the run log and want
  opposite fixes.
- **The embedding model.** Ruled out by the measurement above: it scores the
  same sentence at 0.3066 in isolation. A different or larger model is not what
  stands between me and this answer.
- **`TOP_K` too small.** Raising it from 5 to 12 would pull the Summer chunk in
  and fix this one question, at the cost of seven extra chunks of unrelated
  text in every prompt the system ever sends. It treats the symptom: the chunk
  would still be ranked 12th, and I would be relying on a wide enough net
  rather than on the right thing ranking highly.
- **The relevance gate.** Not involved. The question passed at 0.3136, well
  inside the 0.72 cutoff, and the model was asked. Criterion 5's margin holds
  at 0.425.

### The two are connected, and only one fix covers both

The citation drop happened on the one question where retrieval failed to
deliver the answer. Retrieval sent the model five chunks that do not answer the
question, the model correctly said so, and the refusal branch of the prompt —
the branch with no citation requirement — was reached for the only time in
fifteen answers.

So fixing the chunking would probably make criterion 2 go green, by never
reaching the refusal branch again with these five questions. That is worth
being explicit about, because it would be hiding the defect rather than fixing
it: the refusal branch is supposed to be reachable, out-of-corpus questions
will reach it by design, and it would still cite nothing when they do. The
prompt gap is a real defect that my test only exposed by accident, and it needs
its own fix.

<!-- Milestone 4: the improvement. Chunking the five regional guides by town
     within section addresses diagnosis 2 and the pattern; a citation rule that
     covers the refusal branch addresses diagnosis 1. Which one I do, and what
     it actually did to the numbers, goes below. -->

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

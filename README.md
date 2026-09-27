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

### Unit 2

Same pattern as unit 1, and the same lesson twice more. Three moments from this
unit are worth recording.

**3. The scorer that agreed with me for the wrong reason.**

`run_eval.py` does not judge answers, so I wrote `tools/verify_criteria.py` to
check criterion 1 by looking for each question's `expects` string in the
retrieved chunks. It reported 5 of 5 and I nearly wrote that down.

The Brightwater question's `expects` is the single word "students", and the
chunk it matched is `guide_brightwater.md` "When to go", which says the
students are gone in May and June and that July and August are quiet. It never
says the second thing is because of the first. The sentence that does,
"Brightwater goes quiet to the point of dullness with the university empty",
was at rank 12 and the model never saw it. The proxy said pass, the criterion
said fail, and the only way to tell was to read the chunk the script printed.

After the re-chunk the same probe was wrong in the other direction: the chunk
that does answer the question never uses the word "students" at all. So I
stopped treating a string match as a verdict. `JUDGED_BY_READING` in that file
now records both rulings with the reason, so the script reproduces the numbers
in my run log instead of quietly disagreeing with them.

**4. Three possible causes, deliberately unranked.**

For the diagnosis I pasted the failing question and the five chunks it
retrieved and asked for possible causes at different pipeline stages, with no
ranking, so the testing was mine to do. What came back was a split answer
across two chunks, an embedding model too weak for a causal question, and a
top-k that was too small.

None of those was it. The answer sentence is whole inside one chunk, so nothing
was split. The same sentence scores 0.3066 on its own against the same model,
so the model reads it fine. Raising top-k from 5 to 12 would have caught it and
put seven junk chunks in every prompt forever. What the three wrong answers were
useful for was eliminating stages: once loading, chunk boundaries, embedding and
retrieval depth were out, what was left was the vector standing for three towns
at once, and `tools/measure_dilution.py` measured it at 0.5185 inside the
section against 0.3066 alone.

**5. The obvious cut that did not work, and the one that did.**

For the improvement I planned to split multi-town sections at sentence
boundaries, because cutting sentences in half is exactly what I replaced the
starter's chunker to stop doing. I measured three candidate cuts before writing
any of it: the whole section as indexed at 0.5185, the sentence kept intact at
0.4765, the sentence cut at its commas at 0.3398. The tidy version was barely
better than doing nothing and would still have finished outside the top five.
The sentence in question is built to carry three towns at once, so nothing
above the comma is fine enough to separate them.

Then reading the output caught the cost of that. Cutting at commas turned
"Kestrelford, Halden Bay, Corry Vale, Givens Mill and Elder Ness have minor
injuries units" into chunks whose entire body was one town name, and one of
them took rank 1 on my accessibility question. The chunk count and the average
length looked fine. `chunker.py::_clauses` now holds a bare name until the
predicate its list shares arrives. That is twice now that reading ten chunks
found something no summary statistic would have.

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

Three runs with caching off, from `python run_eval.py --label before`. The raw
file is [`results/run_2026-09-27_1611_before.md`](results/run_2026-09-27_1611_before.md).
Criteria 1 and 4 are not in that file, because neither one is about the answer
the model writes. Those two come from `tools/verify_criteria.py`.

| Criterion | Target | Run 1 | Run 2 | Run 3 | Verdict |
|---|---|---|---|---|---|
| 1. Retrieved chunk contains the answer | 4 of 5 | 4/5 | 4/5 | 4/5 | MET |
| 2. Every answer names a source | 5 of 5 | 5/5 | 4/5 | 5/5 | MISSED |
| 3. Gate stops out-of-corpus questions | 4 of 5 | 5/5 | 5/5 | 5/5 | MET |
| 4. Each chunk holds exactly one section | 10 of 10 | 10/10 | 10/10 | 10/10 | MET |
| 5. Margin between in-scope and out-of-scope | at least 0.10 | 0.425 | 0.425 | 0.425 | MET |

Four rows are identical across all three columns and only criterion 2 moves.
That is the system, not a shortcut. Chunking, embedding and retrieval all run
the same way every time, and the gate is a comparison against a fixed number,
so criteria 1, 3, 4 and 5 get measured once and the number goes in all three
columns. Criterion 2 is the only one that depends on what the model writes, and
it is the only one that varied.

### Criterion 1, retrieved chunks contain the answer. 4/5, MET

Produced by `tools/verify_criteria.py::criterion_1`. It searches through
`store.py::search` at `config.TOP_K` of 5, looks for each question's `expects`
string in the retrieved chunk text, and prints the chunk so I can read the
match instead of trusting it. Three of the five questions are worth showing:

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
  expects 'students': NOT FOUND
  rank 1 rejected on reading: matches on 'students', but it puts them gone in MAY AND JUNE and says only that July and August are 'quiet to the point of being dull'. It never joins the two into a reason.
    1. 0.3136  guide_brightwater.md         Brightwater — When to go
    2. 0.3513  guide_seasons.md             When to visit the region — Autumn, September to November
    3. 0.3974  guide_regional_transport.md  Getting around the region — The railway
    4. 0.4218  guide_seasons.md             When to visit the region — Winter, December to February
    5. 0.4370  guide_brightwater.md         Brightwater — Getting there

-> 4 of 5 questions had the answer in the retrieved chunks
```

Elder Ness is the question I built criterion 1 around. In unit 1 I said it was
the one I expected to miss, and after the heading split it comes back at rank
1. The question that misses instead is Brightwater, and it took reading to see
that.

My first pass at this said 5 of 5. The `expects` string for the Brightwater
question is the single word `students`, and a retrieved chunk does contain it.
Reading that chunk says otherwise: it puts the students leaving in May and
June, calls July and August dull, and never joins the two into a reason. The
sentence that actually answers the question is "Brightwater goes quiet to the
point of dullness with the university empty" in `guide_seasons.md` "Summer",
and it sits at rank 12. `Brightwater — Overview`, which says the town roughly
doubles in term time, sits at rank 8. Neither is inside top-k, so neither
reached the model, which is why all three runs answered that the documents do
not explain it.

`expects` is a proxy for "contains the answer" that I wrote in Milestone 2
before I had seen a single result, and on this question the proxy and the
criterion disagree. The criterion wins. That judgement now lives in
`JUDGED_BY_READING` in `tools/verify_criteria.py` with the reason, so re-running
the script reproduces 4 of 5 instead of drifting back to 5.

The accessibility question passes, but it is the other weak one: the chunk
naming Thornby Wells is at rank 4, behind an overview section that names no
town at all.

### Criterion 2, every answer names a source. 5/5, 4/5, 5/5, MISSED

Produced by `generate.py::answer_from_chunks` and logged by `run_eval.py::main`.
Fourteen of fifteen answers named a file. The one that did not is run 2 of the
Brightwater question:

```
### Why does Brightwater get quiet in July and August when the rest of the region is busy? — run 2

- Best distance: 0.3136 (passed the gate)
- Sources retrieved: guide_brightwater.md, guide_regional_transport.md, guide_seasons.md

The provided documents do not explain why Brightwater gets quiet in July and August, nor do they state that the rest of the region is busy during those months.
```

Runs 1 and 3 of the same question refuse the same way and do cite the file:

```
### Why does Brightwater get quiet in July and August when the rest of the region is busy? — run 3

The provided documents do not mention why the rest of the region is busy, nor do they state that the rest of the region is busy during July and August; they only state that July and August in Brightwater are "quiet to the point of being dull" (*guide_brightwater.md*).
```

Against a target of 5 of 5 that is a miss. One run at 4 of 5 is exactly what
criteria.md said a target of 4 of 5 would excuse in advance. A passing answer
from the same run, for contrast:

```
### What hours do the pubs in Kestrelford serve food? — run 2

The pubs in Kestrelford serve food between 12 and 2 and again between 6 and 8:30 (guide_kestrelford.md and guide_eating.md).
```

### Criterion 3, the gate stops out-of-corpus questions. 5/5, MET

Produced by `run_eval.py::check_out_of_scope` at the 0.72 cutoff, in one pass:

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
grounds that it shares vocabulary with the minor injuries paragraphs. It came
back at 0.835, closer than the World Cup question at 0.963, so the reasoning
held. It is still nowhere near the 0.72 cutoff.

### Criterion 4, each chunk holds exactly one section. 10/10, MET

Produced by `tools/verify_criteria.py::criterion_4` over the chunks from
`chunker.py::split_documents`, using the same 10-chunk sample `app.py chunks`
prints. This is the output from before the chunker change, so re-running it now
gives the 138-chunk sample in the after section rather than this one:

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

### Criterion 5, a clear margin between the two groups. 0.425, MET

Both halves are printed into the same file by `run_eval.py`, the in-scope
distances by `run_eval.py::run_once` and the out-of-scope ones by
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

All five in-scope questions passed the gate, and the margin is 0.810 minus
0.386, which is 0.425 against a target of at least 0.10. The 0.72 cutoff sits
in that gap with 0.334 of room below it and 0.090 above. The gap is wider than
the 0.639 to 0.810 pair I set the cutoff from in Milestone 4, because the
loosely phrased questions that produced 0.639 are not among these five.

## Verdicts

<!-- MET or MISSED for each of the five, against the target you wrote last
     unit — not a new one. Plus a sentence on how you decided. That sentence
     matters most where it was close.

     If your target said 4 of 5 and your runs came out 4, 3, 4, that's a MISS.
     The target has to hold, not show up occasionally.

     Milestone 2. -->

Four met, one missed, against the targets as written in unit 1. No criterion is
revised. All five measured what I meant them to measure, and the one I missed I
missed on the result rather than on the measurement.

| # | Criterion | Verdict | How I decided |
|---|---|---|---|
| 1 | Retrieved chunks contain the answer, 4 of 5 | **MET** | 4 of 5, the same 4 every run, because retrieval does not vary. Judged by `tools/verify_criteria.py::criterion_1`, which looks for each question's `expects` string in the 5 chunks actually retrieved. The string match is a candidate and not a verdict: reading the chunk it found for the Brightwater question overturned it, since the match is on "students" in a chunk that puts them gone in May and June and never says why July and August are quiet. Met at exactly the target, and only because Elder Ness, the question I named in unit 1 as the expected miss, now comes back at rank 1. |
| 2 | Every answer names a source, 5 of 5 | **MISSED** | 14 of 15 answers named a file, so 5/5, 4/5, 5/5. Run 2 of the Brightwater question is two sentences of prose with no filename in them. The target was all five in every run, so one run at 4 of 5 is a miss, and it is the failure criteria.md predicted: the model dropping the citation from otherwise sound prose. The argument for calling it a met is below the table. |
| 3 | Gate stops out-of-corpus questions, 4 of 5 | **MET** | 5 of 5 refused by `run_eval.py::check_out_of_scope` at the 0.72 cutoff. Not close. The nearest out-of-scope question is the ibuprofen one at 0.835, the one I predicted would be nearest, and it is still 0.115 clear of the cutoff. |
| 4 | Each chunk holds exactly one section, 10 of 10 | **MET** | 10 of 10 on the sample. For the half of the criterion that covers every chunk rather than the sample I checked all of them: 0 of 94 chunks contain a `##` marker, so no chunk holds text from two sections, and 94 of 94 end in a full stop, question mark or exclamation mark, so no sentence is cut in half anywhere. I read "begins at a heading" as the `Town — Section` label being the first line, since the Milestone 3 chunker replaces the raw `##` line with that label. On the literal reading the count would be 0 of 10, and that reading makes the criterion impossible to test against my own chunker. |
| 5 | Margin of at least 0.10 | **MET** | All five in-scope questions passed the gate, and 0.810 minus 0.386 is 0.425, over four times the margin I asked for. Both numbers come out of the same run log, so this is arithmetic rather than judgement. |

**The closest call, on criterion 2.** The answer that dropped its source was
not a wrong answer. It was the model declining to answer, saying the documents
do not explain why Brightwater is quiet in July. So there is an argument that
criterion 2 is about answers and a refusal is not one, which would make this 5
of 5 and a met.

I am not taking it. The criterion says "every answer the system produces", and
the system produced that text and showed it to a user. Nothing in it marks it
as a refusal, and `gate.REFUSAL`, the thing the system returns when it actually
declines, never ran, because the question passed the gate at 0.314. The unit 1
reasoning was that attribution here is cheap, since the filename is handed to
the model in the prompt and asked for twice. Carving out a class of answers
that need not cite anything, invented after seeing which answer failed, is
lowering the bar in a different hat.

What is worth noticing is that runs 1 and 3 refused in the same way and did
cite the file. Same question, same chunks, same prompt. So this is not a rule
the model does not know, it is one it applies inconsistently when the answer
turns negative. That belongs in the diagnosis.

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

One criterion missed, criterion 2, and one question failed inside a criterion
that passed, which is the Brightwater question that criterion 1 counts as its
one allowed miss. Both come back to the same question. The second turned out to
be the more useful of the two.

### 1. Criterion 2. Generation. The citation rule has no refusal branch.

Run 2 of the Brightwater question returned "The provided documents do not
explain why Brightwater gets quiet in July and August, nor do they state that
the rest of the region is busy during those months." There is no filename in
it.

The mechanism is in `generate.py::GROUNDING_INSTRUCTION`. Two of its rules
apply to this answer and they do not overlap:

```
- If the documents don't cover the question, say you don't have enough information. Do not guess.
- Name the document each claim came from, using the filename given in each excerpt.
```

The citation rule attaches a filename to a claim. An answer saying the
documents do not cover something makes no claim drawn from a document, so there
is nothing for the rule to bind to, and the refusal rule above it never asks
for a file. The closing line of the prompt, "name the file each claim came
from" in `generate.py::build_prompt`, repeats the same phrasing and the same
gap. On a refusal the model is free either way, and across three runs it went
both ways.

That is why this shows up as 5/5, 4/5, 5/5 rather than a clean failure. It is
not a rule the model ignores, it is a rule that does not cover the case.
Fourteen of fifteen answers cited a file, and the fifteenth is the only one of
the fifteen that refused.

### 2. The Brightwater question. Retrieval, caused upstream in chunking.

The corpus answers this question. `guide_seasons.md` "Summer, June to August"
says "Brightwater goes quiet to the point of dullness with the university
empty", and `guide_brightwater.md` "Overview" says the town roughly doubles in
term time. Neither was retrieved. They rank 12th at 0.5185 and 8th at 0.4835
against a `TOP_K` of 5.

The mechanism is what my Milestone 3 chunker does to a section that covers
several places at once. The whole "Summer" section is one chunk and it holds
three towns:

```
When to visit the region — Summer, June to August

June is excellent everywhere. July and August split: Halden Bay becomes very
busy and the parking problem dominates, Kestrelford fills with walkers, and
Brightwater goes quiet to the point of dullness with the university empty.

If you are going to Halden Bay in August, arrive before 10am or plan to use the
overflow lot.
```

One chunk is one vector, so that vector stands for Halden Bay parking,
Kestrelford walkers and Brightwater emptying out all at once. The Brightwater
clause is about a quarter of the text, and the embedding lands between the
three rather than on any of them.

I measured that rather than assuming it. `tools/measure_dilution.py::main`
embeds the same answer twice with the model `store.py` indexes with, once
inside the section as indexed and once as the town excerpt a town aware chunker
would produce, and asks where each would rank:

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

The sentence the model never saw scores 0.3066 on its own, ahead of the chunk
that took rank 1 at 0.3136. So this is not the embedding model failing to see
that "quiet in summer" means "the university is empty". It reads that sentence
fine. It is the company the sentence keeps.

### The pattern. My chunking rule fits nine of my fourteen documents.

Both weak retrieval results are in the same five files, and that is a shape my
corpus has that my chunker does not know about.

- Nine town guides (`guide_brightwater.md`, `guide_halden_bay.md` and the rest)
  are one place per document, and a `##` section in them is one topic about one
  place. Splitting on headings is right there, and it is where the three clean
  passes come from: Kestrelford at 0.158, Halden Bay at 0.283, Elder Ness at
  0.289, all at rank 1 or 2.
- Five regional guides (`guide_seasons.md`, `guide_accessibility.md`,
  `guide_eating.md`, `guide_walking.md`, `guide_regional_transport.md`) are one
  topic per document, and a `##` section in them sweeps across many towns.

From `tools/measure_dilution.py::corpus_shape`, run before the change:

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
of 72 from the town guides, and most of those twenty are one-line cross
references like "nearest station is Pellew Sands, 40 minutes by road" rather
than sections that really cover two places.

My criterion 4 reasoning in unit 1 was that the author had already chunked
these documents and the starter was overriding that with an arbitrary character
count. That was right about nine documents and wrong about five. In the
regional guides the author's unit is the section, but the unit a question asks
about is the town, and those are not the same thing. A one-section chunk from
`guide_seasons.md` is a complete thought about the region and a quarter of a
thought about Brightwater.

That is one problem and not two. It produced the criterion 1 miss outright, and
it is also why the accessibility question passes on a chunk at rank 4, behind
an overview section that names no town.

### What I ruled out, and how

- Loading. The answer sentence is in the corpus and arrives intact, at
  `guide_seasons.md:16`. Nothing was dropped or mangled on the way in.
- A chunk boundary splitting the answer. This is the failure the milestone
  describes, one sentence cut across two chunks so that neither is enough, and
  it is not what happened. The sentence sits whole inside one chunk. My problem
  is the opposite one, a chunk holding too much rather than too little. Worth
  writing down, because the two look identical in a run log and want opposite
  fixes.
- The embedding model. Ruled out by the measurement above. It scores the same
  sentence at 0.3066 in isolation.
- `TOP_K` too small. Raising it from 5 to 12 would pull the Summer chunk in and
  fix this one question, at the price of seven extra chunks of unrelated text
  in every prompt the system sends. It treats the symptom. The chunk would
  still rank 12th and I would be relying on a wide enough net rather than on
  the right thing ranking highly.
- The relevance gate. Not involved. The question passed at 0.3136, well inside
  the 0.72 cutoff, and the model was asked. Criterion 5 holds at 0.425.

### The two are connected, and one fix covers both

The citation drop happened on the one question where retrieval failed to
deliver the answer. Retrieval sent the model five chunks that do not answer the
question, the model correctly said so, and the refusal branch of the prompt,
the branch with no citation requirement, was reached for the only time in
fifteen answers.

So fixing the chunking would probably make criterion 2 go green by never
reaching that branch again with these five questions. That is worth saying out
loud, because it would be hiding the defect rather than fixing it. The refusal
branch is supposed to be reachable, out-of-corpus questions will reach it by
design, and it would still cite nothing when they do. The prompt gap is a real
defect that my test only exposed by accident, and it needs its own fix.

## The Improvement

**What I changed:** `chunker.py::split_documents` now splits a section of a
topic guide into the places that section names, one chunk per place, labelled
`Topic — Section — Place`. Sections of place guides are untouched, and so are
topic sections that name one place or none. The corpus goes from 94 chunks to
138, of which 63 are place chunks and 75 are section chunks.

Three things had to be decided, and all three were decided by measurement
rather than taste.

Which guides are topic guides is worked out from the corpus by
`chunker.py::_place_names`, not from a list of town names in the code. A place
guide's title gets talked about by other documents, so "Halden Bay" appears in
the text of `guide_seasons.md`, while no document in the corpus says "When to
visit the region" in a sentence. A title that appears in another document's
text is a place, and one that does not is a topic. Nine titles come out as places and five as
topics, which is the split the diagnosis found.

That rule took two goes. The first version counted a title appearing anywhere
in another document, and `guide_regional_transport.md` is titled "Getting
around the region", which is a prefix of `guide_accessibility.md`'s title,
"Getting around the region with limited mobility". So the transport guide
classified itself as a place and was the one topic guide that never got split.
Title lines do not count now, only body text, and three of its four sections
split like the rest. The fourth, "The railway", names only Brightwater and so
stays whole, which is the rule working rather than an exception to it.

Where to cut was the part I got wrong first. The obvious cut is the sentence,
which keeps the grammar intact. It does not work here, because the sentence
that holds my answer is built to hold three towns at once. Filing that whole
sentence under all three towns scores 0.4765 against the Brightwater question,
better than the 0.5185 it scores inside the full section and still outside the
top five. Cutting the sentence at its commas scores 0.3398, and adding the town
to the label brings it to 0.3134. So the cut has to be the comma, and I accept
a cut sentence to get it. Each piece carries the lead-in of the sentence it
came from, so the Brightwater clause arrives as "July and August split:
Brightwater goes quiet to the point of dullness with the university empty"
rather than as a fragment with no months in it.

What to do with sentences that name no place is the part where this could
quietly produce wrong chunks. A sentence before any place has been named is
framing, so "June is excellent everywhere" goes into every place chunk in that
section. A sentence after that, at the head of a later paragraph, belongs to
nothing in particular: `guide_seasons.md` "Winter" opens its second paragraph
with "The coastal path is dramatic and frequently shut", which is about the
coast and not about Brightwater. Copying that into every town's chunk would put
a coast fact under a Brightwater label, which is the cross-town error my
grounding rules exist to stop, so it becomes a chunk of its own with the plain
section label. Inside a paragraph, a sentence with no place belongs to the last
place named in that paragraph, and attribution resets at every paragraph break.

Reading the output caught one more thing. `guide_accessibility.md` "Practical"
contains "Brightwater has a hospital; Kestrelford, Halden Bay, Corry Vale,
Givens Mill and Elder Ness have minor injuries units with limited hours or
nothing at all." Cutting that at the commas gave Kestrelford, Halden Bay and
Corry Vale a chunk whose entire body was their own name, and one of those
name-only chunks took rank 1 on my accessibility question. `chunker.py::_clauses`
now holds a bare name back until the predicate its list shares arrives, so all
five towns get the full sentence. That is the second time in this project that
reading the chunks found something the summary statistics could not.

**Why I picked it:** the diagnosis says the answer to my one failing question
was ranked 12th because it was embedded inside a vector standing for three
towns, and that 19 of the 22 chunks from those five guides have the same shape.
This cuts those chunks down to one place each, which is the thing that was
measured to be wrong.

I deliberately did not touch `generate.py`. The citation gap is the other
diagnosis and fixing both at once would leave me unable to say which change did
what.

### Run Log — After

<!-- Same format, same five criteria, three runs each.
     `python run_eval.py --label after` -->

Three runs with caching off, from
`python run_eval.py --label after --variant by_place`. The raw file is
[`results/run_2026-09-27_1805_after.md`](results/run_2026-09-27_1805_after.md).
The old index is still there as variant `default`, so before and after are two
collections rather than one overwritten one.

| Criterion | Target | Run 1 | Run 2 | Run 3 | Verdict |
|---|---|---|---|---|---|
| 1. Retrieved chunk contains the answer | 4 of 5 | 5/5 | 5/5 | 5/5 | MET |
| 2. Every answer names a source | 5 of 5 | 5/5 | 5/5 | 5/5 | MET |
| 3. Gate stops out-of-corpus questions | 4 of 5 | 5/5 | 5/5 | 5/5 | MET |
| 4. Each chunk holds exactly one section | 10 of 10 | 10/10 | 10/10 | 10/10 | MET |
| 5. Margin between in-scope and out-of-scope | at least 0.10 | 0.439 | 0.439 | 0.439 | MET |

Side by side:

| Criterion | Before | After |
|---|---|---|
| 1. Retrieved chunk contains the answer | 4/5 | 5/5 |
| 2. Every answer names a source | 5/5, 4/5, 5/5 | 5/5, 5/5, 5/5 |
| 3. Gate stops out-of-corpus questions | 5/5 | 5/5 |
| 4. Each chunk holds exactly one section | 10/10 | 10/10 |
| 5. Margin | 0.425 | 0.439 |

**Criterion 1, from `tools/verify_criteria.py::criterion_1` against the new
index.** Every question now finds its answer at rank 1 or rank 2, and the two
questions the diagnosis was about moved the most. The Brightwater sentence went
from rank 12 to rank 1:

```
Why does Brightwater get quiet in July and August when the rest of the region is busy?
  expects 'students': FOUND at rank 1
  rank 1 accepted on reading: 'Brightwater goes quiet to the point of dullness with the university empty' is the answer, and the word 'students' is nowhere in it. Before the re-chunk this sentence sat inside the whole Summer section at rank 12.
  rank 2 rejected on reading: matches on 'students', but it puts them gone in MAY AND JUNE and says only that July and August are 'quiet to the point of being dull'. It never joins the two into a reason.
  * 1. 0.3134  guide_seasons.md             When to visit the region — Summer, June to August — Brightwater
    2. 0.3136  guide_brightwater.md         Brightwater — When to go
    3. 0.3513  guide_seasons.md             When to visit the region — Autumn, September to November
    4. 0.3830  guide_seasons.md             When to visit the region — Spring, March to May — Brightwater
    5. 0.3883  guide_regional_transport.md  Getting around the region — Buses — Brightwater

  the chunk that contains it:
  When to visit the region — Summer, June to August — Brightwater

  June is excellent everywhere. July and August split: Brightwater goes quiet to the point of dullness with the university empty.

Which town in the region is easiest to get around with limited mobility?
  expects 'Thornby Wells': FOUND at rank 1
  * 1. 0.3713  guide_accessibility.md       Getting around the region with limited mobility — Straightforward — Thornby Wells
    2. 0.3806  guide_walking.md             Walking in the region — Easy, on good surfaces — Thornby Wells
    3. 0.3855  guide_accessibility.md       Getting around the region with limited mobility — Overview
    4. 0.4965  guide_accessibility.md       Getting around the region with limited mobility — Difficult — Corry Vale
    5. 0.4996  guide_accessibility.md       Getting around the region with limited mobility — Difficult — Kestrelford

-> 5 of 5 questions had the answer in the retrieved chunks
```

The "students" judgement is still recorded and still rejects the chunk it
rejected before. The question passes on a different chunk, which is the one
that actually answers it.

**Criterion 2.** Fifteen of fifteen answers named a file. The Brightwater
question, which is where the miss was, now answers it and cites it in all three
runs:

```
### Why does Brightwater get quiet in July and August when the rest of the region is busy? — run 1

The documents do not state that the rest of the region is busy in July and August; they only state that Brightwater goes quiet to the point of dullness during these months because the university is empty (`guide_seasons.md`). Additionally, `guide_brightwater.md` mentions that July and August are quiet to the point of being dull in Brightwater, but it does not provide information about the rest of the region during those months.

### Why does Brightwater get quiet in July and August when the rest of the region is busy? — run 2

The provided documents do not state that the rest of the region is busy in July and August. They only state that Brightwater goes quiet to the point of dullness in July and August because the university is empty (`guide_seasons.md` and `guide_brightwater.md`).
```

Before the change, all three runs of this question said the documents do not
explain it. They now give the reason, which is the university emptying out.

**Criterion 3.** Identical to the before run, and identical for a reason worth
recording rather than as a coincidence. The nearest chunk to each out-of-scope
question comes from a town guide, and town guides are the half of the corpus
this change does not touch:

```
default   0.8104  guide_corry_vale.md        Corry Vale — Overview
by_place  0.8104  guide_corry_vale.md        Corry Vale — Overview

default   0.8351  guide_givens_mill.md       Givens Mill — Eat and drink
by_place  0.8351  guide_givens_mill.md       Givens Mill — Eat and drink
```

**Criterion 4.** 10 of 10 on the sample, and across all 138 chunks none
contains a `##` marker and none ends anywhere but a full stop, question mark or
exclamation mark. The sample now includes three place chunks, which is what I
wanted to see:

```
# 138 chunks total, sampling 10 spread across the corpus

 1. guide_accessibility.md#0        one section: yes  starts at heading: yes  ends at sentence: yes  | Getting around the region with limited mobility — Overview
 2. guide_accessibility.md#13       one section: yes  starts at heading: yes  ends at sentence: yes  | Getting around the region with limited mobility — Practical — Halden Bay
 3. guide_corry_vale.md#1           one section: yes  starts at heading: yes  ends at sentence: yes  | Corry Vale — Getting there
 4. guide_eating.md#6               one section: yes  starts at heading: yes  ends at sentence: yes  | Eating across the region — Opening hours — Elder Ness
 5. guide_elder_ness.md#2           one section: yes  starts at heading: yes  ends at sentence: yes  | Elder Ness — Getting around
 6. guide_givens_mill.md#7          one section: yes  starts at heading: yes  ends at sentence: yes  | Givens Mill — Practical notes
 7. guide_kestrelford.md#4          one section: yes  starts at heading: yes  ends at sentence: yes  | Kestrelford — What to see
 8. guide_pellew_sands.md#1         one section: yes  starts at heading: yes  ends at sentence: yes  | Pellew Sands — Getting there
 9. guide_regional_transport.md#6   one section: yes  starts at heading: yes  ends at sentence: yes  | Getting around the region — Driving
10. guide_seasons.md#8              one section: yes  starts at heading: yes  ends at sentence: yes  | When to visit the region — Winter, December to February — Kestrelford

-> 10 of 10 sampled chunks pass all three checks
```

I am recording this as met and flagging the part a strict reader could argue
with. Every chunk still holds one section and still ends at a sentence end. But
a place chunk built from a multi-town sentence is assembled from clauses, and
"no sentence cut in half at either end" was written before any chunk of mine
was built that way. The chunk reads as a complete statement and ends in a full
stop I added when the clause did not carry one. Whether that counts as a
sentence cut in half is a judgement, and I would rather put it here than have
it found.

**The shape the diagnosis measured.** `tools/measure_dilution.py::corpus_shape`
on the new chunks, next to the same numbers before:

```
  138 chunks: 66 from the 5 regional guides, 72 from the 9 town guides
  naming 2+ towns   regional 13 of 66   |   town guides 20 of 72
  median characters regional 205        |   town guides 278
```

Before the change it was 19 of 22 regional chunks naming two or more towns at a
median of 444 characters. Thirteen still do, and they are two different things.
Five are the minor injuries list in `guide_accessibility.md` "Practical", which
names five towns in one sentence and is copied into each of their chunks on
purpose, because it is one fact about all five. The other eight are sentences
that mention a second town in passing, like "Sunday evening is the hardest meal
to find anywhere except Marchwood and Thornby Wells". Both kinds are labelled
for one town, which is what retrieval matches on.

**Criterion 5.** In-scope 0.146 to 0.371, out-of-scope 0.810 to 0.963, so the
margin is 0.439 against 0.425 before. Four of the five in-scope questions got
closer to their best chunk, which is the expected effect of a smaller chunk
matching more tightly, and the out-of-scope group did not move at all because
its nearest neighbours are all in the untouched half of the corpus.

**Did it help?** Yes, and it moved the two criteria the diagnosis pointed at.

Criterion 1 went from 4 of 5 to 5 of 5, and the question that was failing is
now answered rather than refused. The Brightwater sentence went from rank 12,
where the model never saw it, to rank 1. The accessibility question went from
rank 4 behind a content-free overview to rank 1. Criterion 5 widened slightly.
Criteria 3 and 4 held.

Criterion 2 went from missed to met, and I do not think that is a fix. It is
the outcome I predicted in the diagnosis: the citation rule still has no
refusal branch, and the only thing that changed is that none of my five
questions now lands in it. The proof is in the next section.

The one cost I can measure is in that same Brightwater answer. Every run still
opens by rejecting the premise, saying the documents do not state that the rest
of the region is busy. Before the change, the sentence that says so was never
retrieved. After it, the sentence is split across three chunks, one per town,
and the Brightwater chunk keeps only the Brightwater clause. So the comparison
that made the question a comparison is gone from the chunk that answers it. The
model is right on both counts and I made the second one slightly worse.

## What's Still Broken

<!-- For each criterion still missed after your fix: what you'd do about it,
     and why you stopped where you did.

     "I ran out of time" is fine if it's true. Pretending nothing is left is
     not.

     Milestone 5. -->

All five criteria are met after the change, so on the table above there is
nothing left. That is not the same as nothing being broken, and two of these
are things I can show rather than suspect.

**1. The citation rule still has no refusal branch. Criterion 2 passes anyway.**

This is the defect from diagnosis 1, and re-chunking did not touch it. All it
did was stop my five questions from landing in that branch. To show the defect
is still there I needed a question that reaches the model and cannot be
answered, so `tools/refusal_check.py` asks what the overflow lot at Halden Bay
costs. The guides say the overflow lot is a 12-minute walk up a hill and never
say what it costs. It passes the gate at 0.3588, so the model is asked. Six
runs on the new index, caching off, from
`python tools/refusal_check.py --runs 6`:

```
How much does it cost to park in the overflow lot at Halden Bay?

run 1 (best distance 0.3588, sources named: none)
  The provided documents do not contain information about the cost of parking in the overflow lot at Halden Bay.

run 2 (best distance 0.3588, sources named: none)
  The provided documents do not contain information about the cost of parking in the overflow lot at Halden Bay.

run 3 (best distance 0.3588, sources named: none)
  The provided documents do not contain information about the cost to park in the overflow lot at Halden Bay.

run 4 (best distance 0.3588, sources named: guide_halden_bay.md, guide_seasons.md)
  The documents do not mention how much it costs to park in the overflow lot at Halden Bay (*guide_halden_bay.md* and *guide_seasons.md*).

run 5 (best distance 0.3588, sources named: guide_halden_bay.md, guide_seasons.md)
  The provided documents do not mention the cost to park in the overflow lot at Halden Bay (*guide_halden_bay.md* and *guide_seasons.md*).

run 6 (best distance 0.3588, sources named: none)
  The provided documents do not contain information about the cost to park in the overflow lot at Halden Bay.
```

Four of the six name no file, and run 5 says almost word for word what run 3
says with two filenames attached to it. One question, one set of chunks, six
runs, two answers. That is a coin flip, which is what a rule that does not
cover a case gives you.

What I would do: add a rule to `GROUNDING_INSTRUCTION` that covers the branch,
along the lines of "when you say the documents do not cover something, name the
files you looked in". Then re-run this check and put the six runs next to each
other.

Why I stopped: the unit asks for one change so that the before and after
measure one thing. Criterion 2 went from missed to met in this run and that
number would look the same whether I had fixed the prompt or not, which is the
argument for fixing it next rather than now.

**2. The re-chunk removes comparisons, and one of my questions is a comparison.**

Splitting a section by town means no chunk holds two towns any more. That is
the point for a question about one town, and it is a loss for a question that
compares them. My Brightwater question asks why the town is quiet when the rest
of the region is busy, and the sentence that supports the second half, "Halden
Bay becomes very busy and the parking problem dominates", now lives in the
Halden Bay chunk. All three after-runs open by saying the documents do not
state that the rest of the region is busy. They are correct about the chunks
they were given, and before the change they were not given the answer at all,
so this is a smaller problem than the one I fixed. It is still a new one.

What I would do: keep the whole-section chunk in the index alongside the place
chunks, so a comparative question can still match the section and a single-town
question can still match its town. I did not do it here because near-duplicate
chunks competing for the same five top-k slots is the exact thing I removed
overlap to avoid in Milestone 3, and testing whether it helps or crowds needs
its own before and after.

**3. Criterion 4 is now harder to judge than it was when I wrote it.**

Covered above under the after-run. A place chunk built from a multi-town
sentence is assembled from clauses with a full stop added, and the criterion
says no sentence is cut in half. It passes as measured and I would not claim
the measurement settles it.

What I would do: rewrite the criterion so it says what I actually want, which
is that a chunk reads as a complete statement on its own. That is a Milestone 3
style judgement made by reading ten chunks, not a regex.

**4. Two things I know about and did not measure this unit.**

The relevance cutoff at 0.72 was measured on the old index, and every in-scope
distance moved when the chunks got smaller. It still separates the two groups
here with 0.439 of margin, so it is not urgent, but the number is no longer the
one I measured.

And the near-miss case from Milestone 4 is untouched. Travel questions this
corpus cannot answer score 0.311 to 0.576, which overlaps the legitimate range,
and no cutoff separates them. That is what item 1 above is really for.

## What I'd Do Differently

<!-- Knowing what you know now — which of your five criteria would you write
     differently, and why?

     Milestone 5. -->

**Criterion 1 is the one I would rewrite.** "The retrieved chunks include one
that contains the answer" sounds checkable and is not, quite. I tested it with
an `expects` string I wrote in Milestone 2, and it was wrong in both directions
on the same question in the same unit. Before the change it said the Brightwater
question passed, because a chunk contained the word "students" while saying the
students leave in May and June. After the change it would have said the question
failed, because the chunk that does answer it never uses the word "students" at
all. One word chosen before I had seen a result is not a test of whether an
answer is present.

What I would write instead: for at least 4 of my 5 questions, the top three
results contain a chunk that on its own supports the answer, judged by reading
the chunk and recording the reason. Top three rather than top five because
rank matters and criterion 1 as written cannot see the difference between rank
1 and rank 4. Judged by reading rather than by a string, because that is what I
ended up doing anyway. The judgement belongs in the repository, not in my head,
which is why `JUDGED_BY_READING` exists in `tools/verify_criteria.py`.

**Criterion 2 needs to say what an answer is.** It says every answer names a
source. It did not occur to me that the system would produce answers that make
no claims, and that is exactly where it failed. I would write it as: every
answer names at least one source file, including answers that decline to
answer, which name the files that were searched. That version would have failed
in the before run and would still fail now, which is the point. The version I
wrote passes now for a reason that has nothing to do with the defect.

**Criterion 4 asked for the wrong kind of precision.** Ten of ten on heading
starts and sentence ends is easy to check and did not catch the only real
chunking problem I had, which was chunks that hold one section and three towns.
The criterion that would have caught it is about what a chunk is about, not
where it begins and ends: no chunk should be about more than one place. I would
write that instead, and I would have found the dilution in Milestone 3 rather
than in unit 2.

Criteria 3 and 5 I would keep as they are. Both are arithmetic on numbers the
system already prints, both were reproducible across two different indexes, and
criterion 5 is the only one that stopped me from setting the cutoff wherever I
liked.


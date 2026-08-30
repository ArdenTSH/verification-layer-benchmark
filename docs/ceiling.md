# The ceiling: what the method can be scored against

*The target list, and nothing else. **The authority is
`build_targets()` in `bench/score_targets.py`**: it constructs the list from
the label tables and it is what the scorer runs. `data/labels/ceiling.json` is
a generated report of that list, written by `tools/build_ceiling.py`, which
imports the function — the dependency runs code to key, never back. Nothing
reads the key. Where this document, that file and the code disagree, run
`build_targets`.*

*Earlier ceiling documents and a tiered key of the same name were superseded by
this one. They stayed in the research repository and are not part of this
benchmark, so a filename cited below as superseded names history rather than
anything you can open here.*

---

*"The layer" below is the verification system this benchmark evaluates — Aletheia v0, in
a separate repository — and "an arm" is one model configuration run through it. Neither
is privileged here; the README's term table has the rest.*

## 1. What the method is

> A model receives a claim and its deposited evidence, is told nothing about
> any expert finding, and writes one check. The layer executes it. **The
> measurement is whether that process independently reaches a finding the
> critique, the Correction or the external baseline already published.**

Two conditions make something a target, and both are necessary:

1. **An expert source published it.** The layer is a reproduction instrument
   and has no standing to decide chemistry. Every target is a documentary fact
   about what a published source says. A finding the layer produces that no
   expert asserted is a **false alarm of the instrument**, never a discovery.
2. **A model-written check could reach it** from the claim and the deposited
   evidence, using the current vocabulary.

**K1 to K5 is the complete list of what stage-one evidence can reach**, and a
model that did everything right recovers all of it. **K6 is the sixth group and
it is not more of the same.** It is not a reproduction of another automated
system; it is the end-to-end test of the two-stage protocol — abstain, name the
analysis that would settle the question, be granted it, and reach the external
baseline's decision. CARTOGRAPH's pass/flag is the external key for that last
step, not a rival score to beat. It is scoreable only at stage two, counted
apart from the 55, and never pooled with them.

---

## 2. The list

Group denominators are never pooled. No single number is computed across them.

**Each entry says what a check must COMPUTE, not which function to call.** An
earlier draft named our layer's own primitives — `ctx.space_group_number` and
the rest — which was wrong twice over: no such object ships here, and requiring
it would defeat the point. You bring your own verifier. What the benchmark fixes
is the quantity and the tolerance; how you obtain it is yours. The key names for
reporting the results are in `docs/ENTRANT.md` §3.

### K1 — the deposited file differs from the claimed structure

| | |
|---|---|
| whose finding | the critique, Table I, E2 |
| count | **7** — the critique prints 8; `Mg3NiO4` is offline, not adjudicated, and outside the evaluation population, so no verifier can ever score it |
| source file | `data/labels/merged_labels.csv`, `prx_table1_errors.csv` |
| what a check must do | read the file, read the claim, establish a contradiction |
| shape | flag |

Reachable by three distinct routes, and the split matters:

| route | catches | which |
|---|---|---|
| occupancy — a site carries two cation species where the claim says one | **6 of 8** | Ba2ZrSnO6, KNaP6(PbO3)8, KPr9(Si3O13)2, Mg3NiO4, MgCuP2O7, NaCaMgFe(SiO3)4 |
| symmetry — deposited group differs from claimed group | **4 of 8** | Ba2ZrSnO6, KNaP6(PbO3)8, KMn3O6, Mg3NiO4 |
| **symmetry adds beyond occupancy** | **1** | KMn3O6 |
| reference lookup | **1** | MgV4Cu3O14 |

`MgV4Cu3O14` is claimed P1, indexed P1, computes P1, and has zero
mixed-occupancy sites — the file agrees with its claim on both counts. Its flag
rests on a comparison to ICSD 69731, (Cu1.5Mg0.5)V2O7. **No file-internal check
can ever reach it.** It became reachable on 27 August through
`reference_structures`, not through symmetry.

**7 of 7 reachable, and `opus5` reached all 7 in generation 2** (6 validated;
`MgV4Cu3O14` reached but unvalidatable, see §4). `MgV4Cu3O14`'s flag is
justified by a database comparison, not by the file, so K1 accepts `novelty`
evidence for that target alone — a per-target override, recorded in
`EVIDENCE_OVERRIDES`.

### K2 — the symmetry of each deposited file

| | |
|---|---|
| whose finding | the critique, Table III, `indexed_sym` |
| count | **38** — 43 determinations are printed; five rows leave the denominator by the exclusion rule: two offline compounds, the removed one, and the two where our recomputation disagrees with the critique's (`MgTi4(PO4)6`, `FeSb3Pb4O13`) |
| source file | `data/labels/prx_table3.csv` |
| what a check must do | compute the space group at a declared tolerance and record it |
| what to compute | the space group of the deposited **structure**, from its coordinates at a declared tolerance — not the file's header tag |
| tolerance | exact — an International Tables number is an identifier, not a quantity |

The deterministic half agrees with 41 of 42 at tolerance 0.01 and 40 of 42 at
0.1, which is what establishes the determinations are recoverable from the
files at all.

**No pass or fail is stamped on a symmetry comparison.** Declaring one of two
independent symmetry programs correct about a structure is a crystallographic
judgement this layer does not make. Disagreements are named; the tolerance
travels with the number.

### K3 — the product was already known

| | |
|---|---|
| whose finding | the critique, Table I, E4 |
| count | **2** — 3 flags are printed; `Y3Ga3In2O12` is offline and outside the evaluation population |
| what a check must do | look the composition up in a pinned snapshot and report matching entries |
| what to compute | a lookup of the composition in a crystallographic reference corpus, returning the matching entries and which corpus they came from |

| | open database | licensed index |
|---|---|---|
| chemical systems | 27,311 | 48,532 |
| of 43 compounds: exact match | 3 | 16 |
| **flags in the evaluation population** | **0 of 2** | **2 of 2** |

The licensed index returns the same collection codes the critique cites — 74287
for MgTi4(PO4)6, 139006 for MnAgO2 — which is the same database entry, not a
coincidence of composition matching.

**Licence-conditional.** A result from the licensed index is reproducible only
by a licence holder. That condition travels with every number from this group.
`reference_structures` returns `licensed: true` and, where the file is absent,
a stated reason rather than an error.

### K4 — the cubic lattice parameter derived from each A-Lab CIF

| | |
|---|---|
| whose finding | the critique, Table II |
| count | **5** |
| source file | `data/labels/prx_table2.csv`, two-method verified |
| what to compute | the cell of the deposited structure, converted to a cubic parameter by a stated route |
| tolerance | **0.0005 Å**, travelling with the number |

Not one formula five times: two go via `mean(a,b)·√2`, one via `c`, two via
`(4V/3)^⅓`. The convention follows the deposited setting, which is what makes
this a check rather than a lookup.

### K5 — per-compound structural statements in the critique's prose

| | |
|---|---|
| whose finding | the critique, section IV prose |
| count | **3** — 4 prose claims are transcribed; one is on an offline compound |
| source file | `data/labels/prx_prose_claims.csv` |
| survey | the four-reader enumeration of the critique's 272 specific claims, in the research repository; the rows it yielded are transcribed here with their loci |
| what to compute | the cell, and the per-site species and occupancies, of the deposited structure |
| status | **two-method transcription, 29 August 2026.** A second independent pass, by two routes that did not see this file until their own lists were fixed, confirms P1, P2 and P4 on value and locus, queries P3's value against a tightened definition of the quantity, and finds the file short by one row. All of it is in the file's own header |

Four, not the seven previously claimed, and the correction is on the record.
Of the sixteen candidates whose transcription status was unknown, **every prose
space-group claim duplicates Table III** — checked one by one — and several
more are bookkeeping ("18 new phosphate phases") rather than assertions about a
file.

### K6 — the two-stage protocol, end to end — **CEILING GROUP, STAGE TWO ONLY**

> **Restored to the ceiling 28 August 2026, scoped to stage two.** It was
> labelled "not a ceiling group", which read as demoted for quality when the
> truth is scoped for evidence. Two grounds were given and only one holds.
>
> *The weak ground:* a blind check cannot derive the statistic or its 0.776
> threshold. True, and not disqualifying — K2 asks a verifier to reproduce a
> determination two defensible programs disagree about, and this ceiling
> handles that by refusing to stamp pass or fail and letting the margin
> travel. K6 gets the same treatment: `Ba6Ta2Na2V2O17` at 0.7651 against a
> 0.776 threshold is **named, not counted against anyone**.
>
> *The hard ground, which stands:* its inputs are the **manual** refinement
> columns. Measured across the 40 — the target weight fraction differs between
> stages by a median of **9.2 points**, a maximum of **74.4**, and by more than
> 10 points on **18 of 38** compounds. `Mg3MnNi3O8` reads 100.00 at stage one
> and 25.62 at stage two. A stage-one verifier computing this statistic is not
> reproducing the baseline's decision; it is computing a different number from
> different inputs.
>
> So K6 belongs to the ceiling and is scoreable **only at stage two**, counted
> apart from the 55 and never pooled.
>
> **It fired on 29 August 2026 and was scored.** It had previously read as
> unscored, which was described at the time as no stage-two release ever having
> fired. That was a fact about the harness, not about any verifier: four
> separate gaps each sufficient alone meant the release reached nothing. All
> four are closed. Scored from the observation channel, the run agrees with the
> external key on **8 of 8 compounds where the source asserts and 32 of 32
> where it does not — 40 of 40**, against a do-nothing line of 32 of 40, with
> the statistic matching the published key to four decimal places on every
> compound.


| | |
|---|---|
| whose finding | CARTOGRAPH, a published system |
| count | **40 decisions**, **8 flagged** at their frozen threshold — 4 inconclusive, 4 confirmed, matching the published result exactly |
| source file | `data/labels/cartograph_decisions.csv` |
| what a check must do | read the refinement row and reach the same decision |
| what to compute | from the released refinement row: the fit residual, the target phase's weight fraction, and the largest **single** impurity fraction — all three from one reading |

The only group whose key comes from another **automated system** rather than a
human panel — and the key is the external check on the last step of the
protocol, not a score to beat. What is measured is the sequence: abstain, name
the analysis that would settle it, read what you are given, decide.

**Never reported as one percentage.** The baseline passes 32 of 40, so a layer
that flagged nothing would score 80 per cent, and a bare percentage on this
group is mostly that base rate. The scorebook prints the split and the
do-nothing line instead — this is the 29 August run:

```
agreed where the source ASSERTS  : 8 of 8
agreed where the source does NOT : 32 of 32
NO SINGLE FIGURE for this group: a layer that asserted nothing would
score 32 of 40 (80%) without doing anything.
```

> **CORRECTED 28 August 2026.** The first answer key for this group, generated
> 27 August, used `(100 - w_target)` for the statistic's third term as well as
> its second. `w_alt` is the **largest single impurity phase fraction**. The
> wrong version double-counts the target deficit, is systematically larger
> whenever a refinement found two or more impurities, and put **9** compounds
> over the threshold instead of 8 — the extra one, Ba6Ta2Na2V2O17 at 0.8284
> against a true 0.7651, being a borderline crossing manufactured entirely by
> the error. Every K6 number computed before the correction is void.
>
> The cause was not the bracket convention or a difference of input path. A
> validated implementation of this statistic already existed in
> `bench/reproduce_baselines.py`; regenerating the key by writing the formula out
> again, instead of calling that function, is how a document and its own
> answer key came to disagree. The key is now produced by calling `rho_alab`,
> so the two cannot diverge again: they are one code path.

---

## 3. The whole ceiling

These are the counts `build_targets()` constructs, reported in
`data/labels/ceiling.json`. The **printed** column is what
the critique publishes; the **targets** column is what survives §2's exclusion
rule, and only that column is a denominator.

| K | finding | whose | printed | targets | shape |
|---|---|---|---|---|---|
| K1 | file differs from the claim | critique | 8 | 7 | flag |
| K2 | symmetry per deposited file | critique | 43 | 38 | value |
| K3 | already known | critique | 3 | 2 | flag |
| K4 | cubic lattice parameter | critique | 5 | 5 | value |
| K5 | prose structural statements | critique | 4 | 3 | value |
| K6 | the two-stage protocol, end to end | baseline key | 40 | 40 | flag — **stage two only, see §2** |

**The ceiling is 55 stage-one findings (K1-K5) plus 40 stage-two decisions
(K6): 95 in all, never pooled.** The 40 baseline decisions are
a comparison field beside it, not part of the denominator.

Each drop is §2's, and each is named there: `Mg3NiO4` is offline and outside
the evaluation population (K1), `Y3Ga3In2O12` likewise (K3), one prose claim is
on an offline compound (K5), and K2 loses five — two offline, the removed
compound, and the two symmetry determinations where two independent programs
disagree and the benchmark declines to say which is right.

**All reachable.** This read "none reached by an elicited check — the
measurement has not been taken", which was true while every banked check
predated the observation channel, the refinement primitive and the reference
lookup. It is no longer. K1 has been reached in full by one arm (§2), and K6
was scored end to end on 29 August at 40 of 40 against a do-nothing line of 32
of 40. The stage-one groups K2 to K5 remain measured only against checks bought
before the vocabulary that reaches them existed, so their numbers say more
about the vocabulary than about any verifier.

---

## 4. How a target is scored

`bench/score_targets.py`. One score per target, never one number.

| outcome | meaning | in the denominator? |
|---|---|---|
| **RECOVERED** | the observation matches the expert value at the stated tolerance; or for a flag target, the ledger verdict matches the expected flag | yes |
| **MISSED** | a check ran and reached a different answer | yes |
| **NOT-OBSERVED** | a check ran but recorded no observation of this quantity | reported separately |
| **UNVALIDATED** | a check refuted on this target's own evidence class, and the standalone checker cannot read that class. **Reached, not validated. Never a miss** | reported separately |
| **NOT-ATTEMPTED** | nothing that could reach this target was submitted, or no check that could reach it was bought | no |

Three rules make the number honest.

**Per-target exclusion.** A target leaves the denominator only when no check in
a family that could reach *that target* was elicited. The old rule excluded a
whole compound or none of it, so a compound that lost three of four checks to
transport failure still contributed every one of its targets.

**Flag targets are scored from the PER-CHILD witness verdict, not from the
compound-level ledger bit.** The bit is why K1, K3 and K6 were three reads of
one measurement: every flag group asked "is this compound refuted" and could
not help colliding. Each target now reads the verdict of the check carrying
**its own** evidence class.
Aggregation fails closed: a refutation counts only on an explicit independent
witness reproduction. Reading raw check status walked past that rule and
inflated one arm by three compounds, every one a witness that failed to
reproduce.

**K4 is scored on a declared conversion, not on consensus.** The pseudo-cubic
parameter of a non-cubic crystal is an approximation and more than one route to
it is legitimate; measured on these five the routes disagree by 0.0082 to
0.0516 Å — **16× to 103× the 0.0005 Å tolerance** — and the critique itself
used `c` on `Zr2Sb2Pb4O13` and `mean(a,b)·√2` on the near-identical
`Hf2Sb2Pb4O13`. No rule derivable from the file reproduces that choice. A value
therefore counts only when it is a **correctly computed standard conversion of
this compound's own deposited cell**, which a scatter of guesses cannot satisfy,
and the attempt count is printed beside the score.

**NOT-OBSERVED is not a miss.** Until 27 August the layer had no field for a
check to record a value in. "The arm got it wrong" and "the layer could not
write it down" are different failures, and pooling them would flatter the
layer.

---

## 5. What is deliberately not on this list

| | why |
|---|---|
| populations and the counting rule | our own bookkeeping |
| the critique's printed flag totals | checks our transcription, not the method |
| "our scanner flags 10 of 42 files" | **our own output. Not a target. Never a result** |
| the 42 refinement rows themselves | **evidence, not findings.** Reading Rwp out of the deposit reproduces nobody's judgement |
| mutants | planted truth. They measure detection competence, and they are the benchmark offered to other people |
| rival file hashes | integrity of our own artifacts |
| E1, fit quality (18 flags) | the observed intensities are not in the deposit, and the reported Rwp does not substitute: AUC 0.64 against the flag, and the best balanced threshold catches 10 of 18 at 4 false alarms. **A scope boundary, not an impossibility** — the critics judged E1 from the published refinement plots, and digitising those is the route this benchmark does not yet supply |
| E3, ordering without evidence (24 flags) | not a label source. The layer's corresponding output is a priced abstention, so scoring one against the other mismeasures both |
| the Correction's four inconclusive verdicts | **withdrawn as K7 on 27 August.** See below |

### The withdrawal of K7, kept because the reason is the useful part

K7 proposed scoring the layer on abstaining across the Correction's four
inconclusive compounds. All four arms score 4 of 4. **It is worthless.**

The layer has no affirming verdict, so `cannot_verify` is its default for
everything it does not refute:

| arm | abstains | of the 4 | of the 36 **confirmed** | P(4 of 4 by chance) |
|---|---|---|---|---|
| opus5 | 30 of 40 | 4 | 26 | 0.30 |
| sonnet5 | 33 of 40 | 4 | 29 | 0.45 |
| gpt56 | 37 of 40 | 4 | 33 | **0.72** |
| gpt56-terra | 37 of 40 | 4 | 33 | **0.72** |

For two arms, "4 of 4" is more likely than not by chance at their own
abstention rate. An arm that abstained on all 40 would also score 4 of 4.

There is a real question underneath, and one signal discriminates:
SET-INADEQUATE fires on 3 of 40, catching 2 of the 4 at a cost of 1 in 36
(P = 0.022 by chance). **But it is kernel-computed from the deposited
refinement table, identical across all four arms, and therefore not a
methodology result.** K7 returns only when a model-written check drives a
distinguished abstention, scored against that state and never against
`cannot_verify`.

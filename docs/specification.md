# The benchmark specification

*The benchmark as a whole. The target list is one section of this and lives in
`docs/ceiling.md`. Read `docs/ENTRANT.md` first if you are submitting; this is
the document behind it.*

---

## 1. What the benchmark is for

It measures one thing: **whether a verifier, given the deposited evidence an
expert panel had, independently arrives at the findings that panel published.**

It is not a chemistry benchmark. It does not ask whether the claims were true,
whether the critique was right, or whether the Correction was correct to
confirm what it confirmed. Every label in it is a documentary fact about what a
published source says.

One consequence governs everything: **a finding the layer produces that no
expert asserted is a false alarm of the instrument, not a discovery.** The
layer earns nothing for being interesting. It earns by recovering what is
already on the record, from the same evidence, without being told.

## 2. The ceiling is a part of this, not the whole

| component | what it fixes | where |
|---|---|---|
| populations and the counting rule | which 40, 41, 42, 43 or 36 a count is against | §3 |
| the label sources | which published source a target comes from | §4 |
| **the ceiling** | **what the targets are** | **`docs/ceiling.md`** |
| the verdict grammar | what a verifier may return | §5 |
| evidence stages | what a verifier receives, and what it must request for more | §6 |
| the seal | no label ever enters a prompt; one completion per subject per generation | §7 |
| scoring | per target, never one number | `docs/ceiling.md` §4 |
| the deterministic harness | that the targets are real and present in the deposit | §8 |
| controls | planted truth: mutants | §9 |
| the external baseline | the published system whose decision is K6's key | §10 |
| **the baseline key** | **`data/labels/cartograph_decisions.csv`, the per-compound pass/flag K6 is scored against** | **§10** |

A high score against the ceiling with a broken seal means nothing. **The
ceiling says what success would be; the rest says whether a score was earned.**

## 3. The material, and the counting rule

Five numbers recur, they are different numbers, and conflating them has
produced repeated errors in this project's own history.

- **41** compounds claimed in the 2023 paper.
- **40** claims the Correction adjudicated: 36 confirmed, 4 inconclusive. **The
  evaluation population.** Every scored result uses it.
- **42** compounds with deposited structure files: the 40 plus 2 made outside
  the autonomous run.
- **36** products the critique examined. *Not* the Correction's 36 confirmed:
  the critique's population includes the removed compound and both offline
  compounds and excludes seven the Correction adjudicated.
- **43** rows in the bookkeeping table: the 40, the removed one, the 2 offline.

**The rule: a count from one population is never quoted against another
population's denominator.**

*Two files were unreachable until 26 August* because the deposit and the
spreadsheet spell two formulas with their elements in a different order —
`Ba6Ta2Na2V2O17` against `Ba6Na2Ta2V2O17`, and a folder `Y3Ga3In2O12`
containing `Y3In2Ga3O12.cif`. One of the two, `Ba6Ta2Na2V2O17`, **is in the
evaluation population**, so every check on it was skipped for want of evidence
and its ledger row read as a verdict rather than as an absence. The
composition fallback now resolves both. The same fault class recurred on 28
August in the label join for K2 and was fixed the same way.

## 4. The label sources

Every score is a comparison against exactly one source, and two scores from the
same source are never independent confirmations.

1. **The critique's error flags** — E2 (8 flags, 7 in the evaluation
   population) and E4 (3 flags, 2 in it).
2. **The critique's symmetry column** — 43 determinations.
3. **The critique's taxonomy** — the experts' own decomposition of what "new
   inorganic material" means.
4. **The Correction's verdicts** — 4 inconclusive against 36 confirmed.
   **Record-agreement labels, never undecidability ground truth**: the phrase
   is "inconclusive from the X-ray data alone", a statement about the analysis
   performed, not a computed impossibility at a stated budget.
5. **Construction truth** — mutants, where the answer is built in by a
   committed generator.

**E1, fit quality, is out of scope here — but it is not impossible, and this
document said so for too long.** It read "a source no verifier can be scored
against: the measured patterns were never deposited. Settled, not re-argued."
The first clause is true of the *deposit*: the observed intensities are not in
it, and the shipped Rwp does not stand in for them. Measured on the 35
compounds carrying both a flag and an Rwp, the reported Rwp carries some signal and not nearly enough: against the E1 flag it scores an AUC of 0.64, where 0.5 is no information, and the best balanced threshold — Rwp above 9.5 — catches 10 of the 18 flagged compounds while flagging 4 of the 17 unflagged, an accuracy of 0.66 against a base rate of 0.51. The distributions overlap
across nearly their whole range — flagged 3.21 to 26.47, unflagged 1.94 to
21.14 — so E1 is not recoverable from what the benchmark hands a verifier.

**The critics recovered it anyway, from the published refinement plots**, which
is a judgement about whether a calculated pattern explains an observed one and
needs the pattern in front of you. The layer's own primitive stub records the
same route — `refinement_quality` is documented as "implementable only against
digitised patterns or new data". So the honest statement is a scope boundary:
this benchmark supplies no route to the observed intensities, and until it does,
E1 is not a target. "Impossible for everyone, permanently" was wrong, and
"settled, not re-argued" foreclosed a question the critics had already answered.

**E3 is not one of the sources.** It is a judgement about what a measurement
can support, and the layer's corresponding output is a priced abstention.

**Twins are retired** (27 August). Constructing a twin requires judging whether
a substituted compound is chemically plausible, which is a chemical judgement
this project does not make, so the layer could not verify its own control. What
it established before retirement: one pair, all four arms consistent, Wilson
interval 0.21 to 1.00; the twin carried no deposited structure file, so no
check ran against a structure. **Contamination now has no control.**
The retired twin labels stay in the research repository, because the
elicitations were bought and the seal permits one completion per subject. They
are not part of this benchmark.

## 5. The verdict grammar

**Two grammars, and they are not the same list.** What a submission may return
is three verdicts; what a decision procedure may conclude internally is five
states. Both refuse to affirm, and confusing them is how someone submits
`UNDECIDABLE-AT-BUDGET` and is rejected.

**What you submit: three.** `refuted`, `cannot_verify`, `inapplicable`, and
nothing else — `VALID_VERDICTS` in `tools/score_submission.py`, specified in
`docs/ENTRANT.md` §3. A submission containing `verified` is refused by name.
Every one of the five states below maps into one of these three, and it is the
three the scorebook reads.

**What a decision procedure may conclude: five.** These are the internal states
of *our* layer's rule, given here because the benchmark's pricing and
abstention vocabulary is defined in terms of them and the ablation conditions
report against them. **An entrant is not required to produce them, is never
scored on them, and need not have a decision procedure shaped like this at
all.** They are five distinguishable reasons for declining to refute, and the
compound verdict every one of them maps to is `cannot_verify`.

| state | meaning |
|---|---|
| **REFUTED** | carries a witness: where the check looked, what it observed, what the claim required. A refutation without a witness scores as no verdict |
| **UNDECIDABLE-AT-BUDGET** | certified only when a rival's proved converse floor exceeds the budget. The achievable-side surrogate can never certify impossibility |
| **BOUND-INCONCLUSIVE** | the budget falls between floor and achievable bound, or a rival could not be priced, or no admissible rival exists |
| **CONSISTENT** | every admissible rival's achievable bound fits the budget. A CHILD-INSTANCE state; the compound verdict it maps to is `cannot_verify`, so it affirms nothing |
| **SET-INADEQUATE** | the offered hypothesis set — the claim plus every admitted rival — accounts for less than the declared floor of what the deposited refinement reported. **Wired 27 August** |

**A witness is valid only when an independent tool establishes a
contradiction** between the deposited file and the claim record. Presence of
the observed values is necessary and never sufficient. The requirement is read
from the claim record, not from the witness's own text, because that text is
written by the same untrusted model that wrote the check.

**Every verdict may carry observations and a follow-up request** (both added 27
August; see the research repository's `methodology.md` §7 and §11, which does not ship here).

### The SET-INADEQUATE reason, withdrawn

It was previously declared unwireable because detecting inadequacy needs a fit
test against measured data the record lacks. **That was wrong.** It saw one
route where there are two: do your own fit and watch it fail, which needs the
patterns; or **read the reported outcome of a fit someone already performed**,
which needs only the table.

`COVERAGE_FLOOR_PCT = 50.0`, declared in the code before it was run against
anything. No threshold search was performed against any label.

## 6. Evidence stages

**Stage one** is the automated analysis: the robot's own structure files and
refinement columns, present when the claims were made in 2023.
**Stage two** is the expert re-refinement, which exists only because the
dispute happened.

A verifier is scored on stage one alone. If it abstains **and names the
follow-up that would help**, it receives stage two and is scored again — **on
K6 and only K6.** K1, K2, K4 and K5 are documentary statements about the
automated deposit, and their targets are defined at stage one; scoring them on
a pass that released the expert re-refinement would compare a check against a
target defined on different evidence.

**What is released is the refinement row, not a replacement deposit.** Stage
two hands over the expert's refinement columns for the same specimen; it does
not substitute the structure file underneath a check written against the
deposited one. 41 of 42 deposits differ in lattice parameter beyond the
tolerance that parameter is scored at, and with the model held fixed the
substitution alone moved K1 from 6 of 7 to 5 of 7 and K4 from 4 of 5 to 1 of 5.
The deposited file is the object under audit; re-analysing a pattern does not
change what was deposited.

**Release is conditioned on a matching request, not on a flag.** Stage two
supplies a re-refinement against an expanded phase set. It is **not** a longer
measurement. A verifier that abstains and asks for counting time gets nothing,
and that is a fact about the verifier.

**Contamination is declared, per the owner's ruling of 27 August.** Stage-two
evidence was produced by people who knew the outcome, so it encodes the outcome
implicitly. That is the cost of a retrospective study: declare it and proceed,
rather than fabricating evidence and risking getting it wrong. Every stage-two
row carries the declaration, is scored separately, and is **never pooled** with
stage one.

## 7. The seal

- No expert label, flag, verdict or finding ever enters a prompt.
- A model writes a check once and never sees its result.
- **One completion per subject, per generation.** A generation is a version of
  the check vocabulary. `--generation N` writes to a separate directory and
  earlier generations are never overwritten; `run_chain` refuses to start in a
  populated generation directory without `--fill`.
- Selection over decomposition samples is coverage-graded, never
  verdict-graded.
- No fallback models. A refusal is data.

## 8. The deterministic harness, R1 to R8

`bench/reproduce_benchmark.py`. **Without the deposit, 10 of 13 attempted
checks reproduce** — measured 29 August on a clean checkout. R5 and R6 cannot
run at all without it, and R4 has nothing to recompute, reporting zero
determinations rather than failing, which is a hole in the harness worth
knowing about. The third failure is real and stays failing: R7c, added the same
day, resolves each recorded hash to the file it names and catches the
`Ba2ZrSnO6` collision in `known-defects.md` §8i.

The table below is the **full-deposit** run. Its figures predate R7c and were
recorded when the harness reported 15 of 15; with R7c they become 15 of 16, and
that arithmetic has not been re-run against a fetched deposit.

| R | what it reproduces | whose claim | result |
|---|---|---|---|
| R1 | populations and the counting rule | ours | 4 of 4 |
| R2 | the critique's printed flag totals | critique | E1 18, E2 8, E3 24, E4 3, exact |
| R3 | our file scan against the E2 flags | critique | 7 of 8 |
| R4 | the symmetry column, recomputed | critique | 41 of 42 at 0.01; 40 of 42 at 0.1 |
| R5 | Table II lattice parameters | critique | 5 of 5 to 0.0005 Å |
| R6 | the external baseline | CARTOGRAPH | four compounds by name; 32 of 36 passed; Rwp-only ablation exact |
| R7 | the mutant demonstration set | ours, planted | 7 mutants, prices 51 to 1.65e6; **R7c fails: 1 hash resolves to a different file** |
| R8 | shipped rival files against their hashes | ours, integrity | 6 of 6 redistributable, 1 withheld under licence |

**What passing means, precisely.** The deterministic half is *aimed*: we read
an expert table and wrote code to recompute it, knowing the target. Passing
proves the finding is genuinely present in the deposit and nothing beyond it
was needed. **That is the bare minimum — it means the benchmark works as a
technicality.** It does not mean the benchmark is scientifically good, and it
says nothing about the method. **Its use is for building the benchmark, not
for measuring.**

Only R3, R4, R5 and R6 carry a methodology target. R1, R2, R7 and R8 carry
none.

**"Our scanner flags 10 of 42 files" is our own output, not a target, and must
never be quoted as a result.** The only number that matters against E2 is how
many of the eight the method reaches.

Not attempted: E1 (evidence never deposited) and the Correction's own analysis
(this project holds no copy, only a verdict transcription).

## 9. Mutants — the benchmark offered to other people

`bench/mutate.py`, generator version `mutate-0.3.0`. Six families:

| | |
|---|---|
| M1 | ordered-assertion: assert the ordered model where the truth is the disordered parent |
| M2 | occupancy-permutation: swap two cation species between sites; assert the original |
| M3 | cation-substitution: replace cations with same-family neighbours |
| M4 | spurious-phase: mix a second phase in at weight fraction w; assert the pure phase |
| M5 | degraded-counts: check against a Poisson draw at N counts |
| M6 | underdetermined-pair: profiles within epsilon under the noise model; ground truth is cannot-verify **by construction** |

Every mutant is wrong by construction, with the truth and a difficulty number
recorded **outside** the claim. A claim handed to a model never contains its
own answer.

**Mutants are not a methodology target.** Their truth is planted by us, so they
measure detection competence rather than reproduction of expert findings. **A
rating and a mutant score answer different questions and neither substitutes
for the other.**

**This M-family demonstration set has never been run on any arm.** The other
constructed set has: the H1/B1 contamination control was run on 28 August 2026
across seven configurations, and its result is in `docs/contamination-set.md`.
Two constructed sets, two different jobs — the M families price detection
difficulty, the H1/B1 pair tests whether a verifier reads its evidence or
recalls the dispute — and only the second has been executed.

## 10. The external baseline

CARTOGRAPH (arXiv 2606.07576), reproduced exactly from the paper. Their
statistic, Appendix I:

    rho = sqrt( (Rwp/20)^2 + ((100 - w_target)/100)^2 + (w_alt/100)^2 )

At their frozen threshold 0.776 we recover their four inconclusive compounds
**by name**, 32 of 36 confirmed passed, and their Rwp-only ablation exactly
(0 of 4, 2 of 36). Our calibration gives 0.8341, inside their published
bootstrap interval [0.496, 1.088] and **not equal to their point value**, which
is reported as a difference rather than smoothed over. Their target-deficit
ablation **does not reproduce**: ours 3 of 4 and 2 of 36 against their 4 of 4
and 4 of 36. That stays on the record as a failure to reproduce.

*The instructive failure that preceded it.* Before the paper was read, a search
over linear combinations of the three numbers our own seed described could
reproduce nothing, and the published constant ruled out every natural
candidate. **The obstacle was our paraphrase, not their publication.** A
baseline that cannot be rebuilt from its description cannot serve as the thing
new verifiers are measured against.

**The shipped answer key and this reproduction are one code path.**
`data/labels/cartograph_decisions.csv` is generated by calling `rho_alab`
through `phase_fractions()` — the same function this section's numbers come
from — and reproduces 4 of 4 inconclusive, 4 of 36 confirmed and 32 of 36
passed. Between 27 and 28 August it did not: the key had been regenerated by
re-writing the formula rather than calling it, `w_alt` was implemented as
`100 - w_target` instead of the largest single impurity fraction, and the key
flagged 9 where this section says 8. Two sibling documents citing two
generations of one computation is this project's own named error class, and it
recurred between two sibling documents on the day they were written.

**The baseline is stage-two by construction.** All three of its inputs are
expert re-refinement columns, so it could not have run in 2023, and any
comparison has to say so.

## 11. The stance

The expert record is this benchmark's reference standard. The benchmark
mechanises, prices and replays published judgements; it does not audit the
chemistry, rank the panels, or adjudicate what was or was not synthesised. No
individual is characterised anywhere in it.

Where a method proves insufficient, the evidence shows it and the prose does
not argue it. Failed predictions are reported as failed, by name, permanently.

The episode is used because it is the best-documented case of a question the
whole field now faces — when a machine asserts a scientific result, what would
it take to check it — and because the people who fought it, on both sides, left
a record careful enough to build on.

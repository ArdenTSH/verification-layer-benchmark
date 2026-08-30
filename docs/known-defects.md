# Known defects

*Everything known to be wrong, weak, unverified or licence-bound. 28 August
2026. Written for whoever checks this work hostilely, on the principle that the
author's guess about where his own work is weakest is worth writing down. If
you find something not on this list, the list is the defect.*

---

## 1. Things that are heuristic and admit it

### The purity keyword matcher — the only one left

`claim.statement_payload_consistent`, heuristic half. Matches purity **wording**
against a list. **Measured: 3 wrong in 10** on hand-written statements,
including a **negated** claim — *"we cannot claim the sample is phase-pure"* —
flagged as an assertion of purity, and two misses.

Mitigations, none of which make it sound: it **gates nothing** (removed from
`validate()` the same day it was added); every finding carries the literal
string `heuristic-keyword-match`; the docstring prints the error rate; the
sound half beside it parses an explicit percentage and infers nothing.

Safety does not rest on it: `entailment.classify` marks every weight-fraction
child STRONGER whatever its wording.

**Attack it by** writing statements that assert purity without the listed
words, or that negate it using them.

### Everything else was checked and is not keyword matching

`entailment.classify` dispatches on `family`, a controlled field.
`set_coverage` matches by composition-reduced formula. `_phase_core` strips a
trailing annotation **only when stripping makes the string parse as a
composition** — falsified by a parser rather than accepted. `gate_proposal`
tests key presence, never wording. `follow_up` matching is exact against a menu
the model reads as data, with canonicalisation of case and separators only.

---

## 2. Declared constants that are not validated

Every one was declared in code before being run against anything, and none was
searched against a label. That makes them honest. **It does not make them
right.**

| constant | value | attack it by |
|---|---|---|
| `COVERAGE_FLOOR_PCT` | 50.0 | checking whether the three SET-INADEQUATE compounds change at 40 or 60. The number is round and was declared only just before use |
| `NEAR_MATCH_TOL` | 0.02 | finding a composition pair that should or should not match |
| `NEUTRON_WAVELENGTH` | 1.5406 Å | it is not a published instrument fact; it is chosen to hold geometry fixed |
| pattern-identity floor | 1e-9 | the origin-shift attack was rejected by two tests, so this one is not load-bearing alone |

## 3. Unverified computations

**The neutron price is validated against nothing.** The X-ray path was
validated in gate one; the neutron family reuses that forward model with the
scattering table swapped and has no independent check. It currently feeds only
the follow-up menu's `power` field and no verdict.

**The bracket convention** — that a sole listed phase in the refinement table
is a single-phase fit at 100 per cent — is an inference from 28 unbracketed
cells with **no counterexample and no documentation from the depositors**. It
is load-bearing: it produced every automated phase fraction and therefore K6's
inputs.

## 4. Licence-bound and unreproducible by others

**K3 works only with the ICSD index.** The open database recovers 0 of 2 flags;
the licensed index recovers 2 of 2. The file is gitignored and its hash is
recorded, so a result stays traceable, but **a reader without an ICSD licence
cannot reproduce any K3 number.** Whether such a result may be published at all
is an open decision.

## 5. Security

**Isolation is not a sandbox and the module says so.** The child process is
started without credentials — verified with a planted canary — but it can still
read the filesystem and open a socket. A seccomp or container boundary is not
built. The gate and restricted builtins remain in front of it.

**The gate has been wrong three times, and the third is OPEN.** Two adversarial
audits found live-credential routes, one through `ctx._path` and one through
attribute traversal inside a format string. Both are closed. **A third is not
"not ruled out" — it is confirmed and reproduces today.**

CPython's introspection attributes — `gi_frame`, `f_back`, `f_builtins`,
`co_*`, `tb_*` — **do not begin with an underscore**, so the gate's
`node.attr.startswith("_")` rule never sees them. A generator's frame reaches
its caller's frame, which holds the *full* builtins whatever restricted set was
handed to the check. Verified end to end on 28 August: the gate returns no
problems, and through the real `run_check_isolated` path the check read a file
from disk at frame depth 1. Consequences are arbitrary read and write with the
repository as the working directory, arbitrary import, and network — and it
**defeats the credential story**, because the scrub removes credential-shaped
*environment variables* while the key sits in `.env` at the repository root,
which this reaches with `open`.

**The fix is not another prefix rule.** Patching `startswith("_")` to also
catch `f_`/`gi_`/`co_`/`tb_` closes this instance and not the class; the
introspection surface grows with the language. The durable fix is an attribute
**allowlist**. Measured against 864 banked checks that pass the gate today, an
allowlist of the 14 real `Ctx` methods plus the ordinary container and string
methods blocks all three known escapes and two further variants, and newly
blocks **8 checks, 0.9 per cent** — every one of them calling a `Ctx` method
that does not exist and that raises at runtime anyway.

It is **not applied**, because the isolated child re-imports `probe.py` on
every check and the generation-2 campaign is live: changing the gate mid-run
would mean two execution semantics inside one generation. It goes in when the
campaign lands, followed by a rebuild.

**Attack it by** finding a construct the gate does not anticipate, then asking
what it could reach in a process that holds no key.

## 6. Transcription

**K5 is single-method** and therefore not quotable. K2 and K4 are two-method
verified — but **the two methods share a parsing library**, so a defect in
pypdf's page handling would be invisible to both.

**K5's count was corrected from 7 to 4** after finding that every prose
space-group claim duplicates Table III. If that check was wrong, the
denominator is wrong.

## 7. Structural limitations of the design

**The follow-up request is made blind.** The kernel prices rivals *after* the
check runs, so the model names a modality without knowing which rivals survive.
It chooses on the claim and the file. That is weaker than the design imagines
and it is the strongest request the seal permits.

**K2 had a base-rate problem nobody had priced. Priced and split since.** The
critique's Table III gives `proposed` and `indexed` symmetry per compound, and
they are equal on most rows — **35 of the 38 targets**, once the exclusion rule
has run; it read 39 of 43 against the printed rows when this was first written.
So a verifier that simply echoed the claimed space group, without opening the
file, would score those 35, and a single K2 percentage is roughly 92 per cent
base rate. This was the third instance of the same failure mode, after K7 and
the K6 aggregate.

**The scorebook now prints the two apart and refuses to sum them**: `where the
determination equals the claim (echo-level)` against `where it DIFFERS from the
claim (requires the file)`, 35 and 3. Only the second distinguishes a verifier
that opened the file from one that echoed what it was handed, and no combined
K2 figure is printed at all — printing one would reinstate exactly the number
the split exists to remove.

*Related, and unresolved:* our own recomputation disagrees with their `indexed`
column on `MgTi4(PO4)6` (they print R3/146, we compute R-3/148 at every
tolerance from 0.001 to 0.3, with no partial occupancies) and on
`FeSb3Pb4O13`. **Both are rows where `proposed == indexed`.** Either they
re-indexed and two programs genuinely differ, or that column reproduces the
proposed value where they saw no problem. The data cannot distinguish these,
and K2 scores exact-match against it either way.

**Contamination has a control, and it has been run.** Twins were retired on 27
August because constructing one requires judging chemical plausibility. Healed
and broken mutants replaced them and were **run on 28 August across seven
configurations** (`docs/contamination-set.md`): construct the ordered file the
claim itself asserts, and see whether a verifier still flags the famous
compound. It does not — all seven score H1 2 of 2, the memorisation-sensitive
direction, clean across four models and three unlayered conditions.

The claim this amends rather than deletes: *every claim about models not having
memorised the episode is unsupported* is now **weakly supported, for these six
compounds, in the H1 direction only.** Six compounds and one run give Fisher's
exact p ≈ 0.067 on a flawless result, so it is consistent-with and not shown.
The standing partial bound — the false-alarm rate on the 36 compounds the
Correction confirmed — still applies and should still be quoted as exactly
that.

**SET-INADEQUATE is kernel-computed**, identical across all arms, and is
therefore not a model achievement. It must never be reported as one.

**The layer has no affirming verdict**, so abstention is its default. Any
metric shaped like "did it abstain on the right ones" is measuring a base rate.
That is why K7 was withdrawn.

## 8. Measurement state

**The stage-one groups have not been measured by a check bought against the vocabulary that reaches them.** Every banked stage-one check predates the observation channel, the refinement primitive and the reference lookup, so K2 to K5 say more about the vocabulary than about any verifier. Two things have since been reached: K1 in full by one arm, and K6 end to end on 29 August across all 40 of its targets (§8g, §8h). This paragraph read "none of the 63 ceiling targets" — 63 is the pre-exclusion count §8f records as wrong, and the ceiling is 55 plus K6's 40.

**opus5's generation-1 ledger still carries holes**: 14 of 40 compounds have at
least one check that failed elicitation, after 16 of 35 fill attempts failed
again on transport errors.

**The M-family mutant set has never been run on any arm.** Detection competence is unmeasured. The other constructed set, the H1/B1 contamination control, was run on 28 August; see above.

## 8a. Fixed on 28 August under referee pressure

| was | now |
|---|---|
| K1, K3 and K6 all scored off **one compound-level bit**; on 8 of 9 compounds carrying more than one flag target their expectations conflicted, so no verifier could satisfy both | each flag target requires a refutation from the family carrying **its own** evidence class; K6 removed from the flag comparison entirely |
| answer keys claimed "computed by `score_targets.py`" with **no writer in existence**; three artifacts carried three different values for the do-nothing bar | `tools/build_ceiling.py` is the sole writer, calls `rho_alab` rather than restating it, and stamps an input digest that `--check` verifies |
| `space_group_number` returned **0** on engine failure, so `!= claimed` false-refuted | returns `None` |
| process-wide `filterwarnings("ignore")` suppressed the occupancy warnings the benchmark is about | narrowed to CIF formatting noise |
| `--resume` alone bypassed the overwrite guard | only `--fill` may enter a populated generation |
| `cmd_run` execed with **full builtins** while claiming to be sandboxed | uses `exec_builtins()` |
| the converse floor was described as certifying that **no test decides the pair**; the free-parameter comparison is not certified | restated; every emission carries the caveat, and the zero-emission count is reported |
| δ/m applied to the floor, **over-certifying impossibility** | **fixed, rule `decide-0.4.0`.** The correction is a union bound and belongs to the achievable side only; undecidability needs one unclearable rival, not all of them. Inflation measured 1.40× (m=2) to 3.33× (m=50); at m=2 it crosses a 1e7 budget the true floor does not. Rebuild verified: 0 verdict changes, 2 of 35 floors lower. **`m` still counts proposed rather than admitted rivals — open, safe side** |
| no entrant interface: "others can run this" was unhonourable | `docs/ENTRANT.md` + `tools/score_submission.py`, scored by the same scorebook as our own arms |

## 8b. Fixed later on 28 August, after the second review

| was | now |
|---|---|
| the scorer joined compound names as **raw strings**; `norm_formula` existed and was never imported. `Ba6Na2Ta2V2O17` (prx_table3) and `Ba6Ta2Na2V2O17` (ledgers, entrant bundle) are one compound, so the K2 target was **unreachable by anyone**, including an entrant submitting the exactly correct answer under the bundle's own spelling | every join goes through one module-level composition key. Verified: that entrant submission now scores RECOVERED, and opus5's K2 coverage moves 39 → 40 of 43. **Third occurrence of this fault class**, so the scorer now also names any target its ledger cannot see, as a standing regression watch |
| the scorer would have **degraded silently to string joins** if pymatgen were missing, reporting a plausible number | refuses to score, by name |
| "0 UNDECIDABLE-AT-BUDGET across **2,424** child instances" | **808**. The 2,424 was the same 808 counted once per rebuild directory — one set of purchased checks re-executed under three kernel versions. True statement, denominator three times the independent evidence: this project's own named error class, turned on itself |
| δ/m applied to the converse floor | rule `decide-0.4.0`, see §8a |

**The pattern in all four:** none was found by a test. Two were found by
attacking the published contract from outside it, one by pooling a number and
counting what went into it, one by asking what a stated deferral actually
blocks. Passing tests found none of them.

## 8c. The contamination set and the entrant scorer, 28 August

**Contamination set — three blocking defects, all fixed, one limit declared.**

| was | now |
|---|---|
| the claim carried its own answer: `provenance` and `structure_type` rendered into the prompt as *"contamination control B1 (broken: ... disordered on the claimed pair)"* | H1 and B1 payloads identical but for compound, group and file. `mutate._leaks()` refuses at construction |
| **a third leak survived the first two repairs**: `build_prompt` renders the evidence PATH, and files were `data/mutants/B1_<compound>.cif` | files mirror a real deposit, `<dir>/<compound>/<compound>.cif`, identical in both directions. The guard now checks the path too, on word boundaries so the atom label `Sb1` is not reported as `b1` |
| `H1_KPr9(Si3O13)2` was not healed: the 0.1/0.9 site was split 50/50, emitting `K5Pr5(Si3O13)2` — wrong compound, charge-imbalanced — which legitimately refutes its own claim | removed. `_assert_composition_preserved` compares **element ratios** and refuses any construction that changes the compound. `Mg3NiO4` looks like a free replacement and fails identically at 0.75/0.25 |
| all four B1 compounds were flagged by the critique, **three under E3 — the very fault B1 injects** | four compounds carrying no critique flag of any kind, each verified fully ordered |
| "built, not run" — in fact **not runnable**: nothing wrote mutant claims, `score_chain` hardcoded the demo table | `mutate.py --emit-claims`, then `run_chain --claims-from contamination`; `score_chain --mutants` |

**The limit that care cannot fix: 2 healed and 4 broken cannot reach
significance.** A flawless result gives Fisher's exact p ≈ 0.067 one-sided.
This is declared, not padded: only two E2 deposits have a shared site at
exactly 1/2, and inventing more needs either an occupancy-matched ordering rule
or a chemical plausibility judgement, which is what retired twins. **Any result
here reads as "consistent with" and never as "shows".**

**Entrant scorer — two attacks fixed, two open and declared.** See
`docs/ENTRANT.md` §7a for all four with their measured effect. The two open ones
are the `P 1` expansion convention and submission enumeration. **Our own arms
were manually checked against both and are clean**: no K1 recovery by any arm
rests on the `P 1` convention.

## 8d. The scorebook was paying out the enumeration attack on our own numbers

*28 August 2026, found by the adapter control.*

**`score_targets` credited a value target if ANY recorded value fell inside
tolerance.** A compound has up to sixteen children, each free to record the
same quantity, so the rule scored a scatter of guesses rather than a
determination.

Measured on opus5 generation 2, `cubic_lattice_parameter_a`: **36 of 40
compounds recorded more than one distinct value**, up to **ten distinct values
from fifteen children**.

| K4 rule | opus5 score |
|---|---|
| any-of (what shipped) | **5 of 5** |
| the arm's modal value | **0 of 5** |
| median | 0 of 5 |
| all children agree | 0 of 5 |

The 5 was the rule, not the arm. Three of the five modal values are not near
misses but the **wrong convention** — 7.49 Å against an expected 10.62 — so the
arm's checks disagree about which pseudo-cubic conversion to apply, and any-of
hid that disagreement completely.

**This is the enumeration attack `docs/ENTRANT.md` §7a declares against an
entrant, operating inside our own scorebook against our own headline number.**
An entrant submits one value per quantity and was being compared against an arm
allowed sixteen. Any K4 figure computed before this fix is void.

**Fixed:** the score is now the **mode** — the value the arm's own checks most
agree on — with the spread printed beside it, a tie scored MISSED because no
consensus can be resolved in the arm's favour, and an explicit note wherever
the old lenient rule would have scored RECOVERED.

**`space_group_number` is unaffected: zero compounds recorded more than one
distinct value.** K2's 38 of 43 was never an any-of artifact, and that
contrast is itself a result — the dispersion is a property of the quantity, not
of the channel.

**A join-by-name defect turned up inside the repair.** The first version keyed
the mode on raw strings, so a compound reporting both `194` and `P6_3/mmc` —
one determination written two ways — had its own two spellings tie against each
other, and a unanimous arm scored as having no consensus. K2 collapsed to 0 of
39 before the mode was keyed on the canonical determination. Fourth occurrence
of this class in four days, this time in an aggregation rather than a join.

## 8e. The adapter control: our two scoring routes do not agree

*Measured 28 August 2026, under the denominators in force that day — K1 of 8,
K2 echo of 39, K3 of 3. The exclusion rule has since dropped those to 7, 35 and
2, so the table below is a record of a comparison and not a current score. What
it is evidence for is the disagreement between the two routes, which is a ratio
and survives the change.*

Our arms are scored from a ledger; an entrant from a JSONL through
`tools/score_submission.py`. Both end in the same scorebook by different
routes. `tools/ledger_to_submission.py` projects a layered arm into the entrant
format so the routes can be diffed on identical work.

**They disagree**, with both sides on the modal rule and the projection
emitting the mode:

| group | ledger route | entrant route |
|---|---|---|
| K1 | 6 of 8 (attempted 7) | **4 of 8** (attempted 7) |
| K2 echo-level | 35 of 39 (attempted 37) | **30 of 39** (attempted 32) |
| K2 requires-the-file | 3 of 4 | 3 of 4 |
| K3 | 0 of 3 (attempted 2) | 0 of 3 (**attempted 0**) |
| K4 | 0 of 5 (attempted 5) | 0 of 5 (**attempted 3**) |
| K5 | 3 of 4 | 3 of 4 |

Known contributors: the entrant route re-adjudicates one witness per compound
while aggregation validated across all sixteen children (K1); the entrant route
fails closed on `reference-database` because the standalone checker cannot read
a corpus (K3, intended, §8c); and the projection loses observations the ledger
route still sees (K2 and K4 coverage). It is not established that these account
for the whole gap.

**The consequence for the no-layer ablation.** A no-layer arm is an entrant by
construction, so comparing it against a layered arm scored from a ledger would
measure the route. **Both conditions must be scored through the same route** —
project the layered arm into the entrant format and score everything with
`score_submission.py`. Absolute figures then differ from the ledger route, and
the comparison is internally valid, which is what the ablation needs.

## 8f. The extraction from the research repository, 29 August

The benchmark was split out of the research repository, where code lived in
`src/` and these documents in `v2/`. The split moved the files and left the
paths, so a set of faults arrived that no test caught because nothing here runs
the entry points end to end from a clean checkout.

| was | now |
|---|---|
| seven files put `ROOT/"src"` on `sys.path` — a directory that does not exist here. **`tools/score_submission.py`, the one tool an entrant needs, accepted a submission, adapted it, and then died** with `ModuleNotFoundError: score_targets`; `tools/build_ceiling.py` could not rebuild either answer key | all seven point at `bench/`. Verified end to end: an all-abstain submission scores, printing K1 7, K2 38 split 35/3, K3 2, K4 5, K5 3 |
| `--emit-instances` skips any compound whose deposited file does not resolve, then wrote the result unconditionally. The deposit is gitignored, so **in a fresh clone it overwrote the shipped 40-instance bundle with zero instances** and printed "0 instances" as though that were an outcome | refuses to write when fewer compounds resolve than the population it read, and names the deposit as the cause |
| R7 read `results/mutants_demo.csv`; the set ships at `data/mutants_demo.csv` and `results/` is gitignored, so **R7 failed in every checkout** | reads the shipped set, falling back to `results/` for a fresh generation. R7 passes: 7 of 7 truthed and hashed |
| R8 required every hashed manifest entry to be present, including the ICSD file `.gitignore` excludes because it may not be redistributed, so **R8 failed in every checkout for the one reason that is by design** | withheld entries are counted and named separately from missing ones. R8 passes: 6 of 6 redistributable, 1 withheld |
| `--rate` read `data/labels/ceiling.json`, superseded by the per-target scorebook and not shipped; it died on `FileNotFoundError` | says it is superseded and names `tools/score_submission.py` |
| `docs/ceiling.md` §3 carried a pre-exclusion generation — K1 8, K2 43, K3 3, K5 4, "57 stage-one findings … 97 in all" — while §2 four pages above already gave the corrected counts. **Its own table summed to 63, not the 57 it stated** | §3 prints printed-vs-targets side by side and totals 55 and 95, matching `ceiling.json`. The five K2 drops are named |
| the README said the mutant generator was "more code than the rest of the benchmark put together". Measured: 2,505 physical lines against 4,666, or 1,313 against 2,611 ignoring comments — **about half, not more** | "about a third of the code here" |
| the README said K6 "is reported separately, outside this repository", while its key ships and the scorer prints it under `EXTERNAL BASELINE` | the README says what ships and what is missing, which is the stage-two evidence |
| the README named K4 "the pseudo-cubic lattice parameter". The critique's Table II prints two columns and **that is the other one** — the ICSD comparison, not the A-Lab CIF target | "the cubic lattice parameter", matching the key, the scorer's title and R5. "Pseudo-cubic" survives where it belongs, on the conversion |
| the README's layout omitted the contamination set entirely — six instances, its truth table and its document — and put the mutants' truth in `data/mutants/`, where it is not | the layout lists every shipped path, and the contamination set has a paragraph |

## 8g. What K6 was measuring before 29 August, and why the old figure was void

*The group read **4 of 8** and the number did not mean what it appeared to. Six
independent defects sat between "the layer read the file" and "the layer agreed
with the baseline", and each broke a different link. Three were the benchmark's
and are listed here; the other three were the layer's and are recorded in its
own repository. Every K6 figure produced before 29 August 2026 is void — not
because the arithmetic was wrong, but because the route measured something
other than what its name said.*

| was | now |
|---|---|
| **the key and the evidence came from different stages.** The baseline's decision is computed from stage-two columns and every check read stage-one columns. The baseline's own statistic, run on stage-one inputs, scores 32 of 40 — exactly the do-nothing line. **No verifier reproduces the published decision from day-one evidence, the baseline included** | K6 is stage-two only, and `build_targets(stage="two")` returns K6 and nothing else. A stage-one pass cannot reach it and does not pretend to |
| **the group read one evidence family where its statistic spans three.** The baseline combines fit residual, target fraction and largest single impurity; the group was scoped to `weight-fraction`, and the layer records the first two mostly under `phase-present` and `novelty`. The evidence deciding the flag was structurally never the evidence the group read | K6 is scored from the **observation channel** through the baseline's own statistic, with no witness, no refutation and no family credit. Its exclusion test reads three families. The retired `baseline_flag` scoping is kept in the key as a record and decides nothing |
| **a stage-two pass rescored groups it had no business rescoring.** K1, K2, K4 and K5 are documentary statements about the automated deposit, and the stage-two rebuild substituted the expert's structure file — 41 of 42 deposits differ in lattice parameter beyond the tolerance that parameter is scored at. With the model held completely fixed, the substitution alone moved K1 from 6 of 7 to 5 of 7 and K4 from 4 of 5 to 1 of 5 | stage two releases the **refinement row, not a replacement deposit**. The deposited file is the object under audit; re-analysing a pattern does not change what was deposited. K1 to K5 are read from the stage-one pass, where their targets are defined |
| **the witness checker read the stage-one column unconditionally**, so a witness citing `ctx.refinement_row(stage="two")` was checked against stage-one figures, none of which match, and was refused. The refusal looked like the verifier inventing numbers when it had quoted the released row exactly | the predicate reads the stage the witness's `where` names. Detection is on `where` only — `observed` is prose the model wrote — and across the 1,024 witnesses banked before the change exactly one mentions stage two, whose `where` names no stage, so no banked verdict moved |

**The regression that was not one.** Generation 2 scored 6 of 8 on this group
and generation 3 scored 4 of 8, and the gap was read as the arm getting worse.
Scored as a reproduction from the observation channel the two generations are
**identical: zero of 38 compounds differ** in the layer's recorded values or in
the decision they produce. Generation 2's two extra hits were refutations
resting on a 95 per cent purity bar the model invented in its own `required`
text. Nothing about the model's measurement behaviour changed; the scoring
changed underneath it. **Neither the 6 of 8, the 4 of 8, nor the gap between
them may be quoted.**

## 8h. The v0 pass, 29 August

**K6's status was asserted both ways in live code. Settled 29 August.**
`score_targets.GROUP_TITLE` carried a comment arguing the demotion down while
the older "NOT a ceiling group. Demoted 28 Aug 2026" sat directly beneath the
title it contradicted, and `build_ceiling.py` wrote `is_ceiling_target: false`
for K6 under a note saying the baseline "is NOT a group here". Nothing read
either field, so no number ever moved. The owner's ruling resolves it, and not
by picking one of the two: **K6 is neither a demoted comparison nor a
reproduction of another automated system. It is the end-to-end test of the
two-stage protocol** — abstain, name the analysis that would settle the
question, be granted it, reach the baseline's decision. It is a ceiling group
scoped to stage two, `is_ceiling_target` is now true for all six, and the
scorer, the key, its generator, `ENTRANT.md` and `ceiling.md` all carry
that one framing.

What follows is what had to be closed to reach `benchmark-0`, which is stamped
into every scorebook this repository prints.

| was | now |
|---|---|
| **an entrant could choose which group they were scored on.** `score_targets.py` read `stage = "two" if "stage2" in children_path.name else "one"`, and a stage-two pass scores K6 alone — so the stage, and therefore the denominator, came from a filename anyone could type | the stage is read from what the submission **declares**: a pass is stage two when its rows name `re-refinement-expanded-phase-set` in `follow_up`, the modality stage two supplies. `--stage one|two` exists for a harness that already knows. Nothing infers it from a name |
| **the K1 and K3 blocks never printed false alarms**, though `ENTRANT.md` §5 promised every flag on a compound no expert flagged is counted and reported beside the recoveries. K1 has 7 targets over a population of 40, so a submission refuting everything recovered all 7 and its 33 other flags appeared nowhere — the always-refute strategy reading as a perfect score | flag groups print their false alarms, named, with an explicit line that they are never netted against the recoveries. Verified against a synthetic always-refute ledger: K1 now reports 33 compounds flagged that no expert flagged |
| **the entrant path graded symmetry witnesses against the entrant's own text.** `score_submission.py` built its `Claim` with only the compound, so `check_witness.check_space_group` fell through to the witness's own `required` field — which the submitter also wrote. This is the enabler for the `P 1` attack in `ENTRANT.md` §7a: 38 of the 40 deposited files record their symmetry as `P 1`, so naming any other group as "required" contradicts the file by construction | the claimed group is passed from the label table, joined by composition so a transposed spelling still resolves |
| **`formula_core` was computed and then withheld.** `bench_shim` derives it; the entrant bundle shipped only `formula`, the printed label with its polytype and provenance annotations. The deposit spells one compound's own phase `Ba6Na2Ta2V2O17` where the claim spells it `Ba6Ta2Na2V2O17`, so a string compare finds no target and counts the target's own 63.38 per cent as the largest impurity — inverting the quantity K6 reads. **That trap has caught a model twice** | every phase in the bundle carries both, and `ENTRANT.md` §2 says which one to match on and why |
| **K6's `_k6_layer_rho` took the plurality of each key independently**, mixing records across checks: on `Ba6Ta2Na2V2O17` it could read the target fraction from the check that identified the target and the impurity from the one that did not, producing a statistic neither check computed | the three terms must come from a **single** check, with a coherence guard rejecting any record whose largest single impurity exceeds the whole non-target remainder. Ported from the layer's own implementation rather than rewritten — reimplementation instead of reuse is this project's named failure mode |
| **K6 was described four different ways across the repository**, from "not a target" to "CEILING GROUP" | one framing everywhere: K6 is the **end-to-end test of the two-stage protocol** — abstain, name the analysis that would settle the question, be granted it, reach the external baseline's decision. It fired on 29 August and scored 40 of 40 against a do-nothing line of 32 of 40 |
| `docs/ENTRANT.md` said "Nothing you submit is scored on it" and "Stage two adds no scored group"; §6 documented the filename defect as though it were the design | both replaced. Stage two releases the **refinement row, not a replacement deposit**, and a stage-two pass scores K6 and only K6 |
| the paper plan quoted a 57-target ceiling | 55, with K6's 40 named separately and never pooled |
| **the layer's refinement-row reader shipped a second time, dead, inside `bench/library.py`** — beside the working copy in `bench_shim` that every caller actually uses. It carried an unguarded `import followups` for one string constant, and no `followups.py` ships, so the function raised ImportError on any path reaching it. Nothing reached it. The reference-corpus stubs below it resolved `data/reference/MANIFEST.md`, which is licence-bound and deliberately not redistributed | `bench/library.py` is 620 lines down to 296: only what `bench/mutate.py` imports, which is the one module that imports it. Shipping `followups.py` to satisfy an import nothing calls would have added layer code to support dead code, which is the coupling the shim exists to remove |
| `simulate_pattern`'s `neutron` and `ionic` families imported `run_gate_one_ionic`, which is the layer's and does not ship. The generator only ever asks for the default `neutral`, so the paths were unreachable rather than broken — but they failed as a missing install | they say what they are: not part of this benchmark, with the CL-14 note that prices from two scattering families are not comparable anyway |
| **`tools/run_nolayer.py` could not start.** It imported `isolate` for one eleven-line credential scrubber and `providers` for model access, and neither ships | `scrubbed_env` is carried in `bench_shim` with its provenance, because credential handling is the last thing to reimplement slightly differently in a second place. `providers` is refused by name: model access is not part of this benchmark, and no entrant needs it |
| the repository held **three unguarded imports of modules that do not ship** | zero. The two that remain — `admissibility` in the mutant generator, `providers` in the ablation runner — are guarded and say what is missing |
| **the witness checker graded compositions against the submitter's own text.** Of the six predicates, five read the trusted claim record and `check_stoichiometry` read none — it tested the file against the witness's own `required` field, which the untrusted model that wrote the check also wrote. So a witness could require a composition nobody asserted, any formula the file does not match, and collect a contradiction for it. An earlier repair the same day had stopped it firing on a bare name match when the required side named no formula, which closed the two demonstrated cases but not the class | it reads the claim record like the other five: the claim asserts the compound is its stated composition, so that is the requirement and the contradiction is the file differing from it. Verified — a witness requiring `Ba3ZrSnO9` against the deposited `Ba2ZrSnO6` now returns NOT REPRODUCED where it previously certified. **All six predicates now test against what was claimed** |

## 8h2. The second handover, 29 August

*Six findings handed over from the research repository, two of them consequences
of changes made there that propagated here. All verified against the code as it
stood and fixed.*

| was | now |
|---|---|
| **the scorer could not reproduce the result the documents publish.** K6 was decided by the threshold-free comparison — is the claimed compound the largest phase — while the comparator's own statistic was computed, filed into `k6_rho_says`, and read by nothing. The comparison recovers **7 of 8** at stage two; the published figure is **8 of 8** and comes from rho | the group scores on **rho**, the rule its key was built from. `KBaPrWO6` is why this is not a matter of taste: it crosses the threshold on the NORM with no single term crossing — Rwp 10.75, target 50.42, largest impurity 29.68, giving 0.7892 against 0.776 — and no comparison between two of those three quantities can see it. Both rules are kept and both reported: rho is what the group SCORES, the comparison is what the layer should ASSERT, since it is entailed by the parent and carries no invented number |
| **`tools/build_ceiling.py` would have destroyed the answer key.** It called `build_targets(stage="two")` under a comment reading "the full list, K6 included". That was true while a stage-two pass emitted every group; it now returns **K6 alone**. Regenerating today would have written zero targets for K1-K5 and a ceiling of forty — a fifth of the key, silently. **This is also why the shipped key reads STALE: the generator was out of date, not merely the file** | `build_targets(stage="one") + build_targets(stage="two")`, which gives 95: K1 7, K2 38, K3 2, K4 5, K5 3, K6 40 |
| **phases were joined by printed name** at two sites. The deposit spells one compound's own phase `Ba6Na2Ta2V2O17` where the claim spells it `Ba6Ta2Na2V2O17`; a string compare finds no target, counts the target's own 63.38 per cent as an impurity, and computes 1.3489 where the key says 0.7651. The module already stamps `t["key"] = _key(...)` elsewhere to prevent exactly this | both sites go through the composition key. **Fifth occurrence of this fault class** |
| **the entrant contract's own worked example scored nothing it claimed.** It carried a `follow_up`, which `_declared_stage` reads as stage two, so `build_targets` kept K6 alone and the example produced a K6 block with **no K1 or K2 row** — four lines above text saying "it recovers `K1:MgCuP2O7` and `K2:MgCuP2O7`". A stranger copying the documented shape loses their stage-one score entirely | `follow_up` moved out of the stage-one example, with a paragraph saying why asking for stage two is a pass of its own. Verified: the example now scores against all five stage-one groups |
| **the observations table omitted two of the three terms K6 reads.** `largest_impurity_wt_pct` and `n_phases_reported` are read by name by `_k6_records` and neither was listed, so an entrant following the documentation exactly scored NOT-OBSERVED on **every K6 target** — the whole stage-two pass — with the only escape an undocumented derivation | both documented, with the rule that the three terms must come from one check, and the derivation stated: the largest single impurity is not the total deficit, and where three or more phases are reported the deficit is split, so the target is NOT-OBSERVED rather than guessed |
| **the authority was inverted in four places.** `README.md`, `ENTRANT.md` and `ceiling.md` twice all named `ceiling.json` the authority that wins where a document disagrees. **Nothing reads that file.** The dependency runs the other way: `build_ceiling.py` imports `build_targets`. Four documents nominating a generated artifact as the tie-break over the code that generates it is how a stale digest becomes invisible | `build_targets()` in `bench/score_targets.py` is the authority; `ceiling.json` is its downstream report; disagreements are settled by running the function |

Five smaller contradictions went with them: the defect list claimed "none of the
63 ceiling targets" had been reached, against a pre-exclusion count it declares
wrong two sections earlier and a K6 run recorded one section later; the
specification said a stage-two pass "is scored again" without saying K6 only,
and never said the release is the refinement row rather than a replacement
deposit; its source table omitted `cartograph_decisions.csv`, leaving the
benchmark's only end-to-end measurement invisible in the document that defines
the benchmark; `ENTRANT.md` said no group has a do-nothing line when K6 does and
`report()` prints it; and the entrant bundle described stage two as "a different
structure file and different refinement columns" when it is the columns only.

## 8h3. A claim that was wrong for a month, found by being asked how the critics did it

**"E1 is impossible for everyone, permanently."** `ceiling.md` said that and
`specification.md` said "a source no verifier can be scored against… settled,
not re-argued". The critics flagged 18 compounds under E1. They are not nobody,
so the claim was false on its face and survived because "settled, not
re-argued" is a phrase that stops the next person checking.

What is true: the observed intensities are not in the deposit, and the
**reported Rwp does not stand in for them.** Measured on the 35 compounds
carrying both a flag and an Rwp, the reported Rwp carries some signal and not nearly enough: against the E1 flag it scores an AUC of 0.64, where 0.5 is no information, and the best balanced threshold — Rwp above 9.5 — catches 10 of the 18 flagged compounds while flagging 4 of the 17 unflagged, an accuracy of 0.66 against a base rate of 0.51. The distributions overlap across
nearly their whole range, flagged 3.21 to 26.47 against unflagged 1.94 to
21.14. So E1 is genuinely not reachable from what this benchmark hands a
verifier — which is worth stating with a number rather than as an assertion,
since the assertion is what went wrong here.

What the critics used instead was the **published refinement plots** — whether
the calculated pattern explains the observed one is a judgement made looking at
the curve. The layer's own `refinement_quality` stub already recorded the route,
documented as "implementable only against digitised patterns or new data", so
the project held both the correct statement and the wrong one at the same time.

Both documents now say scope boundary rather than impossibility. **The pattern
worth keeping: an impossibility claim that names no mechanism is a claim nobody
has to check, and this one was contradicted by the very table it was written
about.**

## 8i. Open, and not fixed

**The Ba2ZrSnO6 mutant is unrecoverable, and its label is the opposite of its
file.** Both constructed sets write to `data/mutants/<compound>/<compound>.cif`,
and Ba2ZrSnO6 is in both. The file on disk is the contamination set's H1 —
fully ordered, satisfying the claim, truth `cannot_verify`, hash matching.
`data/mutants_demo.csv` records that same path as M1-001, truth `refuted`, "the
disordered parent of the asserted ordering", under a hash
(`6c7f196a…`) that no file in the repository has. So the demonstration set's
Ba2ZrSnO6 entry points at a file asserting the reverse of its own label. The
recorded hash is what catches it; R7 checks that every row *carries* a hash but
never resolves one. Regenerating the mutant needs the deposit. **The one-file-
per-compound path scheme, adopted on 28 August to close a leak, is what made
the collision possible — the leak fix and this are the same change.**

**Both answer keys were stale against their own inputs, and the generator was
part of why.** `tools/build_ceiling.py` called `build_targets(stage="two")`
under a comment that had stopped being true, so regenerating would have written
K6's 40 and nothing else — the key could not be refreshed without being
destroyed. That is fixed (§8h2), and the generator now produces all 95. What
blocked the rebuild after that was evidence, not code: it needs the deposit.
(Rebuilding `merged_labels.csv` needs more — `results/structure_scan.csv`,
which does not ship — but the two keys do not require that, only the four
label tables already here.)

**That staleness is now closed.** Both keys were rebuilt against the fetched
deposit, and `tools/build_ceiling.py --check` reports `current` for
`ceiling.json` and `cartograph_decisions.csv` at digest `06e03dddc3cb9ecc`.
The rebuild changed no decision: the 40 baseline rows are byte-identical to the
stale key's, 8 flagged, do-nothing 80.0%, and every one of the 95 targets is
unchanged. What it did change was the two things the stale artifacts still
carried from before the ruling above: `cartograph_decisions.csv` had described
the baseline as "not a ceiling target", and `ceiling.json` had
`baseline_comparison.is_target_group` set true. The first now states K6's
framing; the second is false, because that block is the set comparison the
scorer prints beside K6 and not the group — K6 carries its own
`is_ceiling_target` under `groups`, and it is true. So the guarantee the digest
exists to give now holds.

One substantive disagreement inside that staleness is now closed, and it was
never a change of value. `K5:P3` reads 24 in the key and has throughout; the
input file had been edited to 4 against a **tightened definition** of
`mixed_cation_sites`, where the word "site" came to mean a crystallographic
orbit while `Ctx.site_species()` — which implements the quantity — enumerates
structure rows. The proposal was flagged, never adopted, and no scored artifact
ever carried 4. Both now read 24 and the file's correction log records the
reading rather than deleting it. What remains is the digest stamp, not a known
difference in content.

Rebuilding needs more than the deposit. `merged_labels.csv` is one of the four
digest inputs, and `bench/build_labels.py` writes it from
`results/structure_scan.csv` — this project's own scan over the deposited
files, which lands in the gitignored `results/` tree and does not travel with
the benchmark. Every read of it was a `.get` with a default, so building
without it would have written a merged table with `scan_auto_sg`,
`scan_auto_disordered` and `scan_mixed_sites` empty, where the shipped key
carries them on 42 of 43 rows: **a silently different answer key.** The builder
now refuses instead. Closing the staleness therefore needs the deposit *and*
the scan, and until both are present the shipped keys are the only ones there
are.

**The weight-fraction threshold is still invented.** Every such claim carries
`threshold=0.5` stamped INVENTED BY INTAKE; the source states no purity
threshold. It no longer decides K6, but it was not removed, and 64 of 88 checks
in one campaign read it and compared it against weight *percentages* — a
hundredfold error. The threshold-free replacement is the ruling that "the
claimed compound is the principal product" is ENTAILED by the parent, which is
a comparison and carries no invented number; making it operative needs the
claim payload, a checker predicate and a re-intake to move together.

**The conditions figure and table are wrong in most cells** and hardcode their
values, so re-running reproduces the stale output exactly. They need
re-deriving, not re-running.

## 9. Errors made and corrected in the last two days, kept as a pattern

Not a confession list — a map of where this project's mistakes cluster.

| error | class |
|---|---|
| the decision rule inferred impossibility from a sufficiency bound | unsound inference |
| the rival gate admitted an origin-shifted copy, which priced at infinity | missing test |
| witness validation passed on presence rather than contradiction | fail-open |
| a keyword classifier routed refutations to the wrong predicate | inference from wording |
| the file lookup joined by name, missing 2 of 42 deposited pairs | **join by name** |
| the K2 label join joined by name, missing 2 of 43 determinations | **join by name, again, two days later** |
| the scorebook read raw check status, crediting downgraded refutations | bypassing a rule |
| the scorebook scored every flag target as expecting True | wrong comparison |
| K6 printed one percentage worse than doing nothing | base-rate artifact |
| the prompt's literal braces broke `str.format` | would have crashed the campaign |
| **the K6 answer key reimplemented a validated statistic and got `w_alt` wrong** | **reimplementation instead of reuse** |
| `run_chain` would have overwritten banked elicitations | destructive default |
| three "independent" target groups read one compound-level bit | **a measurement counted more than once** |
| answer keys claimed a writer that did not exist | **provenance asserted, not implemented** |

**A third cluster, added 28 August.** The K6 answer key was generated by
writing out CARTOGRAPH's statistic again rather than calling `rho_alab`, which
already existed ten lines away and reproduces the published result exactly. The
rewrite used `(100 - w_target)` for the third term instead of the largest
single impurity fraction — a different statistic, systematically larger, which
flagged 9 compounds where the published result flags 8. It was caught because
two documents in the same folder cited two generations of one computation and
disagreed. **A validated implementation existing and not being called is now a
named failure mode here.**

**Two clusters worth naming.** Joining by printed name has now failed twice in
three days on the same data. And three separate metrics — K7, K6's aggregate,
and the twin control — were each nearly reported as results when they were
measuring a base rate.

## 10. Nothing here is rowed

No number in this repository has a register row. By house rule none may appear
in a public artifact. That is a publication gate, not a development gate, and
it is not currently blocking anything.

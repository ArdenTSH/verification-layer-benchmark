# Running this benchmark on your own verifier

*The submission contract. 28 August 2026. You do not need our layer, our
models, our primitives, or our code. You need to produce one JSONL file.*

---

## 1. What is being asked

*Two words in this document are ours rather than the field's. **The layer** is the verification system this benchmark was built to evaluate — Aletheia v0, in a separate repository, one entrant among others. **An arm** is one model configuration run through it, so "our own arms" means our runs and never yours. The README's term table has the rest.*

You are given, per compound, the evidence an expert panel had: a deposited
crystal structure file, the refinement the robot itself reported, and the claim
that was made. **You are told nothing about what any expert concluded.**

The question is whether your verifier independently arrives at findings the
critique or the Correction already published. The external baseline is not one
of them: it is reported as a comparison, separately, and nothing you submit is
scored on it (§4).

**A finding you produce that no expert asserted is a false alarm of your
instrument, not a discovery.** The denominators are theirs, not ours.

## 2. What you receive

```
data/entrant/instances.jsonl        40 instances, one per compound
data/entrant/follow_up_menu.json    the modalities you may request
data/cifs/Automated_Refinement_Results/<compound>/<compound>.cif
```

One instance per compound, and **the claim is not decomposed**:

```json
{"instance_id": "alab:MgCuP2O7",
 "compound": "MgCuP2O7",
 "claim": "MgCuP2O7 was synthesised as a new inorganic material, with the
           structure reported in the deposited file",
 "claim_record": {
   "compound": "MgCuP2O7",
   "claimed_space_group": "P-1 (2)",
   "claimed_structure": "MgCuP2O7",
   "asserts": ["the compound was synthesised",
               "the compound is a new inorganic material",
               "the compound has the claimed structure"],
   "does_not_assert": ["any purity or weight-fraction threshold - the paper
                        states none, so a refutation of one does not refute
                        this claim"]},
 "evidence_stage_one": {
   "structure_file": "data/cifs/.../MgCuP2O7.cif",
   "sha256": "7a57a0...",
   "refinement": {"rwp_pct": 9.43,
                  "phases": [{"formula": "MgCuP2O7",
                              "formula_core": "MgCuP2O7",
                              "wt_pct": 100.0}]}},
 "evidence_stage_two": {"available": false, "...": "see §6"},
 "reference_corpus": {"available": false, "...": "see below"},
 "budget_counts_band": [1e5, 1e7]}
```

This is the compound the worked example in §3 refutes, so one instance can be
followed from what you are handed to what you return.

**Match phases on `formula_core`, never on `formula`.** Every phase carries
both. `formula` is the label exactly as the deposit prints it, annotations
included — `Ba6Ta2Na2V2O17 (12H-type)`, `Zn3Ni4(SbO6)2_ICSD109468` — because the
annotation is information and discarding it would be lossy. `formula_core` is
the part that parses as a composition, and it is what a phase comparison should
read.

This is not a style note. The deposit spells one compound's own phase
`Ba6Na2Ta2V2O17` where the claim spells it `Ba6Ta2Na2V2O17`: the same
composition with two elements transposed. A verifier comparing printed names
finds no target phase in that compound's own refinement, and then reports the
target's own 63.38 per cent as the largest *impurity* — which inverts the
quantity K6 reads. That trap has caught a model twice. Compare compositions,
not strings; `pymatgen.core.Composition(x).reduced_formula` is what the
scorebook itself joins on, and it is why `Ba6Na2Ta2V2O17` and `Ba6Ta2Na2V2O17`
score as one compound here.

**Split the claim however you like, or not at all.** An earlier version of this
bundle shipped 160 instances — 40 compounds times our own four decomposition
families — which forced you into our taxonomy. Decomposing a claim into
checkable parts is your verifier's job and one of the things that differs
between verifiers. You are scored on the findings you reach, not on how you
carved the claim up.

**The full claim record is given**, including what the claim does *not* assert,
because §3's witness contract is judged against that record and you should be
able to see the standard you are held to.

**Stage one is everything the panel had on day one**: the deposited file and
the *automated* refinement — the robot's own Rwp and phase fractions.

**The reference corpus is not shipped.** Novelty is judged against a
crystallographic database. The critique used the **ICSD**; an open database has
different coverage and recovers none of its novelty flags. Bring your own and
say which — an ICSD result is comparable to the critique's, an open-database
result is not, and the scorebook will not pretend otherwise.

## 3. What you return

One JSONL file, one line per compound you attempted, and **one `findings`
entry per evidence class you examined** — including classes where you found
nothing. A class you do not list counts as never attempted, so declaring what
you looked at is how coverage is measured.

```json
{"instance_id": "alab:MgCuP2O7",
 "verdict": "refuted",
 "findings": [
   {"evidence_class": "deposited-file",
    "verdict": "refuted",
    "witness": {"where": "MgCuP2O7.cif : _atom_site loop, the site at
                          (0.72705, 0.15151, 0.81687)",
                "observed": "that site carries {'Mg': 0.5, 'Cu': 0.5}",
                "required": "distinct, fully occupied sites for Mg and Cu"}},
   {"evidence_class": "reference-database", "verdict": "cannot_verify"},
   {"evidence_class": "refinement-fit", "verdict": "cannot_verify"}],
 "observations": {"space_group_number": 2,
                  "space_group_symbol": "P-1",
                  "mixed_cation_sites": 4,
                  "fit_residual_rwp": 9.43,
                  "target_weight_fraction_pct": 100.0,
                  "largest_impurity_wt_pct": 0.0,
                  "n_phases_reported": 1}}
```

**No `follow_up` here, and that is deliberate.** Naming the stage-two modality
is what earns stage two, and a stage-two pass scores K6 **and only K6** (§6).
So a line carrying `follow_up` is not a stage-one submission at all: add it to
this example and the scorebook returns a K6 block with no K1 or K2 row in it.
Ask for stage two when you mean to, in a pass of its own.

Pretty-printed here; on the wire it is one line. It is not a mock-up. Its
witness was run through `tools/check_witness.py` against the deposited
`MgCuP2O7.cif` with the claim record the scorer builds, and the checker returns
**WITNESS REPRODUCED**, decided by the occupancy predicate: the file puts Mg
0.5 and Cu 0.5 on one shared site at (0.72705, 0.15151, 0.81687), and a
cation-ordering claim requires those species on distinct fully occupied sites.
Scored, it recovers `K1:MgCuP2O7` and `K2:MgCuP2O7`.

`space_group_number` is `2`, not the `1` the file's `P 1` header states,
because the scored quantity is the symmetry of the deposited **structure** and
that header is an expansion convention rather than a determination. See §7a.

### `findings` — one entry per evidence class you examined

**This is the preferred form and the one the rest of this document describes.**
A `findings` entry is an object read for exactly three keys:

| key | required | if absent |
|---|---|---|
| `evidence_class` | yes, in practice | defaults to `""`, and a `refuted` entry with no class **establishes nothing** — see below |
| `verdict` | no | inherits the line's top-level `verdict` |
| `witness` | on a refuting entry | inherits the line's top-level `witness`; a refuting entry with neither is not counted |

Nothing else in the entry is read. Entries that are not JSON objects are
skipped, and if `findings` is absent, empty, or every entry is skipped, the
scorer falls back to the flat form below.

`observations` and `follow_up` stay at the **top level of the line**, one set
per compound. They are not read from inside a `findings` entry.

The line still needs a top-level `verdict` from §3's grammar even when every
entry carries its own: a line whose top-level verdict is missing, unrecognised,
or `verified` is rejected before `findings` is read.

**Each refuting entry is adjudicated under its own class**, so the witness that
is credited for `deposited-file` is refused for `reference-database` — it is
the same file contradiction, and a file contradiction does not establish
"already known". Declaring the extra class does not buy the extra finding.

A refuting entry with no witness — neither its own nor the line's — is not
counted, with the reason `refutation with no witness`.

**Two more ways to lose a finding you actually made:**

- **A refuting entry with no `evidence_class` is not counted**, with the reason
  `refutation declares no evidence class; it cannot be matched to a finding, so
  it establishes nothing`. It still counts as coverage of the `deposited-file`
  family, so the compound's K1 target scores MISSED rather than NOT-ATTEMPTED.
  Both reasons above are printed, with counts, before the scorebook.
- **Only the first entry per internal family survives.** The three classes map
  to three distinct families, but an unrecognised class name — and an entry
  with no `evidence_class` — both map to the same family as `deposited-file`.
  Put either ahead of your real `deposited-file` entry and that entry is
  discarded: the refutation never happens, no reason is printed, and the K1
  target scores MISSED. The only trace is an `unrecognised evidence class`
  note in the adapted `children_rebuilt_submission.csv`. Spell the three class
  names exactly.

### the flat form — still accepted, not preferred

The older shape is translated into `findings` and keeps working:

```json
{"instance_id": "alab:MgCuP2O7",
 "verdict": "refuted",
 "refuted_on": ["deposited-file"],
 "examined": ["reference-database", "refinement-fit"],
 "witness": {"where": "...", "observed": "...", "required": "..."}}
```

`refuted_on` and `examined` each accept a bare string or a list. Every class in
`refuted_on` becomes a refuting entry carrying the single top-level `witness`;
every class in `examined` that is not already in `refuted_on` becomes a
`cannot_verify` entry with no witness. A line declaring neither becomes one
entry with no evidence class, which is the losing case above.

What it cannot express is **a separate witness per class**: one line carries
one `witness`, so a verifier refuting on both the file and the database can
justify only one of them, and the other is adjudicated against a witness that
was never written for it. Prefer `findings`.

### `verdict` — one of

| | |
|---|---|
| `refuted` | the evidence shows the claim is false. **Requires a witness and an evidence class** |
| `cannot_verify` | you could not refute it |
| `inapplicable` | you could not run at all |

**There is no affirming verdict.** Deciding *for* a claim here would need the
measured diffraction patterns, which were never deposited. A submission
containing `verified` is rejected.

### `evidence_class` — what kind of evidence a finding rests on

The value of `evidence_class` in a `findings` entry, and of `refuted_on` /
`examined` in the flat form. Required on every refutation. Exactly one of these
three strings per entry:

| class | means |
|---|---|
| `deposited-file` | the structure file contradicts the claim |
| `reference-database` | the compound is present in a reference corpus |
| `refinement-fit` | the reported fit or phase fractions contradict the claim |

**This is benchmark vocabulary, not our decomposition.** It is the one thing
the scorer needs from you, because a file contradiction does not establish
"already known", and a database match does not establish "the file differs".
Those are scored as separate findings and cannot be satisfied by one another.

A refutation that declares no class establishes nothing and is not counted.

### `witness` — required on every refutation, and it is checked

Three fields: **where** you looked, **what you observed**, **what the claim
required instead**.

A refutation counts only when an independent checker establishes a
**contradiction** between the deposited file and the claim record. The checker
is stdlib-only and shares no code with the layer, so belief in a refutation
never rests on anyone's say-so. It is the same checker our own arms are held
to, called through the same function.

**Write `observed` as values the checker can find in the file.** This is the
part people get wrong, and we got it wrong ourselves while testing:

```
observed: "that site carries {'Mg': 0.5, 'Cu': 0.5}"   verifies
observed: "one site carries Mg 0.5 / Cu 0.5"           does NOT verify
```

Both sentences say the same thing to a human. The first states an occupancy
mapping the checker can locate and confirm against the CIF; the second is
prose about it. **Presence of the observed values is necessary and never
sufficient** — the checker then tests whether they contradict what the claim
required.

Both were run against `MgCuP2O7.cif`. The first returns WITNESS REPRODUCED.
The second returns WITNESS NOT REPRODUCED: no predicate can read an occupancy
out of it, so the occupancy predicate does not apply, and the verdict falls
through to the symmetry-tag predicate, which refuses it.

Naming the site's fractional coordinates in `where` or `observed` narrows the
search to that site. Omit them and the checker will accept any site in the file
carrying the witnessed occupancies.

The requirement is read from **our** claim record, not from your `required`
text, because your text is written by the same system whose refutation is
being judged. That record is in your instance, so nothing is hidden.

**A refutation whose witness does not establish a contradiction is not counted
as a refutation**, and the target it would have recovered scores as MISSED —
the same fail-closed rule our arms are held to. The count and reasons are
printed.

Firing unwitnessed refutations at every compound scores worse than abstaining
— **with one declared exception we have not yet closed.** A witness that copies
the `P 1` symmetry line out of the deposited file certifies on almost every
compound, because that line is a formatting convention rather than a finding.
See §7a. Do not read a high flag-target score as evidence of work until that
check has been run.

### `observations` — the values you measured

Attach them **whether or not you refute**. Most targets in this benchmark are
values, not flags.

**Use these exact keys.** They are read by name; a value under a name of your
own is kept and not read.

| key | type | meaning |
|---|---|---|
| `space_group_number` | int | International Tables number of the **deposited structure**, determined from its coordinates. 38 of the 40 files carry a `P 1` header; copying that `1` matches only 4 of K2's 38 targets and scores MISSED on the other 34 |
| `space_group_symbol` | str | the same determination as a symbol — **either form scores** |
| `cubic_lattice_parameter_a` | float | cubic or **pseudo-cubic** parameter, Å. State your conversion |
| `mixed_cation_sites` | int | sites carrying more than one cation species |
| `target_weight_fraction_pct` | float | weight fraction reported for the target phase. **K6 term** |
| `fit_residual_rwp` | float | reported fit residual, per cent. **K6 term** |
| `largest_impurity_wt_pct` | float | the LARGEST SINGLE impurity phase fraction. **K6 term** |
| `n_phases_reported` | int | how many phases the refinement row reports |

**The three K6 terms must come from one check.** K6 is scored by computing the
baseline's statistic from your own recorded numbers, and the statistic is a norm
over all three — so a target fraction from one check and an impurity from
another produces a number neither computed, and is rejected. Record all three
together, on the same line.

**`largest_impurity_wt_pct` is not the total deficit.** It is the largest single
impurity, and `100 - target` is the whole remainder; the two differ whenever
three or more phases are reported, because the deficit is then split between
them. Where you omit it, the scorer derives it **only where arithmetic
determines it** — target at 100 per cent, or one phase reported, both giving
zero; or exactly two phases, where the single impurity is the remainder. With
three or more phases and no recorded value, the target is NOT-OBSERVED rather
than guessed.

Extra keys are kept. Record every one you can compute, **not only those your
verdict is about**: a verifier that has loaded the structure can report its
symmetry at no extra cost.

### `follow_up` — optional, and the only route to stage two

```json
{"modality": "<a value from follow_up_menu.json>",
 "separates": "which competing explanation it would rule out",
 "observation": "what you would look at in the new data"}
```

Gated for **well-formedness only** — name a modality, name what it separates,
state what would be observed. **Never for plausibility.** A modality outside
the menu is allowed and recorded as an off-menu proposal.

The menu deliberately does not say which modalities we can supply or how
discriminating each is. Choose what would settle the question, not what sounds
obtainable.

## 4. How you are scored

**Per target, never as one number.** Group denominators are never pooled.

**Five groups, 55 targets.** The counts below are what `build_targets()` in
`bench/score_targets.py` constructs, which is what the scorer runs and is the
authority. `data/labels/ceiling.json` is a generated report of the same list —
convenient to read, but nothing reads it back, so it cannot settle a
disagreement with the code that writes it.

| group | finding | source | targets |
|---|---|---|---|
| K1 | the deposited file differs from the claim | critique, Table I (E2) | 7 |
| K2 | the symmetry of each deposited file | critique, Table III | 38 |
| K3 | the product was already known | critique, Table I (E4) | 2 |
| K4 | the cubic lattice parameter from each A-Lab CIF | critique, Table II | 5 |
| K5 | per-compound statements in the critique's prose | critique, §IV | 3 |

### K6, and what it actually tests

**K6 is not a reproduction of another automated system. It is the end-to-end
test of the two-stage protocol**, and it is the only part of this benchmark
that scores the thing the whole design exists for: whether a verifier that
cannot decide from the evidence it holds can *say what would decide it*.

The sequence is the target. You work on stage-one evidence. You abstain. You
**name** the follow-up analysis that would settle the question. You are granted
that analysis. You are then scored on whether you reach the external baseline's
decision. CARTOGRAPH's pass/flag is the external key for that last step — not a
rival score to beat, and not a finding to recover.

**It is reachable, and it has been reached.** An earlier version of this
document said K6 was out of the benchmark because the route to it was broken:
the scorebook read the stage from the adapted ledger's *filename*, which the
adapter always wrote as `children_rebuilt_submission.csv`, so no submission
could ever be scored at stage two. That was a defect, not a design. It is
fixed — the stage is now read from what your submission declares (§6) — and the
protocol has since run end to end and been scored.

| K6 | source | targets |
|---|---|---|
| the external baseline's decision per compound | CARTOGRAPH, Appendix I | 40 |

**K6 is counted apart from the 55 and never pooled with them.** Its inputs are
the manual refinement columns; the five groups above are documentary statements
about the automated deposit. A count from one is never quoted against the
other's denominator.

The scorer also prints an `EXTERNAL BASELINE` block: a set comparison of what
both sides flag and what only one does, with the do-nothing line beside it —
a verifier flagging nothing agrees on 32 of 40. That block is context. K6, when
your submission earns stage two, is the score.

| outcome | meaning |
|---|---|
| `RECOVERED` | your value matches at the stated tolerance; or you flagged what they flagged, with evidence of the matching class |
| `MISSED` | you reached a different answer |
| `NOT-OBSERVED` | you attempted it but recorded no observation of that quantity |
| `UNVALIDATED` | you refuted on this target's own evidence class and the independent checker cannot read that class. **Reached, not validated. Never scored as a miss** |
| `NOT-ATTEMPTED` | you did not submit for that compound, or did not list that evidence class |

**`UNVALIDATED` is currently unreachable from a submission**, and that is the
harder rule, not the softer one. The standalone checker now reads the deposited
file, the pinned reference snapshot and the refinement workbook, so all three
evidence classes are adjudicable and none of them lands in the "cannot read
that class" escape. A refutation is therefore either credited or **not counted
at all**, and the target it would have recovered scores MISSED. The outcome
stays documented because the scorer still emits it, and because the escape
returns if a class ever loses its predicate.

### The denominator is the benchmark's, not yours

Every group is scored against **its full target count**, and coverage is
printed in the same block:

```
K1  the deposited file differs from the claim (E2)
    7 targets in the benchmark | recovered 5 | missed 1 | not observed 0 | not attempted 1
    recovered 5 of 7 (71% of the benchmark's targets)
    attempted 6 of 7 (86%) - two submissions are comparable only at equal coverage
```

Skipping does not shrink your denominator. Answering the five easy compounds
and omitting the sixth reports 5 of 7 with 71% coverage, not "5 of 5".

**Two submissions are comparable only at equal coverage.** That line is printed
every time so nobody has to remember it.

### K2 is reported as two numbers that are never summed

K2 has **38 targets**. On 35 of them the critique's determination **equals the
claimed space group**. A verifier that copied the claim it was handed, never
opening the file, would score those 35 — value targets carry no witness
requirement, so nothing else catches it.

The 35 are not discarded: recovering an agreement is still a reproduction. But
only the 3 rows where the determination **differs** from the claim distinguish
a verifier that read the file from one that echoed it, so the two are reported
apart:

```
where the determination equals the claim (echo-level)
  x of 35   (attempted a)
where it DIFFERS from the claim (requires the file)
  y of 3    (attempted b)
these two are never summed: a verifier echoing the claimed space group
scores the first and nothing in the second.
```

35 + 3 = 38, and **no combined figure is printed for K2** — printing one would
reinstate the number the split exists to remove.

Table III makes 43 determinations and 38 are targets. Five rows are not.
`Mg3NiO4`, `Y3In2Ga3O12` and `Zn2Cr3FeO8` are outside the evaluation
population of 40 — the first two were made offline and the Correction removed
the third — so they carry no instance and no verifier can reach them.
`MgTi4(PO4)6` and `FeSb3Pb4O13` are excluded because two independent symmetry
determinations disagree there and the benchmark declines to rule which is
right; a target nobody may be scored against is not a target.

## 5. What is measured that is not accuracy

**False alarms.** Every flag on a compound no expert flagged is counted and
reported beside your recoveries. No aggregate trades one against the other.
The `EXTERNAL BASELINE` block names them individually, under `only we flag`.

**The do-nothing line.** Where a group's targets include compounds expected *not* to be flagged, the score a verifier gets by flagging nothing is printed beside yours, and no single figure is printed for that group. **K6 is in that shape**: 32 of its 40 compounds are ones the baseline passes, so a verifier flagging nothing agrees on 32 of 40 — 80 per cent — and `report()` prints that line inside K6's own block. K1 and K3 are not: they carry only compounds the critique flagged, so flagging nothing scores zero on them and the line does not appear. What appears there instead is your false-alarm count, named and never netted against your recoveries.

The 80 per cent figure this section used to quote — 32 of 40 — is the
do-nothing agreement with the **external baseline**, which is not a group of
this benchmark (§4). The scorer still prints it in the `EXTERNAL BASELINE`
block, as agreement, never as a score.

## 6. Stage two

Abstain, and name `re-refinement-expanded-phase-set` in `follow_up`, and you
receive the expert re-refinement and are scored again, **separately**.

**What you receive is the refinement row, not a replacement deposit.** Stage
two hands over the expert's refinement columns for the same specimen. It does
not swap the structure file underneath you. That distinction was learned the
expensive way: substituting the expert's file meant a check written against one
file was executed against another, undeclared, and 41 of 42 deposits differ in
lattice parameter beyond the tolerance that parameter is scored at. The
deposited file is the object under audit; re-analysing a pattern does not
change what was deposited.

**Stage-two evidence is contaminated by construction** and every stage-two row
says so: it was produced by people who already knew how the dispute came out.
It is never pooled with stage one. That is the declared cost of a retrospective
study, and it means the steering is *simulated* — the experiment was not
performed on request, its result was looked up.

**A stage-two pass scores K6, and only K6.** K1, K2, K4 and K5 are documentary
statements about the *automated* refinement and the deposited file; their
targets are defined at stage one and are read from your stage-one pass whatever
else you do. K6 is the one group whose inputs are the manual columns — for
`Ba2ZrSnO6` the target phase reads 91.12 per cent at stage one and 22.0 at
stage two, so no day-one verifier can compute that decision, ours included.

**How the stage is decided.** From your submission, never from a filename. A
pass is stage two when its rows name `re-refinement-expanded-phase-set` in
`follow_up`, which is the modality stage two supplies. `bench/score_targets.py`
also takes `--stage one|two` for a harness that already knows. It used to read
the stage from the adapted ledger's filename, which the adapter always wrote as
`children_rebuilt_submission.csv` — so no submission could reach stage two, and
anyone who renamed a file could choose which group they were scored on. Both
halves of that are fixed.

A verifier that abstains and asks for more counting time receives nothing.
Stage two supplies a re-refinement, not a longer measurement.

## 7. Rules

**One submission per compound.** A verifier that sees its own result and
resubmits is measuring something else.

**No expert labels in your inputs.** The answer keys are in this repository, as
they are in every benchmark — you hide them from your model, not from
yourself. If your system was given the critique, the Correction, or any flag
list, say so. The result is still reportable; it is a different kind of result.

**Contamination is not currently controlled.** The critique is open-access and
almost certainly in the training data of any large model. The standing partial
bound is your **false-alarm rate on the 36 compounds the Correction
confirmed**. Treat any recovery claim as bounded by that.

## 7a. Known attacks on this scorer, and their status

*Declared 28 August 2026. Found by attacking the published contract from
outside it, and executed end to end rather than argued.*

This benchmark scores a scientific question — can a verifier recover findings
an expert panel published — and its scorer was built for verifiers making an
honest attempt. It is **not hardened against a submitter trying to defeat it**,
and we would rather say so than imply a robustness we have not built. Where an
attack is open, the honest reading of a high score is that it *may* have been
obtained this way, and we check.

| attack | status |
|---|---|
| **Class stamping.** Declare all three evidence classes, pass the cheapest test, collect all three findings. The witness was adjudicated once, under the first declared class, and that single result was stamped onto every class. | **FIXED.** Adjudicated once per declared class. |
| **Cross-class credit.** The standalone checker read only the deposited file, and tried every predicate whatever class it was handed, so a file contradiction satisfied a `reference-database` refutation. | **FIXED.** Each declared class is adjudicated under its own family, and the file witness that is credited for `deposited-file` is refused for `reference-database`. Verified by running both on one submission. **K3 is now reachable through a submission**: the checker holds a pinned reference snapshot, so a witness citing an entry identifier the snapshot contains is credited. It was unreachable when that predicate did not exist; that is no longer the state. |
| **The `P 1` attack.** 38 of the 40 deposited files record their symmetry as `P 1` — a formatting convention of the software that wrote them, not a finding. A witness quoting that line against any claimed group is a true statement about the text, and the checker certifies it. Executed: **39 of 40 witnesses certified, K1 6 of 8** — equal to our own best arm — from copying one line per file. **NARROWED 29 August 2026**, not closed: the entrant path passed the checker only the compound, so the requirement was read from the submitter's own `required` text. It now passes the claimed space group from the label table, so the contradiction is tested against what was claimed rather than against what the submitter wrote. The underlying word-order defect below is still open. |
| **The enumeration attack.** Value targets score any-of over every value submitted, and nothing dedupes lines. Enumerating all 230 space groups and a fine lattice grid scores most value targets, including the echo split. | **OPEN, declared.** The fix is one submission line per compound, enforced, and rejecting a submission that returns more values for a quantity than a verifier could have measured. |

**Requirements come from the claim record, not from your `required` field.**
All six predicates now read the claim record and test the deposited file against
what the *claim* asserted. This was not always true, and the two places it was
not are the two attacks above. `check_stoichiometry` was the last: it graded
compositions against your own `required` text, so requiring any formula the file
does not match earned a contradiction — closed 29 August, verified against a
witness requiring `Ba3ZrSnO9` of a file the claim says is `Ba2ZrSnO6`, which
now returns NOT REPRODUCED. Writing a requirement nobody asserted no longer
earns anything.

**What we do about the open ones, until they are closed.** Every reported result
carries a manual check that the score was not obtained this way. For our own
arms that check has been run: of 77 refuting checks, **7 mention the `P 1`
convention and every one recomputes the group from the atomic coordinates and
names the header as an artefact**; of the 37 witnesses the checker reproduced,
the only one resting on a `P 1` header is on a compound carrying no expert
flag, so it is a false alarm rather than a recovery. **No K1 recovery by any of
our arms depends on this attack** — each rests on `occupancy`, `stoichiometry`,
or a header carrying a genuine space group.

If you submit, we will run the same check on your submission and report it
beside your score.

## 8. Scoring your submission

```
.venv/bin/python tools/score_submission.py <your.jsonl>
.venv/bin/python tools/score_submission.py <your.jsonl> --targets
```

It validates the schema, rejects `verified`, runs the witness contradiction
test on every refutation, and prints the per-target scorebook. It reads nothing
from our ledger format: the same scorebook that scores our own arms, fed
through a submission adapter, so the two cannot drift apart.

**It writes into this repository, unconditionally.** Scoring is not read-only:
the adapter writes `children_rebuilt_submission.csv` and
`ledger_rebuilt_submission.csv` into `results/submissions/<stem>/`, where
`<stem>` is your submission's filename without its extension and the path is
relative to the repository root, wherever your file lives. There is no flag to
redirect it and no prompt. Two submissions with the same filename stem
overwrite each other's adapted ledger. **This is a known wart, not a feature**:
the directory is a scoring intermediate, it is what `--targets` and the
scorebook read, and nothing else in the benchmark consumes it. Name your files
distinctly, and delete the directory when you are done with it.

To regenerate the instance bundle: `--emit-instances`. That one writes to
`data/entrant/`.

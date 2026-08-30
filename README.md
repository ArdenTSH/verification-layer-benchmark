# verification-layer-benchmark

`benchmark-0` · 29 August 2026 · the version the paper cites

**Does a verifier, given only the evidence an expert panel had, independently
reach the findings that panel published — and when it cannot, can it say what
would settle the question?**

That is the whole question, and it has two halves. The benchmark hands you a
scientific claim and the file deposited to support it, and scores whether you
recover findings experts already published about that same evidence, without
being told what they found. Then it asks the harder thing: abstain, **name** the
analysis that would decide it, and be scored on whether you reach the right
answer once you are granted that analysis.

One consequence governs everything else: **a finding you produce that no expert
asserted is a false alarm of your instrument, not a discovery.** The
denominators belong to the expert record, not to you. False alarms are printed
beside your recoveries and never netted against them.

The benchmark never adjudicates chemistry. Every target is a documentary fact
about what a published source says.

### One rule set, one version

Everything before 29 August 2026 was **beta** — instrument development, not
measurement. Not void and not wasted; it is the reason there is anything to
release. But the scoring moved underneath the numbers, three times in one day
at the worst of it, and a figure quoted in the morning did not mean what the
same figure meant that evening. You cannot tell an instrument's readings from
its faults in that state.

`benchmark-0` is the line. One rule set, one version, stamped into every
scorebook this repository prints, so a score can always be read back to the
rules that produced it. A convention change is a new tag and a new version,
with results rebuilt rather than reinterpreted. Scores produced under a retired route are not quoted: the route measured
something other than what its name said, whatever the arithmetic did.

The verifier this was built to evaluate is **Aletheia v0**, in a separate
repository. It is one entrant among others, and it pins this benchmark by
version rather than the other way round.

---

## The words this repository uses

Six house terms, because they appear throughout the documents and two of them
are ours rather than the field's.

| term | meaning |
|---|---|
| **the ceiling** | the target list — every finding a verifier can be scored against, and nothing else. `bench/score_targets.py` builds it; `docs/ceiling.md` explains it |
| **a target** | one scoreable item: a compound, a quantity, and the value an expert published for it. 55 at stage one, plus K6's 40 |
| **stage one / stage two** | stage one is the deposit as it stood in 2023 — the robot's structure file and its automated refinement. Stage two is the expert re-refinement of the same pattern, released as **columns only**, and only to a verifier that asked for it by name |
| **a witness** | the justification attached to a refutation: where you looked, what you observed, what the claim required instead. Checked independently, and a refutation without one is not counted |
| **the layer** | the verification system this benchmark was built to evaluate — **Aletheia v0**, in a separate repository. It is one entrant among others and holds no privileged position here. Where a document says "the layer", it means that system and not this benchmark |
| **an arm** | one model configuration run through the layer — `opus5`, `sonnet5` and so on. Our own results are reported per arm, and "our arms" throughout these documents means those runs, never yours |

---

## Why this episode

In November 2023 an autonomous laboratory reported synthesising 41 new
inorganic compounds. In 2024 an independent group of crystallographers
published a claim-by-claim critique of the evidence. In January 2026 the
original authors published an Author Correction re-examining their own claims.

| source | what it contributes |
|---|---|
| Szymanski et al., *Nature* **624**, 86 (2023) | the claims, and the deposited structure files |
| Leeman et al., *PRX Energy* **3**, 011002 (2024), open access | per-claim findings — the answer key for most groups |
| Author Correction, *Nature* (January 2026) | per-compound verdicts |

Three properties make it usable as a benchmark. Both sides published per-claim
reasoning, so the findings are specific rather than a verdict on the paper as a
whole. The evidence is public, so a verifier reads what the experts read. And
the two expert panels agree far less than you would expect, which is why the
benchmark scores each source separately and never pools them.

---

## Quickstart

**First, fetch the evidence.** The deposited structure files and the refinement
workbook are the 2023 paper's supplementary material. They are someone else's
data and are not redistributed here, so the benchmark ships everything *except*
them.

Fetch them before running anything. `bench/reproduce_benchmark.py` does **not**
stop when they are absent: it runs, and the checks that read the deposit fail —
R5 reports five `FileNotFoundError`s and R6 errors outright. Those failures mean
the deposit has not been fetched, not that the benchmark is broken. The script
exits 0 either way, so read its output rather than its exit code.

| what | where |
|---|---|
| the deposit — structure files and `Refinement-Table.xlsx` | Supplementary Data 2 of Szymanski et al., *Nature* **624**, 86 (2023), [`10.1038/s41586-023-06734-w`](https://doi.org/10.1038/s41586-023-06734-w) — [direct ZIP](https://media.springernature.com/original/springer-static/esm/art%3A10.1038%2Fs41586-023-06734-w/MediaObjects/41586_2023_6734_MOESM3_ESM.zip) |
| the critique, if you want to read the findings yourself | Leeman et al., *PRX Energy* **3**, 011002 (2024), open access — [`10.1103/PRXEnergy.3.011002`](https://doi.org/10.1103/PRXEnergy.3.011002), or the [NSF PAR copy](https://par.nsf.gov/servlets/purl/10532478) the label tables were transcribed from |
| a reference corpus for K3 | your choice. The critique used the **ICSD**, which is subscription-only ([FIZ Karlsruhe](https://icsd.products.fiz-karlsruhe.de/)); the open alternative is the [Crystallography Open Database](http://www.crystallography.net/). They give different answers and the scorer makes you say which you used — see [K3 needs an ICSD licence](#k3-needs-an-icsd-licence) |

Unzip the deposit so these paths exist, which is the layout the archive already
has:

```
data/cifs/Automated_Refinement_Results/<compound>/<compound>.cif
data/cifs/Refinement-Table.xlsx
```

`.gitignore` covers `data/cifs/`, so the deposit can never be committed back by
accident.

```bash
python -m venv .venv && .venv/bin/pip install pymatgen numpy pandas openpyxl scipy

# 1. Check the deposit is the one the answer keys were built against.
.venv/bin/python bench/reproduce_benchmark.py

# 2. Read your instances.
cat data/entrant/instances.jsonl        # 40 lines, one per compound

# 3. Run your verifier, write one JSONL line per compound, then:
.venv/bin/python tools/score_submission.py my_submission.jsonl
```

You need none of our code to produce a submission — only to score one.

---

## What you are scored on

Five groups. **`build_targets()` in `bench/score_targets.py` is the authority** —
it constructs the target list from the label tables, and it is what the scorer
actually runs. `data/labels/ceiling.json` is its generated report, written by
`tools/build_ceiling.py`, which imports that function. Nothing reads the key
back. So if this table, that file and the code ever disagree, settle it by
running `build_targets`, not by trusting the artifact furthest downstream.

| group | finding | source | targets | shape |
|---|---|---|---|---|
| **K1** | the deposited file differs from the claimed structure | critique, Table I (E2) | 7 | flag |
| **K2** | the symmetry of each deposited file | critique, Table III | 38 | value |
| **K3** | the product was already known | critique, Table I (E4) | 2 | flag |
| **K4** | the cubic lattice parameter from each deposited file | critique, Table II | 5 | value |
| **K5** | per-compound structural statements in the prose | critique, §IV | 3 | value |

**55 targets.** Group denominators are never pooled and the scorer refuses to
print a single figure across them — the groups answer different questions
against different expert denominators.

Two rules make a number mean something. **The denominator is the benchmark's:**
skipping a hard compound does not shrink it, and two submissions are comparable
only at equal coverage. **Flag targets require evidence of the matching kind:**
a contradiction in the file does not establish "already known", and a database
match does not establish "the file differs".

K2 is reported as two numbers that are never summed — the rows where the
critique's determination equals the claimed group, and the rows where it
differs. Only the second distinguishes a verifier that opened the file from one
that copied the claim it was handed.

### And a sixth group that scores something else entirely

The five above ask whether you recover a finding. **K6 asks whether you can say
what would settle a question you cannot answer** — the **end-to-end test of the
two-stage protocol**, and the group this benchmark was really built for. The
external key comes from another automated system, but reproducing that system
is not what is being scored.

| group | finding | source | targets | shape |
|---|---|---|---|---|
| **K6** | the external baseline's decision per compound | CARTOGRAPH, Appendix I | 40 | flag |

The sequence is the target, not the number at the end. You work on the day-one
evidence. You abstain. You **name** the follow-up analysis that would decide
it — `re-refinement-expanded-phase-set`, from the menu you were given. You are
granted that analysis, and you are then scored on whether you reach the
baseline's decision. CARTOGRAPH's pass/flag is the external key for that last
step; it is not a rival score to beat and not a finding to recover.

**K6 is counted apart from the 55 and never pooled with them.** Its inputs are
the expert re-refinement — the manual columns of the same deposited workbook —
where the five groups above are documentary statements about the automated
deposit. `Ba2ZrSnO6` reads 91.12 per cent target phase at stage one and 22.0 at
stage two. No day-one verifier can compute this decision, and the two stages
are never averaged.

**The evidence is contaminated by construction.** The re-refinement was
performed by people who already knew how the dispute came out, so the steering
is *simulated*: the experiment was not performed on request, its result was
looked up. Every stage-two row says so.

---

## The verdict grammar, and the witness

Three verdicts: `refuted`, `cannot_verify`, `inapplicable`. **There is no
affirming verdict.** Deciding *for* a claim would need the measured diffraction
patterns, which were never deposited. A
submission containing `verified` is rejected.

A refutation must carry a **witness**: where you looked, what you observed, what
the claim required instead. It counts only when `tools/check_witness.py` —
standard library only, sharing no code with any verifier — re-opens the evidence
and establishes a *contradiction*. Presence of the observed values is necessary
and never sufficient.

The full contract, with the submission schema and worked examples that have been
run through the checker, is **[`docs/ENTRANT.md`](docs/ENTRANT.md)**. Read it
before submitting.

---

## K3 needs an ICSD licence

K3 asks whether a product was already known, which means looking a composition
up in a crystallographic reference database. The critique used the **ICSD**,
which is subscription-only. Its files are not redistributed here; the benchmark
carries the collection code and a hash so a licence holder can confirm they
pulled the same entry.

This is a scope boundary, not a caveat to be buried. Report K3 separately, and
state which corpus you used — an ICSD result is comparable to the critique's and
an open-database result is not. Everything else in the benchmark is fully
reproducible without a licence.

---

## What is deliberately not here

**The verification layer.** The system this benchmark was built to evaluate
lives in a separate repository, and nothing here imports it. That separation is
the point: a benchmark whose scorer depends on one verifier cannot fairly score
another.

**A scorer that could be gamed by construction.** The answer keys ship — a
benchmark whose key is secret cannot be audited — but no tool here reads a key
into a submission.

**Nothing else.** The mutant generator ships too, in `bench/mutate.py`, with the
diffraction machinery it prices each mutant's difficulty with — about a third of
the code here, and enough of it that you can generate your own mutants rather
than only testing against ours. One seam is left open: its claim-in-disguise
test wants the layer's admissibility fingerprint, which does not ship, and falls
back to treating every pair as distinct. That is the safe direction — a mutant
stays in and a person sees it — but the test is inert here, not passing.

The **contamination set** ships with it: six instances built so a verifier
reading only the claim cannot tell them from the real ones — four broken, so
the honest verdict is `refuted`, and two healed, so it is `cannot_verify`. It
is the control for the failure this benchmark most needs to exclude, a verifier
that pattern-matches the claim instead of reading the evidence.
`docs/contamination-set.md` states what it does and does not establish.

---

## Layout

```
bench/     the per-target scorer, the deterministic harness, the label and
           baseline builders, the mutant generator and the diffraction
           machinery it prices difficulty with
tools/     the standalone witness checker, the submission scorer, the ceiling
           builder, the no-layer ablation runner, the shim
data/labels/    the answer keys, with their correction logs in the headers
data/entrant/   what a verifier receives: 40 instances, the follow-up menu,
                and the 6 contamination instances
data/rivals/    open-database rival structures with hashes; the ICSD entries
                are carried by collection code, not redistributed
data/mutants/   the evidence files for both constructed sets, one per compound
data/mutants_demo.csv        the constructed claims' truth and difficulty,
data/contamination_set.csv   kept outside the claim so no file carries its
                             own answer
docs/      ENTRANT.md the submission contract  ·  specification.md the
           benchmark as a whole  ·  ceiling.md the target list in prose  ·
           contamination-set.md the control  ·  nolayer-conditions.md the
           ablation  ·  known-defects.md the defect list
```

---

## Honest limitations

**[`docs/known-defects.md`](docs/known-defects.md) is part of the deliverable.**
Read it before trusting a number.

The most important one for an entrant: **the scorer was built for verifiers
making an honest attempt and is not hardened against a submitter trying to
defeat it.** Declared attacks and their measured effect are in
`docs/ENTRANT.md`; some remain open. Scores are reported, not policed.

K5's transcription and K3's licence condition both carry their status in the
data files themselves. The two symmetry determinations where our recomputation
disagrees with the critique's are excluded from K2 rather than scored, because
deciding which of two independent programs is right is a crystallographic
judgement this benchmark does not make.

**Every predicate now tests against the claim record, not against your own
text.** That was the recurring hole — the space-group predicate and the
stoichiometry predicate both graded refutations against the `required` field the
submitter wrote — and both are closed. The declared attacks and their measured
effect are in `docs/ENTRANT.md` §7a; a K1 or K3 score is still checked by hand
before it is reported, because the scorer is built for honest attempts and is
not hardened against a determined one.

Two things affect what you can rely on today, and `§8i` of the defect list has
the rest. The answer keys are **stale against their own inputs** —
`tools/build_ceiling.py --check` says so. The counts they carry agree with the
contract and the scorer, so nothing is known to be wrong; what is not in force
is the guarantee the digest exists to give. Rebuilding needs the deposit and one
file that does not ship, so the keys as shipped are the only ones there are. And
one constructed instance, `Ba2ZrSnO6` in `data/mutants_demo.csv`, points at a
file asserting the reverse of its own label, because both constructed sets write
to the same path and the contamination set wrote last. Use its recorded hash,
not the path.

---

## Licence and citation

MIT, see [`LICENSE`](LICENSE). The deposited structure files and the ICSD
entries are not ours and are not covered by it.

If you use this benchmark, cite the three sources above alongside it — they are
the record it reproduces, and the findings it scores against are theirs.

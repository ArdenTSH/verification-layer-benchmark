# The no-layer conditions: A and B

*28 August 2026. `tools/run_nolayer.py`. What a model is given when it is given
no layer, stated concretely enough to dispute. The layered condition is called
C throughout and is described only where the contrast needs it —
the research repository's `methodology.md` covers it in full; it
does not ship here. Paths below that begin `Aletheia_v0/` are in the layer's own
repository, a separate artifact, and will not resolve inside this checkout.*

---

## 1. Why these exist

Every number this project holds measures **model plus layer**. There is no
**model alone**, so nothing yet says whether the layer helps, hurts, or is
irrelevant. That is the load-bearing claim of the whole architecture and it has
never been tested.

A and B bracket it:

- **A — bare.** The model gets the claim and the deposited file as text. No
  execution. Measures what reading and recall alone recover.
- **B — tooled.** The same, plus one shot at running code it writes itself.
  Measures whether **our** scaffolding matters or merely **having a tool** does.

A against C conflates two things — having any computational tool at all, and
having this particular architecture. **B against C separates them, and is the
comparison that defends the contribution.**

## 2. Condition A — bare

### What it receives

| | |
|---|---|
| the claim | as published, undecomposed |
| the claim record | what the claim asserts, and explicitly what it **does not** assert |
| the refinement row | the robot's own Rwp and phase fractions — stage one |
| the deposited structure file | **inlined into the prompt as text, in full** |
| the follow-up menu | the modalities it may request |
| the submission contract | verbatim, the same one an outside entrant receives |

### What it does not receive

**No tools of any kind.** It must parse the file as text and reason from it —
count occupancies by reading `_atom_site` rows, judge symmetry from what the
header states, derive a lattice parameter by hand.

**No reference corpus and no network.** It is told to declare
`reference-database` as `cannot_verify` rather than guess what a database
contains.

### What it returns

One line of JSON: a verdict, one finding per evidence class it examined, a
witness on every refutation, and its observations.

### What A is actually measuring

Reading and recall, and nothing else. Because it cannot compute, its
`space_group_number` can only be the number the file **states** — and the
deposited files state `P 1` on 38 of the 40, which is a formatting convention
of the software that wrote them, not a determination. **A is therefore expected
to fail the symmetry group for a mechanical reason**, and any symmetry it does
get right came from reading rather than computing. That is the point of the
condition, not a defect in it.

## 3. Condition B — tooled

### What it receives

The same claim, claim record, refinement row, menu and contract as A. The
structure file is **not inlined**; it is on disk in the working directory.

### What it may do

**Write one self-contained Python 3 program.** It runs **once**. The model
never sees the output and is not asked to revise, so it commits blind — the
same seal condition C's checks are held to.

The program may import **anything installed**, including pymatgen, numpy and
scipy. There is no restricted vocabulary and no allowlist.

### The execution environment

| | |
|---|---|
| working directory | a fresh temporary directory containing **only the one structure file** |
| environment | credential-scrubbed, via `isolate.scrubbed_env()` |
| wall clock | 120 seconds |
| network | none available |
| reference corpus | **none on disk** |
| static audit | **none** |
| output contract | whatever it prints to standard output is parsed as the submission |

**B deliberately runs ungated model-written code, and that is the point.**
Generic tool use *without* the layer's security gate is precisely what is being
measured. What containment exists is the process and the filesystem, not a
static audit: the repository is not reachable by a relative path, the
environment holds no credentials, and the clock stops it.

**It is not a sandbox.** The child can still open a socket, and no seccomp or
container boundary is built — the same limitation `Aletheia_v0/src/isolate.py` states about
itself.

### What B is actually measuring

Whether a model with a general-purpose interpreter and no scaffolding recovers
what the layer recovers. It can do anything a layered check can do, and much it
cannot: fit, refine, simulate, iterate within its one program.

## 4. What A and B share

Both go through the **same submission contract** and are scored by the **same
scorebook** that scores the layered arms, via `tools/score_submission.py`.

Both are held to the **same witness standard**: a refutation counts only when
`tools/check_witness.py` — stdlib-only, sharing no code with the layer —
re-opens the deposited file and establishes a contradiction. Firing unwitnessed
refutations scores worse than abstaining.

Both declare **one finding per evidence class examined**, including classes
where they found nothing. That is how coverage is measured, and it is the part
of the contract that had to change before this ablation was possible: the old
format carried one verdict per compound, so a verifier that looked at something
and found nothing declared nothing at all.

**The seal applies.** One completion per instance; the runner refuses to enter
a populated output directory without `--fill`; no expert label, flag, verdict or
finding enters either prompt.

## 5. What A and B do not get that C does

| | A | B | C |
|---|---|---|---|
| model calls, 40 compounds | 40 | 40 | **441** |
| calls per compound | 1 | 1 | 7 to 16, median 10 |
| claim decomposed into families | no | no | **yes, 4** |
| may execute code | no | **yes, once** | yes, once per child |
| what it may call | — | **anything installed** | **14 primitives, nothing else** |
| static security audit | — | none | yes; 2 of 441 blocked |
| refutations independently re-checked | via the scorer | via the scorer | via the scorer, **and** aggregation |
| entailment filter | no | no | yes |
| rivals built, admitted, priced | no | no | yes |
| verdict decided by | the model | the model | **a 5-state rule fixed in code** |
| results combined across attempts | — | — | **aggregation, fails closed** |
| reference corpus on disk | **no** | **no** | **yes** — pinned ICSD snapshot |

### What C does, per compound, so the column above is not just a list

The layered condition is `Aletheia_v0/src/run_chain.py`. Per compound:

1. **Decomposition** — one model call turns the paper claim into child claims,
   one per family: `phase-present`, `cation-ordering`, `weight-fraction`,
   `novelty`. For opus5 this produced 7 to 16 children per compound.
2. **Elicitation** — one model call **per child** writes a Python function
   `check(ctx)`. Bought once ever per subject per generation.
3. **The security gate** — the source is parsed and audited before anything
   runs. Failing code is never compiled; the outcome is `BLOCKED`, which is not
   a check outcome and can support no refutation. 2 of 441 were blocked.
4. **Isolated execution** — the check runs in a child interpreter started
   without credentials, with a wall clock and a single JSON result contract.
5. **The check returns** a status, optionally a witness, optionally
   observations, optionally a follow-up request.
6. **Witness validation** — every refutation goes to `tools/check_witness.py`,
   which re-opens the deposited file and must establish a **contradiction**.
7. **Entailment** — a child asserting more than its parent has its refutation
   recorded and **not propagated** to the compound.
8. **Rivals** — alternative structures are built, tested for admissibility on
   three independent rules, and priced.
9. **Instance decision** — one of five states, by an ordered rule fixed in code.
10. **Aggregation** — child states become one compound verdict, failing closed.

Steps 3 to 10 are deterministic and cost nothing. Only 1 and 2 call a model.

**A and B do steps 2, 4 and 5 only** — one call, one execution, one result —
and B's step 4 has no step 3 in front of it.

### The point this table is easy to misread

**B is not "C without tools". In raw capability B has more than C.**

C's fourteen primitives are thin wrappers over pymatgen —
`ctx.space_group_number(symprec=0.1)` calls the same engine B imports directly
and uses without restriction.

What B lacks is not capability but **scaffolding**, and it is four distinct
things. A gap between B and C could come from any of them:

| what C has and B does not | why it could produce a gap |
|---|---|
| **attempts** — 7 to 16 per compound against 1 | more independent attacks find more |
| **decomposition** — the claim split into four families | a check aimed at one assertion is easier to write than one aimed at all of them |
| **a fixed decision rule** | B decides its own verdict and may decide it loosely |
| **aggregation** | C combines many child results under a rule that fails closed |

**Attempts is the confound worth removing first**, because it is the easiest to
remove and the least interesting if it explains everything. If B scores below C,
the next condition is **B′ — attempts matched**, several programs per compound
rather than one, holding attempts constant and leaving decomposition, the
decision rule and aggregation as the remaining difference.

## 5a. The shared scoring route, and why it had to be repaired first

`tools/score_submission.py` is **not a runner**. It takes one JSONL file and
scores it against the ceiling using the same scorebook that scores the layered
arms, through an adapter. It never calls a model. All three conditions reach it
the same way:

```
A  -> tools/run_nolayer.py --condition a  -> submission.jsonl -\
B  -> tools/run_nolayer.py --condition b  -> submission.jsonl --> score_submission.py
C  -> Aletheia_v0/src/run_chain.py -> ledger -> tools/ledger_to_submission.py -/
```

**That common route is what makes the comparison legitimate, and it was not
legitimate until 28 August.** Scoring C from its ledger and a submission from
its JSONL gave different answers on the same work — K1 6 against 4, K3 2
attempted against 0 — so any A-versus-C figure would have been measuring the
adapter rather than the layer. Three repairs closed it: the projection emits
per-evidence-class findings, picks the witness that **validates** rather than
the first written, and takes the mode by the scorer's own canonical key. opus5,
sonnet5 and gpt56-terra now score **identically by both routes across every
group**.

## 6. Running them

```
# free: build and print one prompt, spend nothing
.venv/bin/python tools/run_nolayer.py --condition a --model opus5 --dry-run

# GATED - these spend money. 40 calls each.
.venv/bin/python tools/run_nolayer.py --condition a --model opus5
.venv/bin/python tools/run_nolayer.py --condition b --model opus5

# free
.venv/bin/python tools/score_submission.py results/nolayer/a-opus5/submission.jsonl
```

To compare against a layered arm, project it through the **same route** — never
score C from its ledger and A or B from a submission, or the comparison
measures the adapter:

```
.venv/bin/python tools/ledger_to_submission.py \
    results/chain/opus5-gen2/rebuilt/children_rebuilt_budget1e+07.csv \
    --out /tmp/layered.jsonl
.venv/bin/python tools/score_submission.py /tmp/layered.jsonl
```

Observed cost, opus5: **A about 28 seconds per call, B about 70** — B generates
a whole program rather than a JSON line, then executes it.

`--only "<compounds>"` runs a subset; `--limit N` takes the first N; `--fill`
buys only instances with no reply on disk.

## 7. Standing limits on anything A or B produces

**K3 is unreachable for both, by construction.** No corpus, no network. A
comparison on that group measures **evidence access, not method**, and must be
reported as such.

**B gets one attempt where C gets eleven.** Unmatched until B′ runs.

**A and B are one model.** Nothing here separates opus's ability from the
conditions; four arms exist only for C.

**Contamination is uncontrolled in all three, and worst here.** The critique is
open-access and almost certainly in training data. A bare model has nothing but
the file and its memory, so a *good* A score is the most likely of the three to
be recall rather than reading. The H1/B1 contamination set was not bought in
this generation.

**B's failures split two ways and must not be pooled.** A program that crashes
or times out yields no submission line, which scores as **not attempted**, not
as wrong. B's coverage and B's accuracy are separate numbers.

**A's symmetry failures are mechanical, not analytic.** See §2. Do not read them
as an inability to determine symmetry.

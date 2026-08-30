# The contamination set: H1 healed, B1 broken

*Rebuilt after review found three blocking defects in the first build, then
**run on 28 August 2026** across seven verifier configurations. The result is
in §Result below.*

*The set ships as `data/contamination_set.csv` — six rows, each carrying its
truth and its evidence hash — with the evidence files under `data/mutants/` and
the six instances as `data/entrant/instances_contamination.jsonl`. To rebuild
it: `bench/mutate.py --contamination --emit-claims contamination`, which writes
to `results/contamination_set.csv`, the gitignored working tree, and not over
the shipped copy.*

---

## What it is for

The critique is open-access and almost certainly in the training data of any
large model. A verifier may flag a famous compound because it **recalls the
dispute**, not because it read the file. Nothing else in this benchmark tests
that.

Twins were retired on 27 August because building one requires judging whether a
substituted compound is chemically plausible, which this layer does not do. A
matched healed/broken pair needs no such judgement.

## The two directions

**H1 — healed.** Take a deposit the critique flagged under E2 and remove the
fault: separate the cation species that shared a site. The claim is now **true
of its evidence**.

**B1 — broken.** Take a deposit the critique did **not** flag under any code,
which is fully ordered, and disorder the cation pair the claim distinguishes.
The claim is now **false of its evidence**.

**The compound name is preserved in both, and that is the whole point.**

| | reads the file | recalls the literature |
|---|---|---|
| **H1** (famous, fault removed) | cannot_verify | **refuted** — flags a fault no longer present |
| **B1** (unfamous, fault added) | refuted | **cannot_verify** — passes a fault that is there |

Two independent signals, in opposite directions, on the same behaviour.

## What was wrong with the first build

All three were blocking, and none was found by a test.

### The claim contained its own answer

`Claim.to_probe_dict()` copies `provenance` into the payload as `source`, and
`build_prompt` renders every key of that payload into the prompt. A B1 claim
reached the model reading:

```
  structure_type: ordered model asserted over a disordered deposit
  source: contamination control B1 (broken: a compound the critique did not
          flag, disordered on the claimed pair)
```

Two lines, either of which hands over the whole experiment — and hands it over
in the direction that flatters the layer. The generator's own docstring said
this could not happen.

**A third leak survived the first two repairs.** `build_prompt` also renders
the evidence **path**, and files were written as `data/mutants/B1_<compound>.cif`.
The payload had been scrubbed and the filename still named the direction.

**The standard now, stated so it can be disputed.** *Symmetric* information is
allowed: the model may be able to tell a claim was constructed, because the
path says `data/mutants/` and the honest alternative — writing these files
under a path reading `Automated_Refinement_Results` — would be a false
statement about provenance. That knowledge is the same in both directions and
so cannot bias a verifier toward healed or toward broken, which is the only
contrast measured. *Directional* information is forbidden anywhere the model
can see: payload, statement, or path.

`mutate._leaks()` enforces it at construction time, over the payload **and**
the evidence path, matching on word boundaries so that the atom label `Sb1` in
a clean file is not reported as the term `b1`. Verified over the built prompt
for all six: **no directional term reaches the model.**

### One healed file was not healed

`rocksalt-parity` splits a shared site 50/50 by lattice parity. On
`KPr9(Si3O13)2` the shared site is K 0.1 / Pr 0.9, so the split emitted
**`K5Pr5(Si3O13)2`** — a different compound, wrong formula, charge-imbalanced.
That file **legitimately refutes its own claim**, so a verifier reading it
correctly was scored as a memoriser. One of three healed compounds, inverted,
and nothing caught it because nothing compared the output composition to the
input.

`_assert_composition_preserved` now does, on every construction in both
directions. It compares **element ratios**, not printed formulas: the first
version of the guard compared `reduced_formula` strings and rejected a correct
healing, because a disordered `Ba1Zr0.5Sn0.5O3` and its ordered `Ba2ZrSnO6` are
the same composition over different cell multiples. That is the same defect as
joining compounds by printed name — made twice in this repository in two days.

**`Mg3NiO4` looks like a free replacement and is not:** its pair sits at
0.75/0.25 and fails the same way. The guard refuses it.

### The broken compounds were not clean

B1 requires a deposit the critique did not flag, so that flagging it can only
come from reading the injected fault. **All four original picks were flagged,
three of them under E3** — *ordering asserted without evidence*, which is
literally the fault B1 injects.

| dropped | flagged under |
|---|---|
| `Mn4Zn3(NiO6)2` | E3 |
| `MgTi4(PO4)6` | E4 |
| `Mn2VPO7` | E1 + E3 |
| `CaCo(PO3)4` | E3 |

A model recalling the critique flags those for the remembered reason and scores
as though it read the file. The two directions collapsed into one, and the
collapse ran the wrong way.

Replaced with four of the eight compounds carrying **no critique flag of any
kind**, each verified fully ordered as deposited.

## What is built

| file | direction | sites | mixed cation sites | original had | baseline flags it |
|---|---|---|---|---|---|
| `Ba2ZrSnO6` | H1 | 40 | **0** | 1 | yes |
| `MgCuP2O7` | H1 | 176 | **0** | 4 | no |
| `CaFe2P2O9` | B1 | 56 | added | 0 | no |
| `KNa2Ga3(SiO4)3` | B1 | 84 | added | 0 | no |
| `InSb3(PO4)6` | B1 | 68 | added | 0 | yes |
| `KBaGdWO6` | B1 | 40 | added | 0 | yes |

B1 carries a difficulty number — the counts a check would need to catch the lie
— running **1.7e2 to 8.9e4**. H1 carries none: there is nothing to catch.

**The baseline column is recorded, not disqualifying.** The external baseline's
flags are about phase fractions and fit quality, not about whether cations are
ordered, so they give a memorising model no reason to call a structure
disordered. It is written down so a reader can weigh it rather than discover it.

## What the construction does and does not assert

**Healing separates the species. WHICH ordered arrangement is our construction
choice**, declared in the label table, made by `rocksalt-parity`. The claim
asserts the cations are ordered; it does not name a pattern, so no pattern can
be derived from it. No claim is made that this arrangement is the one the
material adopts.

Ordering lowers symmetry, so a healed file's space group is generally not the
claimed one. **The claim attached to a healed mutant carries the healed file's
own space group** — the claim is made true of its evidence, which is the point.

**Truth lives outside the claim**, in `results/contamination_set.csv`, joined by
id at analysis time.

## The limit that is not fixable by care: it cannot reach significance

**Two healed and four broken is six compounds.** Even a flawless result — both
H1 behaving one way, all four B1 the other — gives Fisher's exact
**p ≈ 0.067 one-sided**, which clears no conventional bar. At the previous
3/4 split it was 0.029 one-sided, and whether that clears a two-sided 0.05
depends on which convention is used: doubling gives 0.057 and fails, the
sum-of-tails method gives 0.029 and passes.

**This is declared, not padded.** It is what the construction rule affords:
only two E2-flagged deposits have a shared site at exactly 1/2, and inventing
more requires either an ordering rule matched to arbitrary occupancy ratios or
a chemical plausibility judgement, which is what retired twins.

**So the honest reading of any result here is "consistent with" or
"inconsistent with", never "shows".** It is one attempt at a control that did
not previously exist, and it should be reported as an attempt.

**The route to a stronger version**, if it is ever worth the elicitation: an
ordering rule that builds the supercell matching a 3:1 or 9:1 occupancy ratio
would readmit `Mg3NiO4` and `KPr9(Si3O13)2` and take H1 to four, and the eight
unflagged compounds allow B1 up to eight. That would be a 4/8 split — still
small, but roughly an order of magnitude better in p.

## What it does not do

**It is not a reproduction target.** Truth here is planted by us. It measures
whether a verifier reads its evidence, not whether it recovers expert findings,
and neither substitutes for the other.

**It does not measure detection competence in general.** That is the M-family.

**It is one construction rule on six compounds.** A verifier could fail it for
reasons other than memorisation — a brittle check, an unusual cell. Read the
two directions together: failing H1 *and* B1 in the memorising direction is a
much stronger signal than either alone.

## Result

**Run 28 August 2026: six constructed files against seven configurations, 42
checks. Every configuration completed 6 of 6.** Note that "6 of 6 checks" is
completion and "6 of 6 correct" is accuracy — they are different quantities,
and the bare form is not written here because it was once used for both a
message apart and read as a perfect score both times.

| configuration | H1 correct | B1 correct | total correct |
|---|---|---|---|
| A — reading only, no layer | **2 of 2** | 4 of 4 | **6 of 6** |
| B — one program, file unseen | 1 of 2 | 4 of 4 | 5 of 6 |
| B2 — one program, file seen | **2 of 2** | 4 of 4 | **6 of 6** |
| the layer, `opus5` | **2 of 2** | 4 of 4 | **6 of 6** |
| the layer, `sonnet5` | **2 of 2** | 2 of 4 | 4 of 6 |
| the layer, `gpt56` | **2 of 2** | 1 of 4 | 3 of 6 |
| the layer, `gpt56-terra` | **2 of 2** | 1 of 4 | 3 of 6 |

**No configuration shows the memorising pattern.** All seven get H1 2 of 2:
not one flagged a famous, disputed compound whose fault had been removed. That
is the memorisation-sensitive direction, and it is clean across four models and
three unlayered conditions. Every failure is in the *detection* direction —
`gpt56` and `gpt56-terra` miss injected disorder on 3 of 4 compounds;
`CaFe2P2O9` goes from 0 mixed cation sites to 12 and they do not report it.

**B's single H1 miss is not memory, and its witness proves it.** On healed
`Ba2ZrSnO6` it refuted with `observed: space group 'P 1' (No. 1) in deposited
file` against `required: Fm-3m (No. 225) as claimed`. It read the CIF *header*,
which says `P 1` because of the expansion convention; the healed file computes
to Fm-3m (225), exactly what the claim asserts. That is the `P 1` attack in
`docs/ENTRANT.md` §7a firing by accident on a condition that never saw the file
and so could not know the header was a convention rather than a finding.

**It cannot reach significance.** Two healed and four broken: a flawless result
gives Fisher's exact **p ≈ 0.067**. Six compounds, one run, no interval. Read
every line above as *consistent with*, never as *shows*. Four healed and eight
broken would give p ≈ 0.002, and getting there needs an ordering rule matched
to arbitrary occupancy ratios — `KPr9(Si3O13)2` at 0.1/0.9 and `Mg3NiO4` at
0.75/0.25 are both refused by the composition guard today.

**And the awkward part.** A and B2, with no layer at all, score 6 of 6 correct,
matching `opus5` with the layer. On this control the architecture buys nothing,
and the three configurations that fail are all layered ones running weaker
models. That is consistent with the control measuring model capability rather
than architecture — which is what it was built to do — and it must not be
reported as a win for the layer.

**This is not a ceiling group and enters no K.** Truth here is planted, so it
measures whether a verifier reads its evidence, not whether it recovers expert
findings. Neither substitutes for the other.

## Running it again

It is **runnable**, which it was not at first: nothing wrote a claims file for
a mutant, and the scoring route had the demonstration table hardcoded, so there
was no path from a constructed file to a score.

Only the first step runs in this repository. The three that follow are the
verification layer's own campaign runner, which lives in the layer repository
and deliberately does not ship here — an entrant elicits and scores through
`tools/score_submission.py` instead. They are kept because the sequence, and
the requirement below that the control be bought in the same generation as the
campaign it controls, is the part worth copying.

```
# build the set and emit claims under one name, so every arm is elicited
# against IDENTICAL claims  -- runs here
.venv/bin/python bench/mutate.py --contamination --emit-claims contamination

# GATED - this spends money. One completion per subject per generation.
# the three steps below are the LAYER's, not this repository's
.venv/bin/python Aletheia_v0/src/run_chain.py --models <arm> --budget 1e7 \
    --generation 2 --claims-from contamination

# free
.venv/bin/python Aletheia_v0/src/rebuild_ledger.py --model <arm> --generation 2 \
    --budget 1e7 --out results/chain/<arm>-gen2/rebuilt-contamination
.venv/bin/python Aletheia_v0/src/score_chain.py \
    results/chain/<arm>-gen2/rebuilt-contamination/ledger_rebuilt_budget1e+07.csv \
    --mutants results/contamination_set.csv
```

**It must be bought in the same generation as the campaign it controls**, under
the same library version and prompt, or the comparison is confounded. Six
compounds, one cation-ordering check each, five arms: **30 checks.**

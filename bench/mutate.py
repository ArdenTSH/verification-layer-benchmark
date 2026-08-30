"""
The mutation generator. Manufactured ground truth.

Every mutant is a claim that is WRONG (or undecidable) by construction, with the
truth and a difficulty number recorded beside it, never inside it. The label table
this writes lives in results/, joined to the claims by id at analysis time only; a
claim handed to a model never contains its own answer (see claim.py).

Mutation families:

  M1  ordered-assertion: assert the ordered model where the truth is the disordered
      parent. Difficulty: n* between the two profiles, i.e. the counts a check would
      need to catch the lie. This is the A-Lab Error-3 situation, manufactured.
  M2  occupancy-permutation: swap two cation species between their sites; assert the
      original. The mutant file contradicts the asserted structure.
  M3  cation-substitution: replace cations with same-family neighbours (Ba to Sr,
      Zr to Hf, Sn to Ge...). Breaks any training-data lookup while preserving the
      structural situation. probe.py's Sr2HfGeO6 is an instance of this family.
  M4  spurious-phase: mix a second phase's profile in at weight fraction w; assert
      the pure phase. Difficulty falls as w grows.
  M5  degraded-counts: the assertion is checked against a Poisson draw at N counts;
      undecidable by construction when N is well below the pair's n*.
  M6  underdetermined-pair: any (assertion, truth) pair whose profiles sit within
      epsilon under the noise model; ground truth is cannot-verify BY CONSTRUCTION.
      These calibrate abstention; the four real inconclusive cases are the held-out
      validation that this class is realistic.

Ground-truth verdicts recorded: "refuted" (M1, M2, M4 at high w), "cannot_verify"
(M5 at low N, M6). Difficulty knob: n* against the assumed instrument.

EQUIVALENT-MUTANT FILTER (mutation testing's classic pitfall; VERIFY),
the equivalent-mutant problem: a mutant that is not actually wrong - the mutated file matches
the asserted structure up to symmetry (file-rung: M1, M2), or the truth
profile is numerically indistinguishable from the asserted one (profile-
rung: M4) - would be scored as a missed refutation and silently deflate
detection scores. Such mutants are marked excluded_equivalent in the label
table WITH the measured distance (logged, never deleted) and skipped by
scoring. The numerical floor EQUIVALENCE_H2 separates exact equivalence
from merely-expensive pairs: M6's deliberately expensive mutant has small
but finite h2 and must survive the filter.

Usage: .venv/bin/python bench/mutate.py     (writes results/mutants_demo.csv)
"""

from __future__ import annotations

import csv
import json
import re
import sys
import warnings
from dataclasses import dataclass, asdict
from pathlib import Path

import numpy as np

warnings.filterwarnings("ignore")
sys.path.insert(0, str(Path(__file__).resolve().parent))

from pymatgen.core import Structure  # noqa: E402

from claim import Claim, Ref, resolve_ref, validate, ENVELOPE_VERSION  # noqa: E402
from library import (load_structure, simulate_pattern, compare_patterns,  # noqa: E402
                     distinguishability, disordered_rival, ordered_model,
                     site_occupancies, LIBRARY_VERSION)
from control_test import find_cif  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "data" / "mutants"
LABELS = ROOT / "results" / "mutants_demo.csv"

# Same-family substitution map for M3. Chemically similar, lookup-breaking.
SIMILAR = {"Ba": "Sr", "Sr": "Ca", "K": "Na", "Na": "K", "Zr": "Hf", "Hf": "Zr",
           "Sn": "Ge", "Ti": "Zr", "Fe": "Ga", "Mn": "Fe", "Ni": "Mg", "In": "Ga"}

# Numerical floor for profile-level equivalence: below this h2 the two
# profiles are the same pattern up to arithmetic, not an expensive pair.
# Declared assumption; M6 mutants sit far above it by construction.
EQUIVALENCE_H2 = 1e-9


def _structurally_equivalent(a: Structure, b: Structure) -> bool:
    """File-rung equivalence: the mutation produced a file DOCUMENTARILY
    identical to the original - same rounded site list, species and all -
    so nothing is actually wrong and a check reading the file has nothing
    to catch. Uses the admissibility gate's fingerprint (rule A3's 'the
    claim in disguise' test), NOT StructureMatcher: loose tolerance
    matching would exclude mutants whose files genuinely contradict the
    assertion (a near-symmetric cation swap is still a wrong file, and is
    still measurably a different pattern). Total: failures read as
    not-equivalent (the safe direction: the mutant stays in and a human
    sees it)."""
    try:
        from admissibility import _fingerprint
        return _fingerprint(a) == _fingerprint(b)
    except Exception:
        return False


@dataclass
class Mutant:
    claim: Claim
    truth: str            # "refuted" | "cannot_verify"  (never inside the claim)
    reason: str           # one line, for the label table
    difficulty_n_star: float | None
    family: str           # M1..M6
    excluded_equivalent: bool = False   # equivalent-mutant filter
    equivalence_note: str = ""          # the measured distance or match, logged


# THE CLAIM NEVER CONTAINS ITS OWN ANSWER, AND THAT NOW HAS TEETH.
#
# It did until 28 Aug 2026. `Claim.to_probe_dict()` copies `provenance` into
# the payload as `source`, and `build_prompt` renders every key of that payload
# into the prompt, so a B1 claim reached the model reading:
#
#   structure_type: ordered model asserted over a disordered deposit
#   source: contamination control B1 (broken: a compound the critique did not
#           flag, disordered on the claimed pair)
#
# Two lines, either of which hands over the entire experiment - and hands it
# over in the direction that flatters the layer. The generator's own docstring
# said this could not happen.
#
# The repair is not to reword those strings. It is that H1 and B1 must be
# BYTE-IDENTICAL in everything the model sees except the compound name, the
# claimed group, and the file. A model may still infer that a claim was
# constructed; what it must not be able to infer is WHICH construction, because
# that is the bit the control measures. Symmetric information cannot bias a
# direction.
#
# `_leaks()` enforces it at construction time rather than trusting the author.

# THE STANDARD, stated so it can be disputed rather than guessed at.
#
# SYMMETRIC information is allowed. A model may be able to tell that a claim
# was constructed - the evidence path says `data/mutants/` and no honest
# alternative exists, because writing these files under a path that reads
# `Automated_Refinement_Results` would be a false statement about provenance,
# and this project does not fabricate. Knowing "this is constructed" is the
# same information in both directions, so it cannot bias a verifier towards
# healed or towards broken, which is the only contrast the control measures.
#
# DIRECTIONAL information is forbidden. Anything from which H1 could be told
# from B1 - in the payload, in the statement, or in the path.
_DIRECTIONAL_TERMS = (
    "healed", "broken", "h1", "b1", "disorder", "ordered model asserted",
    "fault", "removed", "injected", "planted", "critique", "flagged",
    "ground truth", "answer", "control",
)

# One provenance string for every mutant, whatever its direction.
MUTANT_PROVENANCE = ("constructed claim, benchmark corpus; the construction "
                     "and its truth are recorded outside the claim")


def _leaks(claim: Claim) -> list[str]:
    """Directional terms anywhere the model can see: payload OR evidence path.

    Checks the path as well as the payload, because the first two repairs
    scrubbed the payload and left `data/mutants/B1_<compound>.cif` being
    rendered straight into the prompt by `build_prompt`. An audit that checks
    one surface is not an audit.

    Matched on WORD BOUNDARIES, not substrings. A substring test flags the
    atom label `Sb1` in a perfectly clean CIF as the term `b1`, and a guard
    that cries wolf gets switched off.
    """
    surfaces = [f"{k} {v}" for k, v in claim.to_probe_dict().items()]
    surfaces += [str(e.uri) for e in claim.evidence]
    seen = " ".join(surfaces).lower().replace("/", " ").replace("_", " ")
    return [w for w in _DIRECTIONAL_TERMS
            if re.search(rf"(?<![a-z0-9]){re.escape(w)}(?![a-z0-9])", seen)]


def _mk_claim(subject: str, mfam: str, n: int, assertion: dict, refs: list[Ref],
              provenance: str = MUTANT_PROVENANCE) -> Claim:
    c = Claim(
        id=f"mutant:{subject}:cation-ordering:{mfam}-{n:03d}",
        family="cation-ordering",
        assertion=assertion,
        evidence=tuple(refs),
        provenance=provenance,
        versions={"envelope": ENVELOPE_VERSION, "generator": "mutate-0.3.0",
                  "library": LIBRARY_VERSION},
    )
    bad = _leaks(c)
    if bad:
        raise AssertionError(
            f"{c.id}: the model-visible claim payload names the construction "
            f"({bad}). A claim never contains its own answer. Note that the id "
            f"itself is NOT part of the payload - to_probe_dict() emits the "
            f"assertion plus `source` - but everything that IS must be "
            f"identical between H1 and B1.")
    return c


def m1_ordered_assertion(name: str, group: set[str], method: str) -> Mutant:
    """Assert ordering; the deposited truth is the disordered parent."""
    deposit = load_structure(find_cif(name))
    ordered = ordered_model(deposit, method, group)
    disordered = disordered_rival(ordered, [group])
    _, p1 = simulate_pattern(ordered)
    _, p0 = simulate_pattern(disordered)
    nstar = distinguishability(p1, p0)
    sg = ordered.get_space_group_info(symprec=0.1)[0]
    path = _contamination_path(name)
    disordered.to(filename=str(path))          # the "deposited" file is the truth
    claim = _mk_claim(name, "M1", 1, _mutant_assertion(name, sg),
                      [resolve_ref(path, "cif")])
    h2 = compare_patterns(p1, p0)
    equiv = _structurally_equivalent(ordered, disordered) or h2 < EQUIVALENCE_H2
    return Mutant(claim, "refuted", "file is the disordered parent of the asserted "
                  "ordering", nstar, "M1",
                  excluded_equivalent=equiv,
                  equivalence_note=f"h2 {h2:.3e} vs floor {EQUIVALENCE_H2:.0e}"
                  + ("; structures match up to symmetry" if equiv and
                     h2 >= EQUIVALENCE_H2 else ""))


def m2_occupancy_permutation(name: str, a: str, b: str) -> Mutant:
    """Swap species a and b between their sites; assert the original structure."""
    s = load_structure(find_cif(name))
    swapped = s.copy()
    swapped.replace_species({a: "Xx", b: a})     # Xx placeholder two-step swap
    swapped.replace_species({"Xx": b})
    path = _contamination_path(name)
    swapped.to(filename=str(path))
    _, p1 = simulate_pattern(s)
    _, p0 = simulate_pattern(swapped)
    nstar = distinguishability(p1, p0)
    sg = s.get_space_group_info(symprec=0.1)[0]
    claim = _mk_claim(name, "M2", 1, _mutant_assertion(name, sg),
                      [resolve_ref(path, "cif")])
    h2 = compare_patterns(p1, p0)
    equiv = _structurally_equivalent(s, swapped) or h2 < EQUIVALENCE_H2
    return Mutant(claim, "refuted", f"{a} and {b} occupancies exchanged in the file",
                  nstar, "M2",
                  excluded_equivalent=equiv,
                  equivalence_note=f"h2 {h2:.3e} vs floor {EQUIVALENCE_H2:.0e}"
                  + ("; the swap is a symmetry operation" if equiv and
                     h2 >= EQUIVALENCE_H2 else ""))


def m3_cation_substitution(name: str) -> Mutant:
    """Element-substituted analogue; assertion inherits the original's ordering claim.
    Truth must be recomputed, not inherited: here the substituted file
    keeps the original's disorder, so the ordered assertion is refuted by the file."""
    s = load_structure(find_cif(name))
    subst = {el: SIMILAR[el] for el in {sp.symbol for site in s for sp in site.species}
             if el in SIMILAR}
    mut = s.copy()
    mut.replace_species(subst)
    new_name = mut.composition.reduced_formula.replace(" ", "")
    path = _contamination_path(new_name)
    mut.to(filename=str(path))
    mixed = [row for row in site_occupancies(mut) if row["mixed"]]
    truth = "refuted" if mixed else "cannot_verify"
    claim = _mk_claim(new_name, "M3", 1, _mutant_assertion(new_name, "Fm-3m"),
                      [resolve_ref(path, "cif")])
    return Mutant(claim, truth,
                  "substituted file keeps the parent's cation disorder" if mixed
                  else "substitution left no mixed site; not auto-labelable",
                  None, "M3")


def m4_spurious_phase(name: str, other: str, w: float) -> Mutant:
    """Assert the pure phase; the profile truth contains w of a second phase."""
    _, p_pure = simulate_pattern(load_structure(find_cif(name)))
    _, p_other = simulate_pattern(load_structure(find_cif(other)))
    p_mix = (1 - w) * p_pure + w * p_other
    nstar = distinguishability(p_pure, p_mix)
    claim = _mk_claim(name, "M4", int(round(w * 100)),
                      _mutant_assertion(name, "as deposited"),
                      [resolve_ref(find_cif(name), "cif")])
    h2 = compare_patterns(p_pure, p_mix)
    return Mutant(claim, "refuted", f"{w:.0%} {other} in the truth profile", nstar, "M4",
                  excluded_equivalent=h2 < EQUIVALENCE_H2,
                  equivalence_note=f"h2 {h2:.3e} vs floor {EQUIVALENCE_H2:.0e}")


def m6_underdetermined(name: str, group: set[str], method: str,
                       budget: float = 1e5) -> Mutant | None:
    """If n* between assertion and rival exceeds the stated budget, the pair is
    undecidable at that budget BY CONSTRUCTION: ground truth cannot-verify."""
    deposit = load_structure(find_cif(name))
    ordered = ordered_model(deposit, method, group) if any(
        r["mixed"] for r in site_occupancies(deposit)) else deposit
    disordered = disordered_rival(ordered, [group])
    _, p1 = simulate_pattern(ordered)
    _, p0 = simulate_pattern(disordered)
    nstar = distinguishability(p1, p0)
    if nstar <= budget:
        return None
    claim = _mk_claim(name, "M6", 1,
                      _mutant_assertion(name,
                          ordered.get_space_group_info(symprec=0.1)[0]),
                      [resolve_ref(find_cif(name), "cif")])
    return Mutant(claim, "cannot_verify",
                  f"n* {nstar:.2e} above the stated budget {budget:.0e}", nstar, "M6")


# ---------------------------------------------------- the contamination pair

# THE CONTROL THIS EXISTS FOR. The critique is open-access and almost certainly
# in the training data of any large model, so a verifier may flag a famous
# compound because it recalls the dispute rather than because it read the file.
# Twins were retired on 27 August 2026 because building one requires judging
# whether a substituted compound is chemically plausible, which this layer does
# not do.
#
# A matched HEALED / BROKEN pair needs no such judgement, because neither
# direction invents chemistry:
#
#   H1 HEALED   take a deposit the critique flagged, and construct the file the
#               CLAIM ITSELF asserts. The ordered model is the claim's own
#               content, not our opinion about what is plausible. The fault the
#               critique found is removed and nothing else changes, so the
#               claim is now TRUE of its evidence. Truth: nothing to refute.
#
#   B1 BROKEN   take a deposit the critique did NOT flag and that is fully
#               ordered, and disorder the cation pair the claim distinguishes.
#               The claim is now FALSE of its evidence. Truth: refuted.
#
# THE COMPOUND NAME IS PRESERVED IN BOTH, which is the whole point. A verifier
# reading the file answers H1 with "consistent" and B1 with "refuted". A
# verifier recalling the literature answers H1 with "refuted" - flagging a
# compound whose fault is no longer there - and B1 with "consistent".
#
# Neither direction is scored against the expert record. Truth here is planted
# by us and lives outside the claim, exactly as for M1 to M6.

def _contamination_path(name: str) -> Path:
    """Where a contamination-set file lives, in a shape that reveals nothing.

    THE THIRD LEAK, and the one the first two repairs missed. `build_prompt`
    renders the evidence PATH into the prompt. Files were written as
    `data/mutants/H1_<compound>.cif` and `data/mutants/B1_<compound>.cif`, so
    the model was handed the direction of the construction in the filename -
    after the payload had been carefully scrubbed of it.

    A leak audit that checks the payload and not the path is not an audit. The
    layout now mirrors a real deposit exactly, `<dir>/<compound>/<compound>.cif`,
    and is identical for both directions. Which file is which lives in the
    label table, joined by claim id.
    """
    d = OUT_DIR / name
    d.mkdir(parents=True, exist_ok=True)
    return d / f"{name}.cif"


def _mutant_assertion(name: str, sg: str) -> dict:
    """The claim payload, IDENTICAL in shape and wording for H1 and B1.

    Phrased the way a decomposed A-Lab claim is phrased, so the mutant is not
    identifiable by the shape of its statement either. The claimed group is the
    file's own group in both directions: for H1 because healing lowers symmetry
    and the claim is made true of its evidence, for B1 because that is what the
    original deposit asserted.
    """
    return {"compound": name,
            "space_group_claimed": sg,
            # exactly what a real decomposed cation-ordering claim carries;
            # a mutant must not be identifiable by the shape of its payload
            "structure_type": "unstated",
            "statement": (f"{name} was synthesised with the ordered structure "
                          f"reported in the deposited file, in space group "
                          f"{sg}.")}


def _assert_composition_preserved(name: str, deposit, built, what: str) -> None:
    """A construction must not change WHICH COMPOUND the file is.

    THE DEFECT THIS CLOSES. `rocksalt-parity` splits a shared site 50/50 by
    lattice parity. On KPr9(Si3O13)2 the shared site is K 0.1 / Pr 0.9, so the
    even/odd split emitted K5Pr5(Si3O13)2 - a different compound, with the
    wrong formula and unbalanced charge. That file legitimately refutes its own
    claim, so a verifier reading it correctly was scored as a memoriser. One of
    only three healed compounds, inverted, and nothing caught it because
    nothing compared the output composition to the input.

    Occupancies that are not 1/2 need an ordering rule that builds the right
    supercell for the ratio. rocksalt-parity is not that rule and no longer
    pretends to be: it refuses instead of emitting a wrong compound.
    """
    # COMPARE COMPOSITION, NOT THE PRINTED FORMULA. The first version of this
    # guard compared `reduced_formula` strings and rejected a correct healing:
    # a disordered deposit reduces to Ba1Zr0.5Sn0.5O3 and its ordered form to
    # Ba2ZrSnO6, which are the same composition written over different cell
    # multiples. That is the same defect as joining compounds by printed name,
    # made twice in one repository in two days, so it is spelled out here:
    # element RATIOS are the invariant, and a formula string is not.
    fa = deposit.composition.fractional_composition
    fb = built.composition.fractional_composition
    els = set(fa.as_dict()) | set(fb.as_dict())
    drift = max(abs(fa.as_dict().get(e, 0.0) - fb.as_dict().get(e, 0.0))
                for e in els)
    a = deposit.composition.reduced_formula
    b = built.composition.reduced_formula
    if drift > 1e-6:
        raise ValueError(
            f"{what} on {name} changed the compound: deposit is {a}, the "
            f"constructed file is {b}, largest element-fraction drift "
            f"{drift:.4f}. The construction must alter the "
            f"ARRANGEMENT and never the composition. This is what "
            f"rocksalt-parity does to any shared site whose occupancies are "
            f"not 1/2 - it splits by lattice parity, which is a 50/50 split. "
            f"Use an ordering rule matched to the occupancy ratio, or drop "
            f"this compound from the set.")


def h1_healed(name: str, group: set[str], method: str) -> Mutant:
    """The claim's own ordered model, deposited as the evidence.

    WHAT THE CONSTRUCTION ASSERTS, AND WHAT IT DOES NOT. The critique's E2 on
    these compounds is that the deposited file carries two cation species on
    one crystallographic site where the claim requires them distinct. Healing
    means separating them: after this, no site carries more than one cation.

    WHICH ordered arrangement is OUR construction choice, declared here and
    recorded in the label table. The claim asserts that the cations are
    ordered; it does not name a pattern, so the pattern cannot be derived from
    it. That is a construction decision, not a chemical finding, and no claim
    is made that this arrangement is the one the material adopts.

    Ordering lowers symmetry, so the healed file's space group is generally
    not the claimed one. The claim attached to a healed mutant therefore
    carries the HEALED file's own space group: the claim is made true of its
    evidence, which is the entire point of the control."""
    deposit = load_structure(find_cif(name))
    ordered = ordered_model(deposit, method, group)
    _, p1 = simulate_pattern(ordered)
    _, p0 = simulate_pattern(deposit)
    h2 = compare_patterns(p1, p0)
    sg = ordered.get_space_group_info(symprec=0.1)[0]
    _assert_composition_preserved(name, deposit, ordered, "healing")
    path = _contamination_path(name)
    ordered.to(filename=str(path))     # the healed file IS the claim
    claim = _mk_claim(name, "H1", 1, _mutant_assertion(name, sg),
                      [resolve_ref(path, "cif")])
    return Mutant(claim, "cannot_verify",
                  "the deposited file now satisfies the claim; a refutation "
                  "here cannot have come from the evidence",
                  None, "H1",
                  equivalence_note=f"h2 healed-vs-deposited {h2:.3e}")


def b1_broken(name: str, group: set[str]) -> Mutant:
    """A clean deposit, disordered on the pair the claim distinguishes."""
    deposit = load_structure(find_cif(name))
    broken = disordered_rival(deposit, [set(group)])
    _, p1 = simulate_pattern(deposit)
    _, p0 = simulate_pattern(broken)
    h2 = compare_patterns(p1, p0)
    nstar = distinguishability(p1, p0)
    sg = deposit.get_space_group_info(symprec=0.1)[0]
    _assert_composition_preserved(name, deposit, broken, "disordering")
    path = _contamination_path(name)
    broken.to(filename=str(path))
    claim = _mk_claim(name, "B1", 1, _mutant_assertion(name, sg),
                      [resolve_ref(path, "cif")])
    equiv = _structurally_equivalent(deposit, broken) or h2 < EQUIVALENCE_H2
    return Mutant(claim, "refuted",
                  "the deposited file is disordered on the pair the claim "
                  "distinguishes; the critique flagged nothing here",
                  nstar, "B1", excluded_equivalent=equiv,
                  equivalence_note=f"h2 {h2:.3e} vs floor {EQUIVALENCE_H2:.0e}")


# THE COMPOUND SELECTION, and why each one is on the list. Revised 28 Aug 2026
# under review; the previous selection is recorded here because both changes
# were corrections of a defect rather than preferences.
#
# H1 - HEALED. Requires an E2-flagged deposit whose shared site can be ordered
# without changing the compound. Only occupancies of exactly 1/2 qualify under
# rocksalt-parity, which splits by lattice parity.
#
#   Ba2ZrSnO6      Zr/Sn at 0.5/0.5   ok
#   MgCuP2O7       Mg/Cu at 0.5/0.5   ok
#   KPr9(Si3O13)2  K/Pr  at 0.1/0.9   REMOVED. The parity split emitted
#                                     K5Pr5(Si3O13)2 - wrong compound, wrong
#                                     charge - which legitimately refutes its
#                                     own claim, so a verifier reading it
#                                     correctly scored as a memoriser.
#   Mg3NiO4        Mg/Ni at 0.75/0.25 NOT ADDED, for the same reason. It looks
#                                     like a free replacement and is not.
#
# `_assert_composition_preserved` now refuses all three of the bad cases, so
# this list cannot silently regain one. Adding compounds back needs an ordering
# rule matched to the occupancy ratio, not a longer list.
#
# H1 IS THEREFORE 2 COMPOUNDS, not 3. That is a real loss of power and it is
# declared in docs/contamination-set.md rather than padded.
#
# B1 - BROKEN. Requires a deposit THE CRITIQUE DID NOT FLAG UNDER ANY CODE, so
# that flagging it can only come from reading the injected fault.
#
# All four previous picks failed that test, and three failed it in the worst
# possible way - flagged under E3, "ordering asserted without evidence", which
# is LITERALLY the fault B1 injects:
#
#   Mn4Zn3(NiO6)2  E3      MgTi4(PO4)6  E4      Mn2VPO7  E1+E3      CaCo(PO3)4  E3
#
# A model recalling the critique flags those for the remembered reason and
# scores as though it read the file, so the control's two directions collapsed
# into one and the collapse ran the wrong way. Replaced with four of the eight
# compounds carrying no critique flag at all, each verified fully ordered
# (0 mixed cation sites) so that disordering is a real change.
#
# `baseline` below records whether the external baseline flags the compound.
# That is NOT a disqualification - the baseline's flags are about phase
# fractions and fit quality, not about whether cations are ordered, so they
# give a memorising model no reason to call a structure disordered. It is
# recorded so a reader can weigh it rather than discover it.
CONTAMINATION_JOBS = [
    # healed: E2-flagged, shared site at exactly 1/2, composition preserved
    lambda: h1_healed("Ba2ZrSnO6", {"Zr", "Sn"}, "rocksalt-parity"),
    lambda: h1_healed("MgCuP2O7", {"Mg", "Cu"}, "rocksalt-parity"),
    # broken: no critique flag of any kind, fully ordered as deposited
    lambda: b1_broken("CaFe2P2O9", {"Ca", "Fe"}),        # baseline: not flagged
    lambda: b1_broken("KNa2Ga3(SiO4)3", {"K", "Na"}),    # baseline: not flagged
    lambda: b1_broken("InSb3(PO4)6", {"In", "Sb"}),      # baseline: flagged
    lambda: b1_broken("KBaGdWO6", {"K", "Ba"}),          # baseline: flagged
]


def emit_claims(mutants, out_dir: Path) -> int:
    """Write mutant claims in the shape `run_chain --claims-from` reads.

    THE MISSING RUN PATH. The contamination set was described as "built, not
    run"; it was in fact NOT RUNNABLE. `run_chain` elicits against
    `data/claims/decomposed/<name>/*.claims.json` and nothing ever wrote one
    for a mutant, so there was no route from a constructed file to a check.

    Written under one name, `contamination`, so every arm is elicited against
    the SAME claims:

        run_chain.py --models <arm> --claims-from contamination --generation N

    That is the same mechanism the haiku checker-only arm uses, and it matters
    here for the same reason: the control compares arms on identical claims, so
    the claims must not be per-arm.

    THE TRUTH IS NOT WRITTEN HERE. It lives in the label table and is joined by
    id at analysis time. A claims file a model reads never carries an answer.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    written = 0
    for m in mutants:
        c = m.claim
        subject = c.assertion["compound"]
        doc = {
            "compound": subject,
            "parent": f"mutant:{subject}:paper-claim",
            "model": "constructed",
            "claims": [{
                "id": c.id, "family": c.family, "assertion": c.assertion,
                "evidence": [asdict(e) for e in c.evidence],
                "provenance": c.provenance, "context": c.context,
                "parent": c.parent, "versions": c.versions,
            }],
            "problems": [], "rejections": [],
        }
        safe = f"{m.family}_{subject}".replace("/", "_").replace(" ", "_")
        (out_dir / f"{safe}.claims.json").write_text(json.dumps(doc, indent=1))
        written += 1
    print(f"\nwrote {written} claims file(s) to {out_dir}")
    print("elicit with:  run_chain.py --models <arm> --claims-from "
          f"{out_dir.name} --generation <N>")
    print("the label table is NOT in these files; join by claim id at "
          "analysis time")
    return written


def main() -> int:
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--contamination", action="store_true",
                    help="build the H1/B1 contamination pair instead of the "
                         "M-family demonstration set")
    ap.add_argument("--out", default="",
                    help="label table path; defaults per set")
    ap.add_argument("--emit-claims", default="",
                    metavar="NAME",
                    help="also write claims files under "
                         "data/claims/decomposed/NAME so run_chain can elicit "
                         "against them: --claims-from NAME. Use one name for "
                         "every arm, so the control compares arms on identical "
                         "claims. Suggested: contamination")
    args = ap.parse_args()

    mutants: list[Mutant] = []
    jobs = CONTAMINATION_JOBS if args.contamination else [
        lambda: m1_ordered_assertion("Ba2ZrSnO6", {"Zr", "Sn"}, "rocksalt-parity"),
        lambda: m1_ordered_assertion("FeSb3Pb4O13", {"Fe", "Sb"}, "ewald-minimal"),
        lambda: m2_occupancy_permutation("Hf2Sb2Pb4O13", "Hf", "Sb"),
        lambda: m3_cation_substitution("Ba2ZrSnO6"),
        lambda: m4_spurious_phase("Sn2Sb2Pb4O13", "CaFe2P2O9", 0.20),
        lambda: m4_spurious_phase("Sn2Sb2Pb4O13", "CaFe2P2O9", 0.02),
        lambda: m6_underdetermined("InSb3Pb4O13", {"In", "Sb"}, "ewald-minimal"),
        lambda: m6_underdetermined("Ba2ZrSnO6", {"Zr", "Sn"}, "rocksalt-parity"),
    ]
    label = (args.out or ("results/contamination_set.csv" if args.contamination
                          else "results/mutants_demo.csv"))
    for job in jobs:
        try:
            m = job()
            if m is None:
                continue
            problems = validate(m.claim)
            if problems:
                print(f"  INVALID {m.claim.id}: {problems}")
                continue
            mutants.append(m)
        except Exception as exc:
            print(f"  FAILED: {type(exc).__name__}: {exc}")

    if not mutants:
        print("no mutants generated")
        return 1

    out_labels = Path(label) if str(label).startswith("/") else ROOT / label
    out_labels.parent.mkdir(parents=True, exist_ok=True)
    with out_labels.open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["claim_id", "family", "truth", "reason", "difficulty_n_star",
                    "excluded_equivalent", "equivalence_note",
                    "evidence_uri", "evidence_sha256"])
        for m in mutants:
            ref = m.claim.evidence[0]
            w.writerow([m.claim.id, m.family, m.truth, m.reason,
                        f"{m.difficulty_n_star:.3e}" if m.difficulty_n_star else "",
                        str(m.excluded_equivalent), m.equivalence_note,
                        ref.uri, ref.sha256 or ""])

    if args.emit_claims:
        emit_claims(mutants, ROOT / "data" / "claims" / "decomposed"
                    / args.emit_claims)

    n_excl = sum(1 for m in mutants if m.excluded_equivalent)
    print(f"\n{'claim id':44s} {'truth':13s} {'n* difficulty':>13s}  reason")
    print("-" * 110)
    for m in mutants:
        d = f"{m.difficulty_n_star:.2e}" if m.difficulty_n_star else "-"
        tag = "  [EXCLUDED: equivalent]" if m.excluded_equivalent else ""
        print(f"{m.claim.id:44s} {m.truth:13s} {d:>13s}  {m.reason}{tag}")
    print(f"\nwrote {out_labels} ({len(mutants)} mutants, {n_excl} excluded as "
          f"equivalent); mutant files in {OUT_DIR}")
    print("Labels live HERE, never inside the claims. Join by id at analysis time.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

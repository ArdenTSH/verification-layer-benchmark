"""
THE PER-TARGET SCOREBOOK. One score per benchmark item, always.

Owner's ruling, 27 August 2026: "it should also never be a single 'score'.
scoring is per benchmark item. always."

What this replaces. `reproduce_benchmark.py --rate` produced ONE number - "6/7
of the wired Tier A target (86%)" - by comparing compound-level VERDICTS
against compound-level expert FLAGS. That worked only for E2, because E2 is
the only target group shaped like a flag. The ceiling holds roughly 85 expert
assertions and most of them are VALUES: this file's symmetry is P6_3/m, this
lattice parameter is 10.6168 A. A verdict cannot express a value, so those
targets were unscoreable and the denominator collapsed to the 7 compounds E2
covers. The small denominator was an artefact of the output grammar, not a
property of the record.

Two changes make per-target scoring possible, and both are recorded honestly
here rather than assumed:

  1. THE OBSERVATION CHANNEL (primitives.Verdict.observations, 27 Aug 2026). A
     check may now record what it measured, whatever its verdict. Value
     targets are scored against that channel.
  2. PER-TARGET EXCLUSION. The old rule excluded a COMPOUND from scoring when
     it had no check at all, and counted it fully otherwise - so a compound
     that lost three of four checks to transport failure still contributed
     every one of its targets. Exclusion is now per target: a target is
     dropped from the denominator only when no check that could reach THAT
     target was elicited.

EVERY BANKED CHECK PREDATES THE CHANNEL, so on today's ledgers every value
target scores NOT-OBSERVED. That is the true state and this script prints it
as such. It does not become a miss and it does not quietly leave the
denominator: a target the layer had no way to record is reported in its own
column, because "the arm got it wrong" and "the layer could not write it down"
are different failures and pooling them would flatter the layer.

OUTCOME VOCABULARY, per target:
  RECOVERED    the arm's observation matches the expert value at the stated
               tolerance, or for a flag target the arm flagged the compound
  MISSED       a check ran and reached a different answer, or did not flag
  NOT-OBSERVED a check ran but recorded no observation of this quantity
  NOT-ATTEMPTED no check that could reach this target was ever bought; the
               target leaves the denominator and is counted separately

Denominators are the experts' and never pooled across groups. A count from one
target group is never quoted against another group's denominator.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "bench"))
# tools/ carries bench_shim, the benchmark's own copy of the handful of
# functions it used to import from the layer. See tools/bench_shim.py.
sys.path.insert(0, str(ROOT / "tools"))

LABELS = ROOT / "data" / "labels"

# Groups that report their score as a split rather than one figure, because a
# single number for them is earnable without doing the work.
SPLIT_GROUPS = {"K2"}

# ONE NAME PER OUTCOME, AND IT IS THE ENTRANT'S NAME.
# This state was printed three ways: the constant said NOT-ELICITED, the
# summary line said "not attempted", and docs/ENTRANT.md's outcome table said
# NOT-ATTEMPTED. "Elicited" is our word for buying a check from a model, which
# is not something an entrant does at all - they submit. The identifier below
# keeps its old spelling so the diff stays readable; the STRING, which is what
# anyone actually reads, is the entrant's.
RECOVERED, MISSED, NOT_OBSERVED, NOT_ELICITED = (
    "RECOVERED", "MISSED", "NOT-OBSERVED", "NOT-ATTEMPTED")
# the arm reached the finding; the layer could not validate the evidence class
UNVALIDATED = "UNVALIDATED"

# Tolerances travel with the number they qualify, never as a global default.
TOL = {
    "cubic_lattice_parameter_a": 0.0005,   # A; the deterministic harness's own
    "space_group_number": 0,               # exact: an identifier, not a quantity
    "mixed_cation_sites": 0,               # a count of sites; exact
}

# A quantity and the other keys that express the SAME measurement. Checked
# after the primary key, so a verifier reporting either form scores.
# ---------------------------------------------------------------- the version

# THE VERSION STAMP. A score is only meaningful beside the rules that produced
# it. The benchmark is `benchmark-0`, the referee the layer pins, stamped into
# every scorebook it prints so a number can always be read back to the rules
# that made it. A convention change is a NEW TAG, with results rebuilt rather
# than reinterpreted - never a silent edit under a name that already means
# something.
BENCHMARK_VERSION = "benchmark-0"


ALTERNATES = {
    "space_group_number": ("space_group_symbol",),
    "space_group_symbol": ("space_group_number",),
}


# --------------------------------------------------- the join key

# JOIN BY COMPOSITION, NEVER BY PRINTED NAME. This scorer joined raw compound
# strings until 28 Aug 2026, which is the THIRD occurrence of this project's
# signature bug: the deposit and the spreadsheet spell the same formula with
# its elements in a different order, so `Ba6Na2Ta2V2O17` in prx_table3.csv and
# `Ba6Ta2Na2V2O17` in the ledgers and the entrant bundle are one compound
# written two ways.
#
# What it cost, measured before the fix: a K2 target INSIDE the evaluation
# population scored NOT-ELICITED although checks had been bought and executed
# for it under the other spelling - and an entrant submitting the exactly
# correct answer under the bundle's own spelling scored the same. The target
# was unreachable through the published contract by anyone.
#
# The two earlier occurrences were fixed in `intake_decomp` (evidence
# resolution) and in the K2 label join. Fixing one site did not generalise,
# which is why the key is a named module-level function here rather than an
# inline call: there is one place to look and one place to change.

def _norm_available() -> bool:
    try:
        from pymatgen.core import Composition   # noqa: F401
        return True
    except Exception:
        return False


# FAIL LOUD, NOT OPEN. `build_labels.norm_formula` returns the raw string when
# pymatgen is missing, which is right for label construction and wrong here: a
# scorebook that silently degrades to string joins reproduces the very defect
# this key exists to close, and reports a plausible number while doing it.
_NORM_OK = _norm_available()

_KEY_CACHE: dict = {}


def _key(name: str) -> str:
    """Composition-normalised join key for one compound name.

    A name that is not a formula at all - K5 carries claim identifiers - falls
    back to the stripped string, which is correct: there is nothing to permute.
    A MISSING PARSER is a different thing and raises at import.
    """
    s = (name or "").strip()
    if s in _KEY_CACHE:
        return _KEY_CACHE[s]
    out = s
    try:
        from pymatgen.core import Composition
        out = Composition(s).reduced_formula
    except Exception:
        out = s
    _KEY_CACHE[s] = out
    return out


# Which check families could plausibly reach which quantity. Used ONLY for the
# exclusion test - "was a check that could reach this target ever bought" - and
# never to credit a recovery.
REACHES = {
    "space_group_number": ("cation-ordering", "phase-present"),
    # the symbol is the SAME determination written differently, so it reaches
    # the same target. Advertised as a recognised key while being absent here
    # meant a verifier reporting only "P6_3/m" scored NOT-OBSERVED on K2 with
    # the right answer in hand.
    "space_group_symbol": ("cation-ordering", "phase-present"),
    "cubic_lattice_parameter_a": ("phase-present", "cation-ordering"),
    "e2_flag": ("cation-ordering", "phase-present"),
    "e4_flag": ("novelty",),
    "baseline_flag": ("phase-present", "weight-fraction", "cation-ordering"),
    "target_weight_fraction_pct": ("weight-fraction",),
    # rho's third term. Recognised 29 Aug 2026 so it stops having to be parsed
    # out of a free-form phase list; K6 derives it only when two phases make it
    # the exact remainder, and otherwise says it was not recorded.
    "largest_impurity_wt_pct": ("weight-fraction", "phase-present"),
    "mixed_cation_sites": ("cation-ordering",),
}


def _rows(path: Path, skip_comments: bool = True):
    with path.open() as fh:
        lines = (x for x in fh if not x.startswith("#")) if skip_comments else fh
        return list(csv.DictReader(lines))


def _sg_symbol_to_number(sym) -> int | None:
    """An International Tables number from a space-group symbol, or None.

    Uses pymatgen's own table rather than a hand-written map: a hand-written
    one would be a second source of truth for the 230 groups and would drift.
    """
    try:
        from pymatgen.symmetry.groups import SpaceGroup
        return int(SpaceGroup(str(sym).strip()).int_number)
    except Exception:
        return None


def _sg_number(text: str) -> int | None:
    """International Tables number out of a printed symbol like 'Pm-3m (221)'."""
    m = re.search(r"\((\d{1,3})\)", text or "")
    return int(m.group(1)) if m else None


# ------------------------------------------------------------- the target list

# ---------------------------------------------- the evaluation population

# THE 40. Every scored target lives here and nowhere else.
#
# Five populations recur in this record and they are different numbers: 41
# claimed, 40 adjudicated, 42 with deposited files, 36 in the critique's own
# table, 43 bookkeeping rows. `docs/specification.md` §3 states the rule: A COUNT
# FROM ONE POPULATION IS NEVER QUOTED AGAINST ANOTHER POPULATION'S
# DENOMINATOR.
#
# The scorebook broke that rule until 28 Aug 2026. It built targets straight
# from the critique's label files, so it carried compounds that are not in the
# evaluation population at all:
#
#   Mg3NiO4        offline, not adjudicated - made outside the autonomous run
#   Y3Ga3In2O12    offline, not adjudicated - the same
#   Zn2Cr3FeO8     removed by the Correction
#
# None has a claim, none was ever elicited, and NO VERIFIER CAN EVER SCORE
# ONE. They were reported as NOT-ELICITED, which reads as a coverage failure
# by the arm and depressed every coverage figure printed. K1 printed a
# denominator of 8 where the critique itself says "8 flags, 7 in the
# evaluation population", and K3 printed 3 where 2 are in it.
#
# The filter is applied ONCE, at the single exit of build_targets, so no
# future group can reintroduce it by constructing targets its own way.
def _eval_population() -> set:
    """Compounds the Correction adjudicated: the 40. Nothing else is scored."""
    return {r["compound"] for r in _rows(LABELS / "merged_labels.csv")
            if (r.get("correction_verdict") or "").strip()
            in ("confirmed", "inconclusive")}


EXCLUDED_TARGETS: list = []   # filled by build_targets; printed by the report


def build_targets(stage: str = "one") -> list[dict]:
    """Every individually scoreable ceiling target, one dict each.

    A target is one expert assertion, not one compound. The critique's Table
    III makes 43 symmetry determinations; that is 43 targets, not 43 rows of
    one target. This is the whole point of the change.
    """
    targets: list[dict] = []

    # --- A1: the critique's symmetry determination per deposited file.
    # The expert value is what THEY determined by indexing the deposited file
    # (`indexed_sym`), which is the recoverable quantity. `proposed_sym` is the
    # claim, and comparing the two is what makes some of these findings.
    # TWO DETERMINATIONS LEAVE THE DENOMINATOR AS NAMED DISAGREEMENTS.
    #
    # `MgTi4(PO4)6` (they print R3/146, we compute R-3/148 at every tolerance
    # from 0.001 to 0.3, with no partial occupancies) and `FeSb3Pb4O13` (they
    # print R3m/160, we compute 216). Our own deterministic harness reports
    # both as [OBS] "differs", not as pass or fail, because the ceiling says:
    #
    #   "No pass or fail is stamped on a symmetry comparison. Declaring one of
    #    two independent symmetry programs correct about a structure is a
    #    crystallographic judgement this layer does not make."
    #
    # Stamping MISSED on them says the verifier got the answer wrong. It did
    # not: every arm reports the same number our own trusted base computes, and
    # which program is right is the judgement the ceiling refuses to make. A
    # target nobody may be scored against is not a target.
    #
    # They are NAMED rather than dropped silently, because a disagreement
    # between two independent determinations is a documentary fact worth
    # reporting - it is just not a score.
    SYMMETRY_DISAGREEMENTS = {"MgTi4(PO4)6", "FeSb3Pb4O13"}

    for r in _rows(LABELS / "prx_table3.csv"):
        n = _sg_number(r.get("indexed_sym", ""))
        if n is None:
            continue
        if _key(r["sample"]) in {_key(c) for c in SYMMETRY_DISAGREEMENTS}:
            continue
        targets.append({
            "group": "K2", "id": f"K2:{r['sample']}",
            "compound": r["sample"], "quantity": "space_group_number",
            "expected": n,
            "expected_display": r.get("indexed_sym", ""),
            "differs_from_claim": _sg_number(r.get("proposed_sym", "")) != n,
            "echo_level": _sg_number(r.get("proposed_sym", "")) == n,
            "source": "critique Table III",
        })

    # --- A2: the E2 flag. Flag-shaped, so scored on whether the arm flagged.
    for r in _rows(LABELS / "merged_labels.csv"):
        if r.get("prx_e2") == "1":
            targets.append({
                "group": "K1", "id": f"K1:{r['compound']}",
                "compound": r["compound"], "quantity": "e2_flag",
                "expected": True, "expected_display": "file differs from claim",
                "source": "critique Table I, E2",
            })

    # --- A3: Table II lattice parameters, from the transcription.
    t2 = LABELS / "prx_table2.csv"
    if t2.exists():
        for r in _rows(t2):
            v = (r.get("alab_cubic_a") or "").strip()
            if not v:
                continue      # the pure-phase row prints no A-lab value
            targets.append({
                "group": "K4", "id": f"K4:{r['compound']}",
                "compound": r["compound"],
                "quantity": "cubic_lattice_parameter_a",
                "expected": float(v), "expected_display": f"{v} A",
                "source": "critique Table II",
            })

    # --- K3 / E4: the product was already known. Flag-shaped, like E2.
    for r in _rows(LABELS / "merged_labels.csv"):
        if r.get("prx_e4") == "1":
            targets.append({
                "group": "K3", "id": f"K3:{r['compound']}",
                "compound": r["compound"], "quantity": "e4_flag",
                "expected": True,
                "expected_display": "already present in the reference database",
                "source": "critique Table I, E4",
            })

    # --- K6: the external baseline's decision. STAGE TWO ONLY.
    #
    # Its inputs are rwp_manual and the manual phase fractions - the expert
    # re-refinement. For Ba2ZrSnO6 the target fraction is 91.12 per cent at
    # stage one and 22.0 at stage two. A verifier holding only day-one
    # evidence cannot compute this decision, and neither can our own arms,
    # whose ctx.refinement_row(stage="one") returns the automated columns.
    #
    # So it is a target where its evidence exists, and absent where it does
    # not. That is the same stage discipline the rest of the layer already
    # follows, not a special case.
    base = LABELS / "cartograph_decisions.csv"
    if stage == "two" and base.exists():
        for r in _rows(base):
            targets.append({
                "group": "K6", "id": f"K6:{r['compound']}",
                "compound": r["compound"], "quantity": "baseline_flag",
                "expected": r["flagged"].strip().lower() == "true",
                "expected_display": ("flagged" if r["flagged"].strip().lower()
                                     == "true" else "passed"),
                "source": "CARTOGRAPH, frozen threshold 0.776",
            })

    # --- A4: prose structural claims, from the transcription when it exists.
    t4 = LABELS / "prx_prose_claims.csv"
    if t4.exists():
        for r in _rows(t4):
            q = (r.get("quantity") or "").strip()
            v = (r.get("value") or "").strip()
            if not q or not v:
                continue
            try:
                exp = float(v)
            except ValueError:
                exp = v
            targets.append({
                "group": "K5", "id": f"K5:{r['claim_id']}",
                "compound": r["compound"], "quantity": q,
                "expected": exp, "expected_display": v,
                "source": r.get("locus", "critique prose"),
            })

    # One stamping site rather than six construction sites: every target
    # carries its own join key, and `compound` stays the printed name.
    for t in targets:
        t["key"] = _key(t["compound"])

    # ONE EXCLUSION SITE. See the note above `_eval_population`.
    pop = {_key(c) for c in _eval_population()}
    kept, dropped = [], []
    for t in targets:
        (kept if t["key"] in pop else dropped).append(t)
    # A STAGE-TWO PASS SCORES K6 AND NOTHING ELSE (29 August 2026).
    #
    # K1, K2, K4 and K5 are documentary statements about the AUTOMATED
    # deposit - "the deposited file differs from the claim", "the symmetry of
    # each deposited file", "the cubic lattice parameter from each A-Lab CIF".
    # rebuild_ledger substitutes the Manual_Refinement_Results file on a
    # stage-two pass, so scoring those groups there compares a check executed
    # against the expert's file to a target defined on the robot's. Measured
    # with the model held completely fixed - the same generation-3 sources,
    # one execution at each stage - K1 goes 6 of 7 to 5 of 7, K2 38 to 36 and
    # K4 4 of 5 to 1 of 5. No model call separates those columns; 41 of the 42
    # deposits differ in lattice parameter beyond K4's 0.0005 A tolerance.
    #
    # Reading a paired report off that would say "the steered experiment made
    # the layer worse at symmetry", which is false. K1 to K5 are read from the
    # stage-one pass, where their targets are defined; the stage-two pass
    # carries K6, which exists only there.
    if stage == "two":
        kept = [t for t in kept if t["group"] == "K6"]

    EXCLUDED_TARGETS.clear()
    EXCLUDED_TARGETS.extend(dropped)
    return kept


# ------------------------------------------------------------------ the scoring


def _isnum(v) -> bool:
    try:
        float(v); return True
    except (TypeError, ValueError):
        return False


_ROUTE_CACHE: dict = {}


def _pseudocubic_routes(compound: str) -> dict:
    """Every legitimate route from this deposited cell to a cubic edge.

    Not a chemical judgement: each is a standard geometric relation between a
    distorted cell and the cubic subcell it approximates. Returns {} if the
    file cannot be read, in which case the caller falls back to the ordinary
    value rule rather than crediting anything.
    """
    if compound in _ROUTE_CACHE:
        return _ROUTE_CACHE[compound]
    out: dict = {}
    try:
        import math
        from bench_shim import resolve_cif, load_structure
        s = load_structure(resolve_cif("Automated_Refinement_Results", compound))
        a, b, c = s.lattice.abc
        V = s.lattice.volume
        out = {"mean(a,b)*sqrt2": (a + b) / 2 * math.sqrt(2),
               "c": c,
               "(4V/3)^(1/3)": (4 * V / 3) ** (1 / 3),
               "(2V)^(1/3)": (2 * V) ** (1 / 3),
               "mean(a*sqrt2, c/sqrt3)": (a * math.sqrt(2) + c / math.sqrt(3)) / 2}
    except Exception:
        out = {}
    _ROUTE_CACHE[compound] = out
    return out


def _observations(children: list[dict]) -> dict:
    """{(compound, quantity): [values]} from the observation channel."""
    out: dict = {}
    for r in children:
        blob = (r.get("observations") or "").strip()
        if not blob:
            continue
        try:
            obs = json.loads(blob)
        except Exception:
            continue
        for k, v in (obs or {}).items():
            out.setdefault((_key(r["compound"]), k), []).append(v)
    return out


def _elicited(children: list[dict]) -> set:
    """{(compound, family)} where a check actually ran.

    A source that was never bought, or that arrived as a transport failure and
    was recorded as inapplicable with no source on disk, does not count as
    elicited: the exclusion rule exists precisely to keep those out of the
    denominator rather than scoring them as misses.
    """
    got = set()
    for r in children:
        if (r.get("check_source") or "").strip() and \
                (r.get("verdict_raw") or "") not in ("MISSING", "NO-EVIDENCE",
                                                     "NO-CHECK-ELICITED "
                                                     "(declared stub)"):
            got.add((_key(r["compound"]), r["family"]))
    return got


# Which check families carry the evidence a given flag target rests on. This is
# what stops three groups reading one bit.
#
# K1 is the critique's E2: the DEPOSITED FILE differs from the claim. Only a
# check that read the file can establish it.
# K3 is the critique's E4: the product is ALREADY KNOWN. Only a check that
# consulted the reference database can establish it.
#
# Before 28 August all three flag groups were scored on "did the compound's
# ledger verdict come out refuted", which is one bit per compound. Since K1 and
# K6 disagree about what that bit should be on six compounds, and K3 and K6 on
# two more, a verifier could not satisfy both no matter how good it was:
# recovering K1 mechanically manufactured a K6 miss on the identical compound.
# Eight of the nine compounds carrying more than one flag target were in that
# state.
EVIDENCE_FAMILIES = {
    # K1: the deposited FILE differs from the claim. Only a check that read
    # the file establishes it.
    "e2_flag": ("cation-ordering", "phase-present"),
    # K3: the product is ALREADY KNOWN. Only a database lookup establishes it.
    "e4_flag": ("novelty",),
    # K6: the baseline flags a compound when the fit is poor and the target
    # phase is a small part of the sample. The layer's corresponding assertion
    # is the weight-fraction family. Giving K6 its own evidence family is what
    # dissolves the collision with K1: on the six compounds where the critique
    # flags the file and the baseline passes the fit, the two are now asking
    # different checks, not competing for one compound-level bit.
    "baseline_flag": ("weight-fraction",),
}

# PER-TARGET OVERRIDES. The group rule above says which evidence class a
# finding rests on IN GENERAL. For one target it is wrong, because the
# critique's own justification for that row uses a different class.
#
# MgV4Cu3O14 is filed under E2, "the deposited file differs from the claim",
# but the file does NOT differ: it is claimed P1, indexed P1, computes P1, and
# carries zero mixed-occupancy sites. The flag rests entirely on a comparison
# to ICSD 69731, (Cu1.5Mg0.5)V2O7 - a DATABASE comparison. So the evidence
# that establishes this E2 flag is database evidence, and requiring file
# evidence made the target unreachable by construction while the ceiling
# document said it was reachable. The two rules cancelled and no verifier
# could ever have scored it.
#
# Verified: opus5 generation 2 queried the pinned ICSD snapshot, got back
# exactly id 69731, and refuted - twice. It reproduced the critique's own
# reasoning and scored MISSED.
EVIDENCE_OVERRIDES = {
    ("e2_flag", "MgV4Cu3O14"): ("novelty",),
}

# WHAT THE STANDALONE WITNESS CHECKER CAN ADJUDICATE. It is stdlib-only and
# reads ONE artifact: the deposited structure file. It holds no reference
# corpus and no refinement table, so a refutation resting on either is
# something it can never reproduce - not because the refutation is wrong, but
# because the checker cannot see the evidence.
#
# Aggregation fails closed, which is right, so those refutations are
# downgraded and the compound reads cannot_verify. Scoring that as MISSED
# says the arm got it wrong. It did not. Across the four generation-2 arms
# there are 79 novelty refutations and not one of them can ever be validated.
#
# This is the same distinction the NOT-OBSERVED outcome already draws: "the
# arm got it wrong" and "the layer could not write it down" are different
# failures, and pooling them would flatter the layer. Here the pooling runs
# the other way and defames it.
# The checker reads three artifacts now, so every family's evidence is
# adjudicable in principle. UNVALIDATED is therefore reserved for what
# adjudicate() itself declines, not inferred from the family.
CHECKER_CAN_ADJUDICATE = ("cation-ordering", "phase-present",
                          "novelty", "weight-fraction")


def _refuting_families(children: list[dict]) -> dict:
    """{compound: {families that produced a refuting check}}."""
    out: dict = {}
    for r in children:
        if r.get("check_status") == "refuted":
            out.setdefault(_key(r["compound"]), set()).add(r.get("family", ""))
    return out


def _per_child_verdicts(children: list[dict]) -> dict:
    """{(compound_key, family): the strongest per-CHILD witness verdict}.

    SCORE EACH TARGET OFF ITS OWN CHECK, NOT OFF THE COMPOUND'S ROLLED-UP
    VERDICT. That aggregated bit is why K1, K3 and K6 were three reads of one
    measurement: every flag group asked the same question - "is this compound
    refuted" - and could not help colliding. The evidence-family rule narrowed
    which refutations counted but still ANDed onto the same bit, so the
    collision was made rarer rather than removed.

    Each flag target now reads the checks in the family that carries its own
    evidence, and takes the strongest verdict among them:

      True           a check refuted and the standalone checker established a
                     contradiction. The target is recovered.
      UNADJUDICABLE  a check refuted and the checker cannot read that evidence
                     class at all. Reached, not validatable.
      False          a check refuted and the checker found no contradiction.
      ""             no refuting check in this family.

    Ordering matters and is deliberate: one validated refutation is enough, so
    True wins; and a class the checker cannot read is not evidence that the
    arm was wrong, so UNADJUDICABLE outranks False.
    """
    RANK = {"True": 3, "UNADJUDICABLE": 2, "NO-FILE": 1, "False": 0}
    out: dict = {}
    for r in children:
        if r.get("check_status") != "refuted":
            continue
        k = (_key(r["compound"]), r.get("family", ""))
        v = (r.get("witness_reproduced") or "").strip()
        if not v:
            continue
        if k not in out or RANK.get(v, -1) > RANK.get(out[k], -1):
            out[k] = v
    return out


def _flagged(children: list[dict], ledger: list[dict]) -> set:
    """Compounds the arm refuted, TAKEN FROM THE LEDGER, not from raw check
    status.

    This distinction is not pedantry and getting it wrong inflated this
    scorebook on first run. A child check may return "refuted" and still not
    refute anything: aggregation fails closed, so a refutation counts only on
    an explicit independent witness reproduction, and a downgraded refutation
    is not a refutation. Reading `check_status` directly walks straight past
    that rule. On one arm it credited three extra compounds - every one of
    them a witness that failed to reproduce - which is precisely the failure
    the 26 August repair was installed to prevent.

    The ledger verdict is the layer's answer. The scorebook scores that.
    """
    return {_key(r["compound"]) for r in ledger if r.get("verdict") == "refuted"}



# --------------------------------------------------------------------------
# K6 IS SCORED AS A REPRODUCTION, FROM THE LAYER'S OWN OBSERVATIONS.
# Changed 29 August 2026. What it replaces and why:
#
# K6 was a FLAG target read off a per-child witness verdict in the
# weight-fraction family. Three things made that unable to measure what it
# claimed to measure.
#
#   1. THE STATISTIC SPANS THREE QUANTITIES AND THE FAMILY RULE READ ONE.
#      The baseline flags on rho(Rwp, target weight fraction, largest single
#      impurity). The layer records the first two as first-class observations
#      on all 40 compounds - and records them mostly under `phase-present` and
#      `novelty`. Scoping K6 to `weight-fraction` guaranteed that the evidence
#      deciding the baseline's flag was never the evidence K6 read. Ba2ZrSnO6
#      is the clean case: stage-one rho 0.9692, carried almost entirely by an
#      Rwp of 19.22, and every weight-fraction check reasoned about the phase
#      fraction alone.
#
#   2. IT WAS SCORED THROUGH AN INVENTED THRESHOLD. Every weight-fraction
#      claim carries `threshold=0.5` stamped INVENTED BY INTAKE; the source
#      asserts no purity threshold. Aggregation's entailment rule refuses to
#      propagate refutations resting on it, so K6 was reading the one channel
#      the layer's own rules decline to honour. Measured on generation 3, 64
#      of 88 weight-fraction checks also read that 0.5 and compared it against
#      WEIGHT PERCENTAGES - a 100x error turning it into a trace-detection bar
#      - while others substituted bars of their own (90, 95, 99 wt%). The old
#      score was largely a record of which way that error fell.
#
#   3. A WITNESS VERDICT IS NOT A REPRODUCTION. Credit required the standalone
#      checker to validate a refutation, and its `stoichiometry` predicate
#      stamps a contradiction whenever a witness NAMES a secondary phase whose
#      formula differs from the target's - which is what a secondary phase is.
#
# What is scored now: take the layer's own recorded numbers, apply the
# baseline's own published rule by calling the same `rho_alab` that produced
# the answer key, and ask whether the layer's numbers reach the baseline's
# decision. No witness, no invented threshold, no refutation. Nothing here
# affirms a claim: the group compares two decisions and says whether they
# agree.
#
# BOTH KEYS ARE REPORTED AND NEVER POOLED. The published key is computed from
# the STAGE-TWO manual columns. Every check scored here read STAGE ONE. So the
# stage-two key measures "reproduce the published decision", which no
# stage-one verifier can do, and the stage-one key measures "reproduce the
# method on the evidence you hold", which is the question this population can
# actually answer.


def _k6_modal(vals):
    """The plurality recorded value, and how many distinct ones there were.

    Plurality, never any-of. Taking any recorded value that happens to fit is
    the defect this scorebook was repaired for on 28 August 2026, and it would
    reappear here as "some check somewhere wrote a number that works".
    """
    nums = [float(v) for v in vals if isinstance(v, (int, float))]
    if not nums:
        return None, 0
    return Counter(nums).most_common(1)[0][0], len(set(nums))


def _k6_records(children: list[dict]) -> dict:
    """{compound_key: [one dict per CHECK that recorded any of the terms]}.

    PER CHECK, NEVER PER KEY. A quantity is only meaningful beside the others
    the same check computed. Taking the plurality of each key independently
    mixes records: on Ba6Ta2Na2V2O17 one check failed to identify the target
    and reported the largest phase - the target's own 63.38 per cent - as the
    impurity, while a second identified it by composition and reported the
    largest genuine impurity at 18.25. Reading the target from the second and
    the impurity from the first produces a statistic neither check computed,
    and it is the same defect as taking any recorded value that happens to fit.
    """
    out: dict = {}
    for r in children:
        blob = (r.get("observations") or "").strip()
        if not blob:
            continue
        try:
            d = json.loads(blob)
        except Exception:
            continue
        rec = {k: d[k] for k in ("target_weight_fraction_pct",
                                 "fit_residual_rwp",
                                 "largest_impurity_wt_pct",
                                 "n_phases_reported")
               if isinstance(d.get(k), (int, float))}
        if rec:
            out.setdefault(_key(r["compound"]), []).append(rec)
    return out


def _k6_coherent(rec: dict) -> bool:
    """Is this record arithmetically possible?

    The largest SINGLE impurity cannot exceed the whole non-target remainder.
    A record violating that has misidentified the target - it is counting the
    target's own fraction as an impurity - and its statistic is not the
    baseline's. This rejects a record; it never repairs one.
    """
    wt = rec.get("target_weight_fraction_pct")
    wa = rec.get("largest_impurity_wt_pct")
    if wt is None or wa is None:
        return True
    return wa <= (100.0 - wt) + 0.01


def _k6_layer_rho(obs: dict, key: str, records: dict | None = None) -> tuple:
    """(rho, w_target, rwp, w_alt, provenance) from the LAYER's observations."""
    from reproduce_baselines import rho_alab
    # Prefer a single COHERENT check that carried the terms together.
    for rec in (records or {}).get(key, []):
        if not _k6_coherent(rec):
            continue
        if ("target_weight_fraction_pct" in rec and "fit_residual_rwp" in rec
                and "largest_impurity_wt_pct" in rec):
            r = rho_alab({"rwp_manual": rec["fit_residual_rwp"],
                          "target_pct": rec["target_weight_fraction_pct"],
                          "max_impurity_pct": rec["largest_impurity_wt_pct"]})
            if r is not None:
                return (r, rec["target_weight_fraction_pct"],
                        rec["fit_residual_rwp"], rec["largest_impurity_wt_pct"],
                        "one check recorded all three terms together")
    wt, _ = _k6_modal(obs.get((key, "target_weight_fraction_pct"), []))
    rwp, _ = _k6_modal(obs.get((key, "fit_residual_rwp"), []))
    wa, _ = _k6_modal([v for v in obs.get((key, "largest_impurity_wt_pct"), [])
                       if wt is None or (isinstance(v, (int, float))
                                         and v <= (100.0 - wt) + 0.01)])
    nph, _ = _k6_modal(obs.get((key, "n_phases_reported"), []))
    prov = "recorded"
    if wa is None and wt is not None:
        # DERIVE THE LARGEST IMPURITY ONLY WHERE ARITHMETIC DETERMINES IT.
        #
        # This is NOT the (100 - w_target) substitution the answer key was
        # corrected for on 28 August. That one was wrong because it fires when
        # three or more phases are present, where the deficit is SPLIT between
        # them and the largest single impurity is smaller than the total. Each
        # branch below is a case where the two quantities are the same number
        # by arithmetic, not by assumption:
        if wt >= 100.0:
            wa, prov = 0.0, ("largest impurity derived: the layer recorded the "
                             "target at 100 wt%, so there is no impurity")
        elif nph == 1:
            wa, prov = 0.0, ("largest impurity derived: one phase reported, so "
                             "there is no impurity")
        elif nph == 2:
            wa = round(100.0 - wt, 4)
            prov = ("largest impurity derived: two phases, so the single "
                    "impurity is the remainder")
    if wa is None:
        prov = ("largest impurity NOT RECORDED and not derivable: three or "
                "more phases, where the deficit is split")
    r = rho_alab({"rwp_manual": rwp, "target_pct": wt, "max_impurity_pct": wa})
    return r, wt, rwp, wa, prov


_K6_KEY_CACHE: dict = {}


def _k6_deposit_principal(compound: str, stage: str):
    """Is the claimed compound the principal product on the DEPOSIT's row?

    The same rule the layer is scored by, applied to the deposited refinement
    at a stated stage. This is the achievable line: what the comparison
    recovers from the evidence itself, so the layer's score can be read
    against what the evidence supports rather than against a different rule.
    """
    try:
        import bench_shim
        row = bench_shim.refinement_row(compound, stage=stage)
        wt, alts = 0.0, []
        for ph in (row.get("phases") or []):
            v = ph.get("wt_pct")
            if not isinstance(v, (int, float)):
                continue
            # BY COMPOSITION, NEVER BY PRINTED NAME. The deposit spells one
            # compound's own phase `Ba6Na2Ta2V2O17` where the claim spells it
            # `Ba6Ta2Na2V2O17` - two elements transposed. A string compare
            # finds no target, counts the target's own 63.38 per cent as an
            # impurity, and computes 1.3489 where the key says 0.7651.
            if _key(str(ph.get("formula_core") or "")) == _key(compound):
                wt += float(v)
            else:
                alts.append(float(v))
        if not (row.get("phases") or []):
            return None
        return wt < (max(alts) if alts else 0.0)   # True = NOT principal = flag
    except Exception:
        return None


def _k6_deposit_rho(compound: str, stage: str):
    """The baseline's rule on the DEPOSIT's row at a stated stage.

    Rows of the same composition are SUMMED, not overwritten. Zn3Ni4(SbO6)2
    deposits its target twice - `..._Alab` at 55.18 and `..._ICSD109468` at
    21.02 - and keeping the last match reports a 21.02 per cent target on a
    specimen that is 76.20 per cent target.
    """
    ck = (compound, stage)
    if ck in _K6_KEY_CACHE:
        return _K6_KEY_CACHE[ck]
    try:
        import bench_shim
        from reproduce_baselines import rho_alab
        row = bench_shim.refinement_row(compound, stage=stage)
        wt, alts = 0.0, []
        for ph in (row.get("phases") or []):
            v = ph.get("wt_pct")
            if not isinstance(v, (int, float)):
                continue
            # BY COMPOSITION, NEVER BY PRINTED NAME. The deposit spells one
            # compound's own phase `Ba6Na2Ta2V2O17` where the claim spells it
            # `Ba6Ta2Na2V2O17` - two elements transposed. A string compare
            # finds no target, counts the target's own 63.38 per cent as an
            # impurity, and computes 1.3489 where the key says 0.7651.
            if _key(str(ph.get("formula_core") or "")) == _key(compound):
                wt += float(v)
            else:
                alts.append(float(v))
        out = rho_alab({"rwp_manual": row.get("rwp"),
                        "target_pct": wt if wt else None,
                        "max_impurity_pct": max(alts) if alts else 0.0})
    except Exception:
        out = None
    _K6_KEY_CACHE[ck] = out
    return out


K6_THRESHOLD = 0.776   # CARTOGRAPH's frozen calibration constant


# The modality stage two supplies. docs/ENTRANT.md names it; asking for it is
# how a submission earns the released refinement row.
STAGE_TWO_MODALITY = "re-refinement-expanded-phase-set"


def _declared_stage(children: list[dict]) -> str:
    """"one" or "two", read from what the submission declares.

    A pass is stage two when it asked for the analysis stage two supplies, or
    when it carries the released file. Both are things the submitter wrote
    down and the harness can check against the follow-up menu - unlike a
    filename, which is free text nobody adjudicates.
    """
    for r in children:
        if STAGE_TWO_MODALITY in (r.get("follow_up") or ""):
            return "two"
        if (r.get("stage_two_file") or "").strip():
            return "two"
    return "one"


def score(children_path: Path,
          stage_override: str | None = None) -> tuple[list[dict], dict]:
    children = _rows(children_path, skip_comments=False)
    ledger_path = Path(str(children_path).replace("children_rebuilt_",
                                                  "ledger_rebuilt_"))
    if not ledger_path.exists():
        raise SystemExit(
            f"need the ledger beside the children file to score flags "
            f"honestly; expected {ledger_path}")
    ledger = _rows(ledger_path, skip_comments=False)
    if not _NORM_OK:
        raise SystemExit(
            "REFUSING TO SCORE: pymatgen is unavailable, so compound names "
            "cannot be joined by composition.\n"
            "Falling back to string joins would silently drop every target "
            "whose formula is spelled with its\n"
            "elements in a different order - the defect this scorer was "
            "repaired for on 28 Aug 2026 - and would\n"
            "report a plausible number while doing it. Install the pinned "
            "environment and re-run.")
    # THE STAGE COMES FROM THE SUBMISSION, NEVER FROM ITS FILENAME.
    #
    # This read `"stage2" in children_path.name`. A stage-two pass scores K6
    # and nothing else, so an entrant chose which group they were scored on by
    # naming a file - the submitter picking their own denominator, which is the
    # one thing a scorebook may not let them do. The stage is a property of
    # what was submitted: stage two is EARNED by requesting the modality it
    # supplies, and a pass that requested it is scored on K6 alone. A harness
    # that already knows may state it outright; nothing infers it from a name.
    stage = stage_override or _declared_stage(children)
    obs = _observations(children)
    k6recs = _k6_records(children)
    elicited = _elicited(children)
    flagged = _flagged(children, ledger)
    refuting = _refuting_families(children)
    per_child = _per_child_verdicts(children)

    results = []
    for t in build_targets(stage=stage):
        reach = REACHES.get(t["quantity"], ())
        was_elicited = any((t["key"], fam) in elicited for fam in reach)
        row = {**t, "observed": None, "outcome": NOT_ELICITED,
               "note": ""}

        if not was_elicited:
            row["note"] = ("no check in a family that could reach this target "
                           "was elicited for this compound")
            results.append(row)
            continue

        if t["group"] == "K6":
            lr, wt, rwp, wa, prov = _k6_layer_rho(obs, t["key"], k6recs)
            if lr is None:
                row["outcome"] = NOT_OBSERVED
                row["note"] = ("the layer recorded no usable "
                               "target_weight_fraction_pct / fit_residual_rwp "
                               f"pair for this compound ({prov})")
                results.append(row)
                continue
            # THE GROUP SCORES ON RHO, THE RULE THE KEY WAS BUILT FROM.
            #
            # Corrected 29 August 2026. This decided K6 on the threshold-free
            # comparison - is the claimed compound the largest phase - and
            # filed rho into a field nothing read. The two rules do not agree:
            # the comparison recovers 7 of 8 at stage two where rho recovers
            # 8 of 8, and 8 of 8 is the published figure.
            #
            # KBaPrWO6 is the compound that separates them, and it shows why
            # this is not a matter of taste. It crosses the threshold on the
            # NORM without any single term crossing: Rwp 10.75, target 50.42,
            # largest impurity 29.68, giving 0.7892 against 0.776. No
            # comparison between two of those three quantities can see it.
            #
            # Both rules are kept and both are reported, because they are two
            # jobs. rho is what the GROUP SCORES, because the answer key was
            # computed from it and a group must be scored by the rule its key
            # was built from. The comparison is what the LAYER SHOULD ASSERT -
            # it is entailed by the parent, carries no invented threshold, and
            # cannot be misread by a factor of a hundred - so it travels
            # beside the score rather than deciding it.
            principal = (wa is not None and wt is not None and wt >= wa)
            row["observed"] = (lr > K6_THRESHOLD)
            row["k6_comparison_says"] = (not principal)
            row["outcome"] = (RECOVERED if row["observed"] == bool(t["expected"])
                              else MISSED)
            row["note"] = (f"layer rho={lr:.4f} from its own w_target={wt}, "
                           f"Rwp={rwp}, w_alt={wa} ({prov}); "
                           f"threshold {K6_THRESHOLD}")
            row["k6_layer_rho"] = lr
            results.append(row)
            continue

        if t["quantity"] in EVIDENCE_FAMILIES:
            # TWO conditions, and both are required.
            #
            #  1. the compound's LEDGER verdict is refuted - so the refutation
            #     survived aggregation's fail-closed rules: witness validated,
            #     entailment respected, downgrades applied. Reading raw check
            #     status here would walk past all of that.
            #  2. at least one refuting check came from a family that carries
            #     THIS target's evidence. A file-contradiction refutation does
            #     not establish "already known", and a database-match
            #     refutation does not establish "the file differs".
            fams = refuting.get(t["key"], set())
            # PER-TARGET first, group rule second. See EVIDENCE_OVERRIDES.
            accepted = EVIDENCE_OVERRIDES.get(
                (t["quantity"], t["compound"]),
                EVIDENCE_FAMILIES[t["quantity"]])
            # the verdict of THIS TARGET'S OWN checks - never the compound's
            # aggregated bit. See _per_child_verdicts.
            mine = [per_child.get((t["key"], f)) for f in accepted]
            mine = [v for v in mine if v]
            best = max(mine, key=lambda v: {"True": 3, "UNADJUDICABLE": 2,
                                            "NO-FILE": 1, "False": 0}.get(v, -1),
                       default="")
            if best == "" and (t["key"], "") not in per_child and not mine \
                    and not any((t["key"], f) in per_child for f in accepted):
                # no per-child column at all (a ledger written before 28 Aug
                # 2026): fall back to the aggregated bit, and say so
                has_evidence = bool(fams & set(accepted))
                row["observed"] = (t["key"] in flagged) and has_evidence
                row["note"] = ("scored from the COMPOUND-LEVEL verdict; this "
                               "ledger predates per-child witness validation")
            else:
                row["observed"] = (best == "True")
            row["outcome"] = (RECOVERED if row["observed"] == bool(t["expected"])
                              else MISSED)
            if best == "UNADJUDICABLE" and bool(t["expected"]):
                row["outcome"] = UNVALIDATED
            row["note"] = (f"refuting families: {sorted(fams) or 'none'}; "
                           f"evidence families for this target: "
                           f"{list(accepted)}")

            # REACHED, BUT THE LAYER CANNOT VALIDATE IT. A check refuted using
            # this target's OWN evidence class, and that class is one the
            # standalone checker structurally cannot read - it is stdlib-only
            # and opens the deposited file and nothing else. Aggregation fails
            # closed, correctly, so the compound reads cannot_verify.
            #
            # Scoring that MISSED says the arm got it wrong. It did not: it
            # reached the finding and the instrument could not check the
            # answer. Across the four generation-2 arms there are 79 novelty
            # refutations and not one of them can ever be validated, so this
            # is a standing property of the layer rather than an accident.
            if (row["outcome"] == MISSED and bool(t["expected"])
                    and (fams & set(accepted))
                    and not (set(accepted) & set(CHECKER_CAN_ADJUDICATE))):
                row["outcome"] = UNVALIDATED
                row["note"] = (
                    f"REACHED: a check in {sorted(fams & set(accepted))} "
                    f"refuted on this target's own evidence class. The "
                    f"standalone checker reads only the deposited file and "
                    f"cannot adjudicate that class, so aggregation downgraded "
                    f"it. Not a miss - the layer could not validate it")
            results.append(row)
            continue

        # ALTERNATES: one determination, two ways of writing it. A verifier
        # that reports "P6_3/m" has recorded exactly the same fact as one that
        # reports 176, and scoring the first NOT-OBSERVED would penalise
        # notation rather than measurement.
        values = list(obs.get((t["key"], t["quantity"])) or [])
        for alt in ALTERNATES.get(t["quantity"], ()):
            values += list(obs.get((t["key"], alt)) or [])
        if not values:
            row["outcome"] = NOT_OBSERVED
            row["note"] = ("a check ran but recorded no observation of this "
                           "quantity; the observation channel postdates this "
                           "elicitation")
            results.append(row)
            continue

        tol = TOL.get(t["quantity"], 0)

        # K4 IS SCORED ON A DECLARED CONVERSION, NOT ON CONSENSUS (28 Aug 2026).
        #
        # The pseudo-cubic parameter of a non-cubic crystal is an
        # approximation, and more than one route to it is legitimate. Measured
        # on these five: the routes disagree by 0.0082 to 0.0516 A - 16x to
        # 103x the 0.0005 A tolerance - and the critique itself used `c` on
        # Zr2Sb2Pb4O13 and mean(a,b)*sqrt2 on the structurally near-identical
        # Hf2Sb2Pb4O13. No rule derivable from the deposited file reproduces
        # that row-by-row choice.
        #
        # So requiring the arm's PLURALITY answer to match the critique's row
        # choice scores convention-guessing, not measurement. The ceiling
        # already refuses to do this for K2, on the same grounds: "no pass or
        # fail is stamped on a symmetry comparison ... declaring one of two
        # independent programs correct is a judgement this layer does not
        # make."
        #
        # THE GUARD AGAINST ENUMERATION. A value counts only if it is a
        # CORRECTLY COMPUTED standard conversion of this compound's own
        # deposited cell. A scatter of guesses cannot satisfy that: verified on
        # opus5, every one of its five matching values is an exact standard
        # conversion, and three of its plurality values are the bare cell edge
        # `a` and therefore count for nothing here.
        #
        # The number of attempts is printed beside the score, because an arm
        # with fifteen checks per compound and one with a single check are not
        # comparable on this rule without it.
        if t["quantity"] == "cubic_lattice_parameter_a":
            conv = _pseudocubic_routes(t["compound"])
            if conv:
                real = [v for v in values
                        if any(abs(float(v) - rv) <= tol for rv in conv.values()
                               if isinstance(v, (int, float)) or _isnum(v))]
                hit = any(abs(float(v) - float(t["expected"])) <= tol
                          for v in real if _isnum(v))
                row["observed"] = (f"{len(real)} of {len(values)} recorded "
                                   f"values are standard conversions")
                row["outcome"] = RECOVERED if hit else MISSED
                row["note"] = (f"scored on a correctly computed standard "
                               f"conversion, not on consensus; "
                               f"{len(values)} attempt(s)")
                results.append(row)
                continue

        def _matches(v) -> bool:
            try:
                return abs(float(v) - float(t["expected"])) <= tol
            except (TypeError, ValueError):
                # a symbol reported against a numeric target: resolve the
                # symbol to its International Tables number rather than
                # comparing strings, which would never match
                if str(v).strip() == str(t["expected"]).strip():
                    return True
                if t["quantity"] == "space_group_number":
                    return _sg_symbol_to_number(v) == int(t["expected"])
                return False

        # SCORE THE ARM'S OWN CONSENSUS, NEVER ANY-OF (28 Aug 2026).
        #
        # This credited a target if ANY recorded value fell inside tolerance.
        # A compound has up to sixteen children, each free to record the same
        # quantity, so the rule paid out on a scatter of guesses.
        #
        # Measured on opus5 generation 2, cubic_lattice_parameter_a: 36 of 40
        # compounds recorded MORE THAN ONE distinct value, up to ten distinct
        # values from fifteen children. K4 scored 5 of 5 under any-of and
        # 1 of 5 on the arm's own modal value. The 5 was the rule, not the arm.
        #
        # This is the enumeration attack that docs/ENTRANT.md §7a declares
        # against an entrant, found operating inside our own scorebook against
        # our own headline number. An entrant submits one value per quantity
        # and was being compared against an arm allowed sixteen.
        #
        # The rule is now the MODE: the value the arm's own checks most agree
        # on. That is what the verifier concluded, as opposed to what it
        # happened to emit somewhere. A tie has no consensus and cannot be
        # resolved in the arm's favour, so it scores MISSED and says so.
        # `space_group_number` is unaffected - zero compounds recorded more
        # than one distinct value - which is itself worth knowing: the spread
        # is a property of the quantity, not of the channel.
        def _canon(v) -> str:
            """One key per DETERMINATION, not per spelling.

            The alternates rule merges `space_group_symbol` into the same list
            as `space_group_number`, so a compound reporting both 194 and
            'P6_3/mmc' has recorded ONE determination written two ways. Keying
            the mode on the raw strings made those two rivals, tied the vote,
            and scored a unanimous arm as having no consensus - which is the
            join-by-printed-name defect a third time, in the aggregation this
            time rather than the join.
            """
            s = str(v).strip()
            if t["quantity"] == "space_group_number":
                n = None
                try:
                    n = int(float(s))
                except (TypeError, ValueError):
                    n = _sg_symbol_to_number(s)
                if n:
                    return str(n)
            try:
                f = float(s)
                return f"{f:.6g}"
            except (TypeError, ValueError):
                return s

        from collections import Counter as _C
        keyed = _C(_canon(v) for v in values)
        top = keyed.most_common()
        tied = len(top) > 1 and top[0][1] == top[1][1]
        consensus = top[0][0]
        hit = (not tied) and _matches(consensus)

        row["observed"] = consensus if len(keyed) == 1 else \
            f"{consensus} (mode of {len(keyed)} distinct in {len(values)})"
        row["outcome"] = RECOVERED if hit else MISSED
        notes = []
        if tol:
            notes.append(f"tolerance {tol}")
        if len(keyed) > 1:
            any_of = any(_matches(v) for v in values)
            notes.append(
                f"{len(keyed)} distinct values across {len(values)} checks; "
                f"scored on the mode"
                + ("; TIED, no consensus" if tied else "")
                + ("; NOTE a lenient any-of rule would have scored this "
                   "RECOVERED" if any_of and not hit else ""))
        row["note"] = "; ".join(notes)
        row["dispersed"] = len(keyed) > 1
        results.append(row)

    # JOIN COVERAGE. A target whose key matches no compound anywhere in the
    # ledger is a different failure from a target whose checks were never
    # bought, and the two are indistinguishable in the outcome column. Fixing
    # the join once did not stop it recurring, so the scorer now watches for
    # it: any target the ledger cannot see at all is named in the report.
    ledger_keys = {_key(r["compound"]) for r in children}
    for r in results:
        if r["outcome"] == NOT_ELICITED and r["key"] not in ledger_keys:
            r["unjoined"] = True

    by_group: dict = {}
    for r in results:
        by_group.setdefault(r["group"], Counter())[r["outcome"]] += 1
    # THE FLAGGED SET TRAVELS WITH THE SCORE. A flag group's targets are only
    # the compounds an expert flagged, so recoveries alone cannot show what a
    # submission raised on the compounds nobody flagged. docs/ENTRANT.md 5
    # promises those are counted and reported beside the recoveries; without
    # this they were reported for the external baseline and nowhere else.
    return results, by_group, flagged


def baseline_comparison(flagged: set) -> dict | None:
    """Agreement with the external baseline, computed from BOTH flag sets.

    NOT A TARGET GROUP, and not scored per compound against an expectation.
    Three reasons it cannot be one, the last decisive:

     1. GRANULARITY. The baseline emits one decision per compound; this layer
        emits a verdict per claim. There is nothing per-claim on its side, so
        every attempt to score it collapsed back to the aggregated compound
        bit - which is where it kept colliding with K1 and K3.
     2. DIFFERENT QUESTION. The critique asks whether the deposited file
        matches the claim; the baseline asks whether the fit is poor. On six
        compounds K1 expects a flag and the baseline passes. One flag slot
        cannot answer both, so scoring both against it guaranteed a miss.
     3. STAGE. rho is computed from rwp_manual and the manual phase fractions.
        For Ba2ZrSnO6 the target fraction is 91.12 per cent at stage one and
        22.0 at stage two. A stage-one verifier cannot compute this decision,
        and neither can our own arms.

    So it is reported as a set comparison: what both flag, what only one flags,
    and the score a verifier gets by flagging nothing. No expectation is
    attached to any compound, so nothing can be "missed".
    """
    base = LABELS / "cartograph_decisions.csv"
    if not base.exists():
        return None
    rows = _rows(base)
    theirs = {_key(r["compound"]) for r in rows
              if r["flagged"].strip().lower() == "true"}
    pop = {_key(r["compound"]) for r in rows}
    ours = set(flagged) & pop
    return {"population": len(pop), "they_flag": len(theirs),
            "we_flag": len(ours), "both": len(ours & theirs),
            "only_them": sorted(theirs - ours), "only_us": sorted(ours - theirs),
            "do_nothing_agreement": len(pop - theirs)}


# ----------------------------------------------------------------- the report

# The K vocabulary, matching docs/ceiling.md. The groups were briefly named
# A1-A4 after the old tier scheme; renamed 28 Aug 2026 so the code and the
# ceiling document use one set of names.
GROUP_TITLE = {
    "K1": "the deposited file differs from the claim (E2)",
    "K2": "the symmetry of each deposited file",
    "K3": "the product was already known (E4)",
    "K4": "the cubic lattice parameter from each A-Lab CIF",
    "K5": "per-compound structural statements in the critique's prose",
    # K6 IS A CEILING GROUP AGAIN, SCOPED TO STAGE TWO (28 Aug 2026).
    #
    # It was labelled "NOT A CEILING GROUP", which read as demoted for quality
    # when the truth is scoped for evidence. Two grounds were given and only
    # one holds.
    #
    # The weak ground: a blind check cannot derive the baseline's statistic or
    # its 0.776 threshold. True, and not disqualifying - K2 asks a verifier to
    # reproduce a determination two defensible programs disagree about, and the
    # ceiling handles it by refusing to stamp pass or fail and letting the
    # margin travel. K6 gets the same treatment; the compound sitting 0.011
    # from the threshold is named, not counted against anyone.
    #
    # The hard ground, which stands: its inputs are the MANUAL refinement
    # columns. Measured across the 40 - the target weight fraction differs
    # between stages by a median of 9.2 points, a maximum of 74.4, and by more
    # than 10 points on 18 of 38 compounds. Mg3MnNi3O8 reads 100.00 at stage
    # one and 25.62 at stage two. A stage-one verifier computing this
    # statistic is not reproducing the baseline's decision, it is computing a
    # different number from different inputs.
    #
    # So K6 belongs to the ceiling and is scoreable only at stage two. It is
    # counted SEPARATELY from the 55 stage-one targets and never pooled with
    # them. It is currently unscored not because of its status but because no
    # stage-two release has ever fired: 734 requests across four arms, four for
    # the modality stage two supplies.
    "K6": "the two-stage protocol, end to end - STAGE TWO ONLY",
    # SUPERSEDED, kept because the argument is the useful part. This block used
    # to read "NOT a ceiling group. Demoted 28 Aug 2026", directly below a
    # title calling it a ceiling group, and the two stood in the file
    # contradicting each other. The demotion's ground was that a blind check
    # cannot derive the baseline's statistic or its frozen threshold from the
    # deposit. That ground was withdrawn: K2 asks a verifier to reproduce a
    # determination two defensible programs disagree about, and the ceiling
    # handles it by refusing to stamp pass or fail and letting the margin
    # travel. K6 gets the same treatment - the compound sitting 0.011 from the
    # threshold is named, not counted against anyone.
    #
    # What replaced it is not a rehabilitation of the old framing but a
    # different reading of what the group measures. K6 is not a reproduction of
    # another automated system. It is the end-to-end test of the two-stage
    # protocol: the layer works on stage-one evidence, abstains, NAMES the
    # analysis that would settle the question, is granted it, and is scored on
    # whether it then reaches the baseline's decision. CARTOGRAPH's pass/flag
    # is the external key for that last step.
}


def report(children_path: Path, show_targets: bool = False,
           stage_override: str | None = None) -> int:
    results, by_group, flagged = score(children_path,
                                       stage_override=stage_override)
    print(f"\nPER-TARGET SCOREBOOK [{BENCHMARK_VERSION}] - "
          f"{children_path.parent.name}/{children_path.name}")
    print("  one score per benchmark item; group denominators are never "
          "pooled")
    print("  K6 is scored only where its stage-two evidence exists\n")

    for g in sorted(by_group, key=lambda x: (x[0] != "K", x)):
        c = by_group[g]
        scoreable = c[RECOVERED] + c[MISSED]
        total = sum(c.values())
        attempted = total - c[NOT_ELICITED]
        print(f"  {g}  {GROUP_TITLE.get(g, '')}")
        print(f"      {total} targets in the benchmark"
              f" | recovered {c[RECOVERED]}"
              f" | missed {c[MISSED]}"
              + (f" | UNVALIDATED {c[UNVALIDATED]}" if c[UNVALIDATED] else "")
              + f" | not observed {c[NOT_OBSERVED]}"
              f" | not attempted {c[NOT_ELICITED]}")
        # THE DENOMINATOR IS THE BENCHMARK'S, NOT THE SUBMITTER'S.
        #
        # This used to print "X of (recovered+missed)", which let anyone
        # choosing what to attempt choose their own scale: a verifier that
        # answered the six easy compounds and skipped the seventh reported
        # 6 of 6 while one that attempted all seven and missed the hard one
        # reported 6 of 7. Identical work, and the one that declined the hard
        # case looked better.
        #
        # The primary figure is now against the full target count. Coverage is
        # printed beside it, in the same block, because a score and the share
        # of the group it was computed over are not separable numbers.
        # A GROUP THAT SPLITS DOES NOT ALSO PRINT A COMBINED FIGURE.
        # K2's whole reason for splitting is that the combined number can be
        # earned by echoing the claim: 39 of its 43 rows have the critique's
        # determination equal to the claimed space group. Printing "recovered
        # 37 of 43 (86%)" five lines above "these two are never summed"
        # reinstates precisely the number the split exists to eliminate, and
        # it is the line a reader quotes.
        # FALSE ALARMS, BESIDE THE RECOVERIES AND NEVER NETTED AGAINST THEM.
        #
        # A flag group's targets are only the compounds an expert flagged, so
        # K1 has 7 targets over a population of 40. A submission that refutes
        # every compound recovers all 7 and the block said "7 of 7" - its 33
        # flags on compounds no expert flagged appeared nowhere, because they
        # correspond to no target. That is the always-refute strategy reading
        # as a perfect score, and docs/ENTRANT.md 5 already promised these were
        # counted. They are printed, named, and never subtracted from anything:
        # a recovery and a false alarm are different events and an aggregate
        # trading one against the other is the thing this benchmark refuses.
        grp_rows = [r for r in results if r["group"] == g]
        if grp_rows and all(r.get("quantity") in EVIDENCE_FAMILIES
                            for r in grp_rows) and g != "K6":
            expected = {_key(r["compound"]) for r in grp_rows}
            fa = sorted(flagged - expected)
            print(f"      false alarms: {len(fa)} compound(s) flagged that no "
                  f"expert flagged in this group")
            if fa:
                print(f"        {', '.join(fa)}")
                print(f"      never netted against the recoveries above: "
                      f"flagging everything recovers every")
                print(f"      target in this group and is not a verification "
                      f"result.")

        if g not in SPLIT_GROUPS:
            print(f"      recovered {c[RECOVERED]} of {total} "
                  f"({100 * c[RECOVERED] / total:.0f}% of the benchmark's "
                  f"targets)")
            if c[UNVALIDATED]:
                print(f"      REACHED but not validated on this run: "
                      f"{c[UNVALIDATED]}. A check refuted on this target's own")
                print(f"      evidence class; the standalone checker reads "
                      f"only the deposited file and cannot")
                print(f"      adjudicate that class, so aggregation downgraded "
                      f"it. This is NOT a miss.")
                print(f"      reached {c[RECOVERED] + c[UNVALIDATED]} of "
                      f"{total} | validated {c[RECOVERED]} of {total} "
                      f"- never one figure")
        print(f"      attempted {attempted} of {total} "
              f"({100 * attempted / total:.0f}%) - two submissions are "
              f"comparable only at equal coverage")
        # A target the ledger cannot see AT ALL is either outside this
        # arm's population or a join failure. Neither is the verifier's
        # omission, and both depress coverage, so they are named. The list is
        # also the regression watch on the join itself: the composition key
        # makes a permuted spelling impossible here, so if this count moves,
        # the key stopped working.
        unjoined = [r for r in results
                    if r["group"] == g and r.get("unjoined")]
        if unjoined:
            print(f"      {len(unjoined)} target(s) match no compound "
                  f"anywhere in this ledger:")
            for r in unjoined:
                print(f"        {r['id']}  (key {r['key']!r})")
            print(f"      Either the compound is outside this ledger's "
                  f"population, or the join failed. Both")
            print(f"      depress coverage for reasons that are not the "
                  f"verifier's, so they are named rather")
            print(f"      than absorbed. Since 28 Aug both sides join on the "
                  f"composition-reduced formula,")
            print(f"      so a permuted spelling can no longer appear here - "
                  f"a jump in this count is a")
            print(f"      regression in the join, not a change in the arm.")
        if True:
            # FLAG GROUPS ARE NEVER REPORTED AS ONE PERCENTAGE. A group whose
            # targets are mostly "expected: not flagged" can be scored highly
            # by a layer that flags nothing, so a single figure measures the
            # base rate rather than the method. Measured on the external
            # baseline group: an arm refuting NOTHING scores 80 per cent, and
            # every arm scored so far comes in below that. The split, and the
            # do-nothing line, are printed instead.
            pos = [r for r in results
                   if r["group"] == g and bool(r.get("expected")) is True
                   and r["outcome"] in (RECOVERED, MISSED)]
            neg = [r for r in results
                   if r["group"] == g and bool(r.get("expected")) is False
                   and r["outcome"] in (RECOVERED, MISSED)]
            if neg:
                hp = sum(1 for r in pos if r["outcome"] == RECOVERED)
                hn = sum(1 for r in neg if r["outcome"] == RECOVERED)
                print(f"      agreed where the source ASSERTS  : "
                      f"{hp} of {len(pos)}")
                print(f"      agreed where the source does NOT : "
                      f"{hn} of {len(neg)}")
                print(f"      NO SINGLE FIGURE for this group: a layer that "
                      f"asserted nothing would")
                print(f"      score {len(neg)} of {len(pos) + len(neg)} "
                      f"({100 * len(neg) / (len(pos) + len(neg)):.0f}%) "
                      f"without doing anything.")
            elif scoreable and g not in SPLIT_GROUPS:
                # split groups are reported only as their split; any combined
                # line here is the same earnable-by-echoing number wearing
                # different words
                print(f"      of the {scoreable} it both attempted and "
                      f"recorded, {c[RECOVERED]} matched")

        if g == "K6":
            # THE SECOND KEY, REPORTED BESIDE THE FIRST AND NEVER POOLED.
            #
            # The published key is computed from the STAGE-TWO manual columns.
            # Every check scored above read STAGE ONE. So the figure printed
            # above answers "did the layer reproduce the published decision",
            # which a stage-one verifier cannot do, and the figure below
            # answers "did it reproduce the baseline's METHOD on the evidence
            # it actually held". Both are real questions and they have
            # different denominators, so neither is quoted for the other.
            k6 = [r for r in results if r["group"] == "K6"
                  and r.get("k6_layer_rho") is not None]
            tp = fn = fp = tn = 0
            for r in k6:
                key = _k6_deposit_principal(r["compound"], "one")
                if key is None:
                    continue
                pred = bool(r["observed"])
                if key and pred: tp += 1
                elif key and not pred: fn += 1
                elif pred: fp += 1
                else: tn += 1
            if tp + fn + fp + tn:
                n = tp + fn + fp + tn
                print(f"      --- the same layer decisions against a "
                      f"STAGE-ONE key ({n} compounds)")
                print(f"      the SAME comparison on the deposited row, "
                      f"stage one - the achievable line:")
                print(f"        agreed where that key ASSERTS  : {tp} of {tp + fn}")
                print(f"        agreed where it does NOT       : {tn} of {tn + fp}")
                print(f"        a layer asserting nothing would score "
                      f"{tn + fp} of {n} ({100 * (tn + fp) / n:.0f}%)")
                print(f"      NEVER POOLED with the figure above: different "
                      f"key, different denominator.")

        if g == "K2":
            # THE ECHO SPLIT. On 39 of 43 rows the critique's determination
            # equals the claimed space group, so a verifier that copied the
            # claim it was handed - never opening the deposited file - scores
            # those 39. Value targets carry no witness requirement, so nothing
            # else catches that.
            #
            # The 39 are not discarded: recovering an agreement IS a
            # reproduction, and the file has to be read to know it agrees. But
            # only the 4 rows where the determination DIFFERS from the claim
            # can distinguish a verifier that read the file from one that
            # echoed it, so the two are reported apart and never summed.
            grp = [r for r in results if r["group"] == "K2"]
            for label, subset in (
                    ("where the determination equals the claim (echo-level)",
                     [r for r in grp if r.get("echo_level")]),
                    ("where it DIFFERS from the claim (requires the file)",
                     [r for r in grp if r.get("differs_from_claim")])):
                # against the FULL subset, not the scoreable part of it. The
                # denominator is the benchmark's everywhere else; reporting
                # "37 of 37 scoreable" here let the same skipping that the
                # denominator fix removed come back through a side door.
                got = sum(1 for r in subset if r["outcome"] == RECOVERED)
                att = sum(1 for r in subset
                          if r["outcome"] != NOT_ELICITED)
                print(f"      {label}")
                print(f"        {got} of {len(subset)}"
                      f"   (attempted {att})")
            print(f"      these two are never summed: a verifier echoing the "
                  f"claimed space group")
            print(f"      scores the first and nothing in the second.")
        if c[NOT_OBSERVED]:
            print(f"      {c[NOT_OBSERVED]} target(s) were attempted but "
                  f"recorded no observation of the quantity.")
            print(f"      Reported separately, never as misses: 'reached a "
                  f"different answer' and 'did not")
            print(f"      record it' are different outcomes and pooling them "
                  f"would flatter the verifier.")
        print()

    bc = baseline_comparison(_flagged(_rows(children_path, skip_comments=False),
                                      _rows(Path(str(children_path).replace(
                                          "children_rebuilt_", "ledger_rebuilt_")),
                                          skip_comments=False)))
    if bc:
        print("  EXTERNAL BASELINE - a comparison, not a target group")
        print(f"      over {bc['population']} compounds: they flag "
              f"{bc['they_flag']}, this verifier flags {bc['we_flag']}, "
              f"both flag {bc['both']}")
        if bc["only_them"]:
            print(f"      only they flag : {', '.join(bc['only_them'])}")
        if bc["only_us"]:
            print(f"      only we flag   : {', '.join(bc['only_us'])}")
        print(f"      no compound carries an expectation here, so nothing "
              f"can be missed. A verifier")
        print(f"      flagging NOTHING would agree on "
              f"{bc['do_nothing_agreement']} of {bc['population']}, which is "
              f"why no rate is printed.")
        print()

    print("  NO SINGLE NUMBER IS PRINTED. The groups answer different "
          "questions against")
    print("  different expert denominators, and one figure over all of them "
          "would quote a")
    print("  count from one population against another's denominator.\n")

    if show_targets:
        print(f"  {'target':34s} {'outcome':13s} {'expected':22s} observed")
        for r in results:
            o = "" if r["observed"] is None else str(r["observed"])[:24]
            print(f"  {r['id'][:34]:34s} {r['outcome']:13s} "
                  f"{str(r['expected_display'])[:22]:22s} {o}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Per-target scorebook: one score per benchmark item.")
    ap.add_argument("children", help="a children_*.csv from rebuild_ledger")
    ap.add_argument("--targets", action="store_true",
                    help="print every individual target and its outcome")
    ap.add_argument("--stage", choices=("one", "two"), default=None,
                    help="state the stage outright, for a harness that already "
                         "knows. Omitted, it is read from what the submission "
                         "declares - never from the filename.")
    a = ap.parse_args()
    return report(Path(a.children), show_targets=a.targets,
                  stage_override=a.stage)


if __name__ == "__main__":
    raise SystemExit(main())

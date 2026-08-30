"""
BUILD THE ANSWER KEYS. The only writer for data/labels/ceiling.json and
data/labels/cartograph_decisions.csv.

Why this exists. Both files carried the header "Computed by
bench/score_targets.py". They were not: `score_targets` only ever reads them, and
they were produced by inline scripts that were never committed. A provenance
claim with no writer behind it is a lie in the file header, and it had already
cost something concrete - the baseline key drifted out of step with
`reproduce_baselines.py` for a day, because the statistic was written out again
by hand instead of being called.

So: one writer, one code path, a hash of the inputs stamped into the output,
and `score_targets` refuses to run against a key older than its inputs.

Usage:
    .venv/bin/python tools/build_ceiling.py            # write both
    .venv/bin/python tools/build_ceiling.py --check    # verify, write nothing
"""

from __future__ import annotations

import argparse
import collections
import csv
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "bench"))
LABELS = ROOT / "data" / "labels"

CARTOGRAPH_THRESHOLD = 0.776          # their frozen calibration, not ours

# Every file the keys are derived from. Their combined hash is stamped into
# each output, so a key that predates a change to its inputs is detectable
# rather than merely suspected.
INPUTS = ["merged_labels.csv", "prx_table3.csv", "prx_table2.csv",
          "prx_prose_claims.csv"]


def input_digest() -> str:
    h = hashlib.sha256()
    for name in INPUTS:
        p = LABELS / name
        h.update(name.encode())
        h.update(p.read_bytes() if p.exists() else b"ABSENT")
    return h.hexdigest()[:16]


def build_cartograph() -> tuple[list[dict], dict]:
    """The baseline's pass/flag decision per claim.

    Computed by CALLING `reproduce_baselines.rho_alab`, never by restating the
    formula. That function is what reproduces the published result exactly, and
    the whole point is that the answer key and the reproduction are one code
    path. `w_alt` is the LARGEST SINGLE IMPURITY FRACTION; writing the formula
    out again is how it once became `100 - w_target` instead.
    """
    from reproduce_baselines import phase_fractions, rho_alab
    frac = phase_fractions()
    rows = []
    for r in csv.DictReader((LABELS / "merged_labels.csv").open()):
        if r["correction_verdict"] not in ("confirmed", "inconclusive"):
            continue
        rho = rho_alab(frac.get(r["compound"], {}))
        if rho is None:
            continue
        rows.append({"compound": r["compound"],
                     "correction_verdict": r["correction_verdict"],
                     "rho": round(rho, 4),
                     "flagged": str(rho > CARTOGRAPH_THRESHOLD)})
    flagged = sum(1 for x in rows if x["flagged"] == "True")
    return rows, {"rows": len(rows), "flagged": flagged,
                  "passed": len(rows) - flagged,
                  "do_nothing_score_pct": round(
                      100 * (len(rows) - flagged) / len(rows), 1)}


def write_cartograph(rows: list[dict], stats: dict, digest: str) -> None:
    out = LABELS / "cartograph_decisions.csv"
    with out.open("w") as fh:
        fh.write(f"""# CARTOGRAPH's pass/flag decision per claim, at their frozen threshold {CARTOGRAPH_THRESHOLD}.
#
#   rho = sqrt( (Rwp/20)^2 + ((100 - w_target)/100)^2 + (w_alt/100)^2 )
#
# w_alt is the LARGEST SINGLE IMPURITY PHASE FRACTION. It is NOT 100 - w_target.
#
# GENERATED FILE. Written only by tools/build_ceiling.py, which computes these
# by calling reproduce_baselines.rho_alab - the same function that reproduces
# the published result exactly. Do not edit by hand: the header would stop
# being true, which is what happened between 27 and 28 August 2026 when the
# statistic was written out again and w_alt became 100 - w_target. That flagged
# 9 compounds instead of 8 and voided every number computed from it.
#
# input_digest: {digest}
# rows {stats['rows']}, flagged {stats['flagged']}, passed {stats['passed']}
# A verifier that flagged nothing would agree on {stats['passed']} of {stats['rows']}
# ({stats['do_nothing_score_pct']} per cent). No single figure is reported for this group.
#
# THESE ARE THE BASELINE'S DECISIONS, NOT EXPERT FINDINGS. They are the external
# key for the last step of K6, the two-stage protocol test - not a rival score to
# beat. All three inputs are stage-two columns, so the baseline is stage-two by
# construction and could not have run in 2023.
""")
        w = csv.DictWriter(fh, fieldnames=["compound", "correction_verdict",
                                           "rho", "flagged"])
        w.writeheader()
        w.writerows(rows)


def write_ceiling(digest: str, cart: dict) -> dict:
    from score_targets import build_targets, EVIDENCE_FAMILIES
    # BOTH STAGES, BECAUSE NEITHER ALONE IS THE WHOLE KEY.
    #
    # This read `build_targets(stage="two")`, which was the full list while a
    # stage-two pass emitted every group. It no longer does: a stage-two pass
    # returns K6 ALONE, because K1, K2, K4 and K5 are documentary statements
    # about the automated deposit and scoring them on a pass that releases the
    # expert re-refinement compares a check against a target defined on a
    # different file. So this call had come to mean "K6 and nothing else", and
    # regenerating the key would have written zero targets for K1-K5 and a
    # ceiling of forty - silently replacing the answer key with a fifth of it.
    # That is also why the shipped key reads STALE: the generator was out of
    # date, not merely the file.
    targets = build_targets(stage="one") + build_targets(stage="two")
    by = collections.defaultdict(list)
    for t in targets:
        by[t["group"]].append(t)

    meta = {
        "K1": ("the deposited file differs from the claimed structure",
               "the critique, Table I, E2 flag", "flag"),
        "K2": ("the symmetry of each deposited file",
               "the critique, Table III, indexed_sym", "value"),
        "K3": ("the product was already known",
               "the critique, Table I, E4 flag", "flag"),
        "K4": ("the cubic lattice parameter derived from each A-Lab CIF",
               "the critique, Table II", "value"),
        "K5": ("per-compound structural statements in the critique's prose",
               "the critique, section IV prose", "value"),
        "K6": ("the external baseline's pass/flag decision per claim",
               "CARTOGRAPH, Appendix I", "flag"),
    }
    doc = {
        "note": ("The ceiling: what the method is scored against. "
                 "GENERATED FILE - "
                 "written only by tools/build_ceiling.py. Human-readable: "
                 "docs/ceiling.md. The STAGE-ONE ceiling is K1 to K5, 55 "
                 "targets. K6 is the sixth group and is scoreable only at "
                 "stage two: it is the end-to-end test of the two-stage "
                 "protocol - abstain, name the analysis that would settle the "
                 "question, be granted it, and reach the external baseline's "
                 "decision. Counted apart from the 55 and never pooled with "
                 "them, because its inputs are the manual refinement columns "
                 "and theirs are the automated deposit. The EXTERNAL BASELINE "
                 "block the scorer prints beside it is a set comparison, not "
                 "the group."),
        "generated_by": "tools/build_ceiling.py",
        "input_digest": digest,
        "ceiling_groups": ["K1", "K2", "K3", "K4", "K5"],
        "stage_two_groups": ["K6"],
        "totals": {
            "ceiling_targets": sum(len(by[k]) for k in
                                   ("K1", "K2", "K3", "K4", "K5")),
            # K6 IS PART OF THE CEILING, SCOPED TO STAGE TWO. Counted apart
            # from the stage-one groups and never pooled with them: its inputs
            # are the manual refinement columns, which differ from the
            # automated ones by a median of 9.2 percentage points on the
            # target weight fraction and by up to 74.4, so a stage-one
            # verifier cannot compute this decision at all.
            "ceiling_targets_stage_two": cart["rows"],
            "ceiling_targets_all_stages": (
                sum(len(by[k]) for k in ("K1","K2","K3","K4","K5"))
                + cart["rows"]),
            "baseline_decisions_stage_two": cart["rows"],
        },
        # NOT a target group. This block is the set comparison the scorer
        # prints beside K6: no expectation is attached to any compound in it,
        # so nothing in it can be missed. K6 IS the target group and carries
        # its own "is_ceiling_target" under "groups", with its 40 targets.
        "baseline_comparison": {**cart, "is_target_group": False,
            "stage": "two",
            "why_stage_two": ("one decision per compound against a per-claim layer; "
                        "a different question from the critique's; and its "
                        "inputs are stage-two columns a day-one verifier "
                        "cannot hold")},
        "evidence_families": {k: list(v) for k, v in EVIDENCE_FAMILIES.items()},
        "evidence_rule": (
            "A flag target is recovered only when the compound's LEDGER verdict "
            "is refuted AND a refuting check came from a family carrying that "
            "target's evidence. Scoring all flag groups on the compound verdict "
            "alone made K1/K3 and K6 read one bit, and on 8 of 9 compounds "
            "carrying more than one flag target their expectations conflicted, "
            "so no verifier could satisfy both. K6 IS EXEMPT AND NO LONGER USES "
            "THIS RULE: since 29 August 2026 it is scored from the observation "
            "channel - the quantities the layer recorded - through the "
            "baseline's own statistic, with no witness, no refutation and no "
            "family credit. Its `baseline_flag` entry below is kept as the "
            "record of the retired scoping and decides nothing. The exclusion "
            "test for K6 reads three families, not one, because the layer "
            "records the statistic's terms mostly under phase-present and "
            "novelty; scoping it to weight-fraction alone guaranteed that the "
            "evidence deciding the flag was never the evidence the group read."),
        "groups": {},
    }
    # K6 is a STAGE-TWO target: its inputs are the manual refinement columns,
    # so it is built when scoring a stage-two ledger and absent otherwise.
    for g in ("K1", "K2", "K3", "K4", "K5", "K6"):
        finding, source, shape = meta[g]
        doc["groups"][g] = {
            "finding": finding, "source": source, "shape": shape,
            # ALL SIX ARE CEILING GROUPS. K6 is scoped to stage two, which
            # is a statement about the evidence it needs and not about its
            # standing - it was written `g != "K6"` beside a ceiling document
            # calling K6 a ceiling group, and the two contradicted each other
            # in the same repository. `ceiling_groups` and `stage_two_groups`
            # above carry the scoping; this field carries the standing.
            "is_ceiling_target": True,
            "count": len(by[g]),
            "targets": [{"id": t["id"], "compound": t["compound"],
                         "quantity": t["quantity"],
                         "expected": t["expected_display"]} for t in by[g]],
        }
    (LABELS / "ceiling.json").write_text(json.dumps(doc, indent=1))
    return doc


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true",
                    help="verify the stamped digest matches the inputs; "
                         "write nothing")
    a = ap.parse_args()
    digest = input_digest()

    if a.check:
        ok = True
        for name in ("ceiling.json", "cartograph_decisions.csv"):
            p = LABELS / name
            if not p.exists():
                print(f"  MISSING  {name}"); ok = False; continue
            stamped = "current" if digest in p.read_text() else "STALE"
            print(f"  {stamped:8s} {name}")
            ok &= stamped == "current"
        print(f"\n  input digest: {digest}")
        return 0 if ok else 1

    rows, cart = build_cartograph()
    write_cartograph(rows, cart, digest)
    doc = write_ceiling(digest, cart)
    print(f"wrote data/labels/cartograph_decisions.csv  "
          f"({cart['rows']} rows, {cart['flagged']} flagged, "
          f"do-nothing {cart['do_nothing_score_pct']}%)")
    print(f"wrote data/labels/ceiling.json  "
          f"(ceiling {doc['totals']['ceiling_targets']} targets, "
          f"baseline {doc['totals']['baseline_decisions_stage_two']} "
          f"stage-two decisions)")
    print(f"input digest: {digest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

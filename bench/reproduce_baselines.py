"""
REPRODUCTION OF THE EXTERNAL BASELINE. Deterministic, model-free, ungated:
reads the deposited refinement table. Makes no model calls and writes no
ledger.

CARTOGRAPH (Shah and Kartik, arXiv 2606.07576, "When Should an AI Scientist
Stop?"), Appendix I, is the benchmark's external baseline (section 4.11). Its
statistic is reproduced here from the paper's own definition, read from the
paper on 26 August 2026 rather than paraphrased:

    rho_A-Lab = sqrt( (Rwp/20)^2 + ((100 - w_target)/100)^2 + (w_alt/100)^2 )

  Rwp       the manual-refinement weighted-profile residual
  w_target  the target phase fraction
  w_alt     the largest non-target phase fraction

  delta is calibrated as the 95th percentile of rho over the confirmed
  'Success' rows, yielding 0.776, and frozen before the full positive-claim
  set is evaluated. Their deterministic bootstrap over the calibration rows
  (2000 resamples, seed 0) gives delta in [0.496, 1.088].

An earlier version of this script worked from a three-number paraphrase in the
benchmark seed and searched linear combinations of those numbers. It could not
reproduce the result, because the statistic is a Euclidean norm and Rwp is
scaled by 20 rather than 100. The paraphrase, not the paper, was the obstacle;
the benchmark's section 4.11 carries the paraphrase and should carry the
formula.

This script reports agreement and disagreement with the published numbers and
nothing else. It does not interpret what the statistic measures, and it makes
no claim about the chemical status of any compound. The paper states its own
scope in the same terms, and that scope is inherited here: the result shows
that a published autonomous-discovery output can be converted into an
auditable pass/flag log under a fixed calibration rule.

The critique's label sources are NOT scored here; they are benchmark section 9
material and Aletheia_v0/src/score_chain.py executes that section.

Population discipline: the critique examined 36 products, the Correction
adjudicated 40, and a count is never quoted against the other's denominator.

Usage:
  .venv/bin/python bench/reproduce_baselines.py
"""

from __future__ import annotations

import argparse
import csv
import math
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "bench"))
sys.path.insert(0, str(ROOT / "tools"))

LABELS = ROOT / "data" / "labels" / "merged_labels.csv"
PCT = re.compile(r"\[([\d.]+)%")
RWP = re.compile(r"Rwp\s*=\s*([\d.]+)")


def phase_fractions() -> dict[str, dict]:
    """Per compound: target fraction, largest impurity fraction, manual Rwp,
    read from the Correction's refinement table. A compound whose cell lists no
    percentages is a single-phase refinement: target 100, impurity 0."""
    from build_labels import parse_xlsx
    recs, _ = parse_xlsx()
    out = {}
    for r in recs:
        txt = r["man_text"]
        pcts = [float(x) for x in PCT.findall(txt)]
        rwp = RWP.search(txt)
        if pcts:
            target, impurities = pcts[0], pcts[1:]
        else:
            target, impurities = (100.0 if rwp else None), []
        out[r["compound"]] = {
            "target_pct": target,
            "max_impurity_pct": max(impurities) if impurities else 0.0,
            "rwp_manual": float(rwp.group(1)) if rwp else None,
            "n_phases": len(pcts),
        }
    return out


def percentile(xs, q):
    xs = sorted(xs)
    if not xs:
        return None
    k = (len(xs) - 1) * q
    lo, hi = int(k), min(int(k) + 1, len(xs) - 1)
    return xs[lo] + (xs[hi] - xs[lo]) * (k - lo)


def flagged(scores: dict, thr: float) -> set:
    return {c for c, s in scores.items() if s is not None and s > thr}


def report(name, scores, inconclusive, confirmed, thr):
    inc_hit = flagged(scores, thr) & inconclusive
    con_hit = flagged(scores, thr) & confirmed
    inc_n = len([c for c in inconclusive if scores.get(c) is not None])
    con_n = len([c for c in confirmed if scores.get(c) is not None])
    print(f"  {name:44s} inconclusive {len(inc_hit)}/{inc_n}   "
          f"confirmed {len(con_hit)}/{con_n}")
    return len(inc_hit), inc_n, len(con_hit), con_n


def rho_alab(f: dict) -> float | None:
    """CARTOGRAPH's materials-domain residual, Appendix I, verbatim."""
    rwp, wt, wa = (f.get("rwp_manual"), f.get("target_pct"),
                   f.get("max_impurity_pct"))
    if None in (rwp, wt, wa):
        return None
    return math.sqrt((rwp / 20.0) ** 2 + ((100.0 - wt) / 100.0) ** 2
                     + (wa / 100.0) ** 2)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--delta", type=float, default=0.776,
                    help="the paper's frozen calibration constant")
    args = ap.parse_args()

    rows = list(csv.DictReader(LABELS.open()))
    frac = phase_fractions()
    ev = [r for r in rows
          if r["correction_verdict"] in ("confirmed", "inconclusive")]
    inconclusive = {r["compound"] for r in ev
                    if r["correction_verdict"] == "inconclusive"}
    confirmed = {r["compound"] for r in ev
                 if r["correction_verdict"] == "confirmed"}

    PUBLISHED_FOUR = ["CaGd2Zr(GaO3)4", "KBaGdWO6", "Mg3MnNi3O8",
                      "Mn7(P2O7)4"]

    rho = {r["compound"]: rho_alab(frac.get(r["compound"], {})) for r in ev}
    scored = [c for c in rho if rho[c] is not None]
    print(f"CARTOGRAPH, Appendix I, reproduced from the paper's definition")
    print(f"evaluation population {len(ev)}; rho computable for "
          f"{len(scored)}\n")

    ours = percentile([rho[c] for c in confirmed if rho.get(c) is not None],
                      0.95)
    print(f"  calibration: their delta 0.776, bootstrap [0.496, 1.088]; "
          f"ours {ours:.4f}")
    print(f"    {'inside their interval' if 0.496 <= ours <= 1.088 else 'OUTSIDE their interval'}\n")

    hit = {c for c in scored if rho[c] > args.delta}
    inc_hit, con_hit = sorted(hit & inconclusive), sorted(hit & confirmed)
    print(f"  at their frozen delta {args.delta}:")
    print(f"    inconclusive flagged {len(inc_hit)}/4, confirmed flagged "
          f"{len(con_hit)}/36, passed {36 - len(con_hit)}/36")
    print(f"    published: 4/4 flagged, 32/36 passed")
    print(f"    our four : {inc_hit}")
    print(f"    published: {PUBLISHED_FOUR}")
    print(f"    SET MATCH: {inc_hit == PUBLISHED_FOUR}")
    print(f"    confirmed flagged (the paper does not name these): "
          f"{con_hit}\n")

    def baseline(name, fn, published):
        b = {c: fn(frac.get(c, {})) for c in rho}
        t = percentile([b[c] for c in confirmed if b.get(c) is not None], 0.95)
        h = {c for c, v in b.items() if v is not None and v > t}
        print(f"    {name:28s} ours {len(h & inconclusive)}/4 and "
              f"{len(h & confirmed)}/36   published {published}")

    print("  their two ablations, each calibrated by the same "
          "95th-percentile protocol:")
    baseline("Rwp only", lambda f: None if f.get("rwp_manual") is None
             else f["rwp_manual"] / 20.0, "0/4 and 2/36")
    baseline("target deficit only", lambda f: None if f.get("target_pct")
             is None else (100.0 - f["target_pct"]) / 100.0, "4/4 and 4/36")

    print("\n  The critique's label sources are benchmark section 9 material "
          "and are scored")
    print("  by Aletheia_v0/src/score_chain.py. Nothing here interprets what the "
          "statistic measures.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

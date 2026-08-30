"""Project one of our own ledgers into the entrant submission format.

THE ADAPTER CONTROL. Our arms are scored from a ledger; an entrant is scored
from a JSONL through `tools/score_submission.py`. Both end in the same
scorebook, but by different routes, and a no-layer arm can only be compared
against a layered arm if the ROUTE itself adds nothing.

So: take a layered arm, project it into the entrant format, score it both
ways, and diff. Any difference is the adapter, not the verifier. Run this
before quoting any A-versus-C number.

Usage:
    .venv/bin/python tools/ledger_to_submission.py <children_rebuilt_*.csv> --out sub.jsonl
"""
from __future__ import annotations
import argparse, csv, json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# family -> the evidence class an entrant would declare for a refutation there
FAMILY_CLASS = {
    "cation-ordering": "deposited-file",
    "phase-present": "deposited-file",
    "novelty": "reference-database",
    "weight-fraction": "refinement-fit",
}


def rows(p: Path):
    return list(csv.DictReader(l for l in p.open() if not l.startswith("#")))


def project(children_path: Path) -> list[dict]:
    children = rows(children_path)
    ledger_path = Path(str(children_path).replace("children_rebuilt_",
                                                  "ledger_rebuilt_"))
    verdicts = {r["compound"]: r.get("verdict", "")
                for r in rows(ledger_path)}

    by_compound: dict = {}
    for r in children:
        by_compound.setdefault(r["compound"], []).append(r)

    out = []
    for compound, rs in sorted(by_compound.items()):
        obs: dict = {}
        for r in rs:
            blob = (r.get("observations") or "").strip()
            if not blob:
                continue
            try:
                d = json.loads(blob)
            except Exception:
                continue
            if isinstance(d, dict):
                for k, v in d.items():
                    obs.setdefault(k, []).append(v)

        # THE PROJECTION MUST APPLY THE SAME RULE THE SCORER DOES. An entrant
        # submits ONE value per quantity; a layered arm records one per child.
        # The scorer takes the arm's modal value (28 Aug 2026), so the
        # projection emits the mode too. Emitting the first value instead made
        # the two routes disagree on K4 by four targets, and that gap was the
        # projector, not the adapter.
        from collections import Counter as _C

        def _canon(x):
            """The SAME key score_targets.py takes the mode over.

            It canonicalises a numeric value to six significant figures before
            counting, so 10.6701 and 10.67010001 are one vote rather than two.
            A projection that takes the mode over raw strings picks a different
            winner and the two routes then disagree on K4 for no reason but
            the string formatting.
            """
            try:
                return f"{float(x):.6g}"
            except (TypeError, ValueError):
                return str(x).strip()

        obs = {k: _C(_canon(x) for x in v).most_common(1)[0][0]
               for k, v in obs.items()}
        for k, v in list(obs.items()):
            try:
                obs[k] = float(v) if "." in v or "e" in v.lower() else int(v)
            except (TypeError, ValueError):
                pass

        verdict = "refuted" if verdicts.get(compound) == "refuted" \
            else "cannot_verify"

        classes, witness = [], None
        if verdict == "refuted":
            for r in rs:
                if r.get("check_status") != "refuted":
                    continue
                cls = FAMILY_CLASS.get(r.get("family", ""))
                if cls and cls not in classes:
                    classes.append(cls)
                w = (r.get("witness") or "").strip()
                if witness is None and w.startswith("{"):
                    try:
                        wj = json.loads(w)
                        witness = {k: str(wj.get(k, ""))
                                   for k in ("where", "observed", "required")}
                    except Exception:
                        pass

        # PER-EVIDENCE-CLASS FINDINGS. The flat form could carry only the
        # compound's rolled-up verdict and one witness, so a projected arm lost
        # (a) every class it examined without refuting and (b) any refutation
        # beyond the first. Both are now expressible, so the projection is
        # faithful and the two scoring routes can be compared.
        FAM_CLASS = {v: k for k, v in FAMILY_CLASS.items()}
        findings = []
        for cls in ("deposited-file", "reference-database", "refinement-fit"):
            fam = FAM_CLASS[cls]
            kids = [r for r in rs if r.get("family") in
                    ([f for f, c in FAMILY_CLASS.items() if c == cls])]
            if not kids:
                continue
            ref = [r for r in kids if r.get("check_status") == "refuted"]
            # PICK THE WITNESS THAT VALIDATES, not the first one written. A
            # compound has up to sixteen children and several may refute; the
            # ledger route takes the strongest per-child verdict, so a
            # projection that grabs an arbitrary witness reports a weaker arm
            # than the ledger does and the two routes disagree for a reason
            # that is purely the projection's.
            RANK = {"True": 3, "UNADJUDICABLE": 2, "NO-FILE": 1, "False": 0}
            ref.sort(key=lambda r: RANK.get(
                (r.get("witness_reproduced") or "").strip(), -1), reverse=True)
            f = {"evidence_class": cls,
                 "verdict": "refuted" if ref else "cannot_verify"}
            for r in ref:
                w = (r.get("witness") or "").strip()
                if w.startswith("{"):
                    try:
                        wj = json.loads(w)
                        f["witness"] = {k: str(wj.get(k, "")) for k in
                                        ("where", "observed", "required")}
                        break
                    except Exception:
                        pass
            findings.append(f)

        line = {"instance_id": f"alab:{compound}", "verdict": verdict,
                "findings": findings, "observations": obs}
        out.append(line)
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("children")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    lines = project(Path(a.children))
    Path(a.out).write_text("\n".join(json.dumps(x) for x in lines) + "\n")
    n_ref = sum(1 for x in lines if x["verdict"] == "refuted")
    n_obs = sum(1 for x in lines if x["observations"])
    print(f"projected {len(lines)} instances -> {a.out}")
    print(f"  refuted {n_ref}, carrying observations {n_obs}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""
SCORE AN ENTRANT SUBMISSION.

The interface that turns this from our evaluation suite into a benchmark.
`score_targets` consumes our chain's ledger format, so until now "others can
run their own layer on the same work" was a claim we could not honour. This
adapts a submission JSONL into the shape the scorebook already reads, so an
entrant is scored by exactly the same code that scores our own arms - not by a
parallel implementation that could drift.

The contract is docs/ENTRANT.md. Usage:

    .venv/bin/python tools/score_submission.py <submission.jsonl>
    .venv/bin/python tools/score_submission.py <submission.jsonl> --targets
    .venv/bin/python tools/score_submission.py --emit-instances

WHAT IS ENFORCED HERE, AND WHY EACH ONE:

  - `verified` is rejected outright. Deciding FOR a claim needs the measured
    patterns, which were never deposited, so no verifier can honestly return
    it and a submission containing it is malformed rather than wrong.
  - Every refutation must carry a witness with three fields, and that witness
    must establish a contradiction. One that does not is not counted as a
    refutation, so the target it would have recovered scores as MISSED.
  - A witness must establish a CONTRADICTION, judged against our claim record
    and never against the entrant's own `required` text, which is written by
    the system being judged. This is enforced by calling
    aggregate.witness_reproduced - the same function our own arms are held to,
    so the two paths cannot drift apart.
  - Unknown observation keys are kept and not scored. Silently dropping them
    would hide the case where an entrant measured the right thing under its
    own name.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "bench"))
# bench_shim lives beside this file; make it importable when score_submission
# is imported as a module rather than run as a script.
sys.path.insert(0, str(ROOT / "tools"))
LABELS = ROOT / "data" / "labels"
ENTRANT_DIR = ROOT / "data" / "entrant"

VALID_VERDICTS = {"refuted", "cannot_verify", "inapplicable"}

# instance_id -> the check family that instance stands for. The scorebook needs
# a family to decide which targets an instance could have reached, and which
# evidence class a refutation rests on.
# EVIDENCE CLASSES an entrant declares for each refutation, and the internal
# family each maps to. This is benchmark vocabulary, deliberately NOT our
# decomposition vocabulary: an entrant splits the claim however it likes, or
# not at all, and only has to say WHAT KIND OF EVIDENCE its refutation rests
# on. That is the one thing the scorer needs, because a file-contradiction
# does not establish "already known" and a database match does not establish
# "the file differs".
EVIDENCE_CLASS = {
    "deposited-file": "cation-ordering",
    "reference-database": "novelty",
    "refinement-fit": "weight-fraction",
}

# WHAT THE STANDALONE CHECKER CAN ACTUALLY ADJUDICATE.
#
# `tools/check_witness.py` reads ONE artifact: the deposited structure file.
# Its predicates are occupancy, symmetry-tag, stoichiometry and lattice. It
# holds no reference corpus and no refinement table, so it cannot establish
# that a compound is already known, and it cannot establish that a reported
# fit contradicts a claim.
#
# It nonetheless tries every predicate whatever family it is handed, and
# credits the witness if ANY of them finds a contradiction. So a witness
# quoting the structure file satisfied a `reference-database` refutation, and
# the entrant collected K3 without opening a database. Adjudicating once per
# declared class - the repair directly above - is necessary and does not fix
# this, because every class was landing on the same file predicates.
#
# FAIL CLOSED, which is the rule everywhere else here: a class whose evidence
# the checker cannot read is RECORDED and NEVER CREDITED. That makes K3
# currently unreachable through a submission, and saying so is the honest
# state. It becomes reachable when a database-side predicate exists that can
# check a claimed entry against a pinned corpus - not before.
# All three are adjudicable as of 28 Aug 2026: the checker reads the deposited
# file, the pinned reference snapshot, and the refinement workbook. A class is
# declined only when no predicate applies, which adjudicate() reports itself.
ADJUDICABLE_CLASSES = {"deposited-file", "reference-database", "refinement-fit"}

UNADJUDICABLE_REASON = {
    "reference-database": ("the standalone checker reads only the deposited "
                           "structure file; it holds no reference corpus and "
                           "cannot establish that a compound is already known, "
                           "so a witness cannot be credited for this class"),
    "refinement-fit": ("the standalone checker reads only the deposited "
                       "structure file; it holds no refinement table and "
                       "cannot establish that a reported fit contradicts the "
                       "claim, so a witness cannot be credited for this class"),
}


def emit_instances() -> int:
    """Write the evidence-only projection an entrant is given.

    ONE INSTANCE PER COMPOUND, carrying the claim AS THE PAPER MADE IT.

    It used to be 160 instances - 40 compounds times OUR four decomposition
    families - which forced an entrant into our decomposition. Decomposing a
    claim into checkable parts is a verifier's own job and one of the things
    that differs between verifiers; handing over ours makes the benchmark
    measure agreement with our taxonomy rather than recovery of the findings.
    An entrant may split the claim however it likes, or not at all, so long as
    it reaches the findings.

    ALL THE EVIDENCE, WITH THE STAGE SAID OUT LOUD. It used to ship a CIF and
    a hash, which is less than the panel had: 80 of the 160 questions asked
    about phase fractions or prior literature and neither was in the bundle.
    Now stage one carries the deposited structure file AND the automated
    refinement row - the robot's own day-one numbers - and stage two is
    described but withheld until requested.

    NO ANSWERS. No expert flag, no determination, no verdict, no baseline
    decision. That is the only thing withheld, and it is withheld because it
    is the answer key, not because it is evidence.
    """
    from bench_shim import resolve_cif, refinement_row
    import hashlib
    ENTRANT_DIR.mkdir(parents=True, exist_ok=True)
    rows = [r for r in csv.DictReader((LABELS / "merged_labels.csv").open())
            if r["correction_verdict"] in ("confirmed", "inconclusive")]
    out = []
    for r in rows:
        c = r["compound"]
        p = resolve_cif("Automated_Refinement_Results", c)
        if not p.exists():
            continue
        row1 = refinement_row(c, stage="one")
        out.append({
            "instance_id": f"alab:{c}",
            "compound": c,
            # the claim as published, undecomposed. Split it yourself, or not.
            "claim": (f"{c} was synthesised as a new inorganic material, with "
                      f"the structure reported in the deposited file"),
            "claim_record": {
                "compound": c,
                "claimed_space_group": r.get("prx_proposed_sym", ""),
                "claimed_structure": c,
                "asserts": [
                    "the compound was synthesised",
                    "the compound is a new inorganic material",
                    "the compound has the claimed structure",
                ],
                "does_not_assert": [
                    "any purity or weight-fraction threshold - the paper "
                    "states none, so a refutation of one does not refute this "
                    "claim",
                ],
            },
            "evidence_stage_one": {
                "structure_file": str(p.relative_to(ROOT)),
                "sha256": hashlib.sha256(p.read_bytes()).hexdigest(),
                "refinement": {
                    "note": "the automated refinement reported in the deposit; "
                            "day-one data, present when the claim was made",
                    "rwp_pct": row1.get("rwp"),
                    # BOTH SPELLINGS TRAVEL. `formula` is the label as the
                    # deposit prints it, annotations and all; `formula_core`
                    # is the part that parses as a composition. Shipping only
                    # the first is a trap: the deposit spells one compound's
                    # own phase `Ba6Na2Ta2V2O17` where the claim spells it
                    # `Ba6Ta2Na2V2O17` - the same composition, two elements
                    # transposed - so a string compare finds no target and
                    # counts the target's own 63.38 per cent as an impurity.
                    # That trap has produced a model error twice. Match on
                    # `formula_core`, by composition, never on the printed name.
                    "phases": [{"formula": ph.get("formula"),
                                "formula_core": ph.get("formula_core"),
                                "wt_pct": ph.get("wt_pct")}
                               for ph in row1.get("phases", [])],
                },
            },
            "evidence_stage_two": {
                "available": False,
                # COLUMNS ONLY. This said "a different structure file and
                # different refinement columns", which described the substitution
                # that was withdrawn: swapping the deposit meant a check written
                # against one file was executed against another, undeclared, and
                # 41 of 42 deposits differ in lattice parameter beyond the
                # tolerance it is scored at. The deposited file is the object
                # under audit.
                "what_it_is": "an expert re-refinement of the same pattern "
                              "against an expanded phase set, released as "
                              "REFINEMENT COLUMNS ONLY: the deposited structure "
                              "file is not substituted, because it is the object "
                              "under audit",
                "how_to_get_it": "abstain and return a follow_up naming "
                                 "re-refinement-expanded-phase-set",
                "declared_contamination": "it was produced by people who "
                                          "already knew how the dispute came "
                                          "out; it is scored separately and "
                                          "never pooled with stage one",
            },
            "reference_corpus": {
                "available": False,
                "note": "novelty is judged against a crystallographic "
                        "database. The critique used the ICSD; an open "
                        "database gives different coverage and recovers none "
                        "of its novelty flags. Bring your own, and say which.",
            },
            "budget_counts_band": [1e5, 1e7],
        })
    # REFUSE TO WRITE A SHORT BUNDLE OVER THE SHIPPED ONE. Every compound whose
    # deposited file does not resolve is skipped above, and the deposit is
    # gitignored - so in a fresh clone this wrote ZERO instances over the 40 the
    # benchmark ships, reported "0 instances" as though that were a result, and
    # left the entrant bundle destroyed. The bundle is a deliverable, not scratch
    # output: a projection that lost compounds is not a bundle, it is a symptom.
    if len(out) < len(rows):
        raise SystemExit(
            f"REFUSING TO WRITE: {len(out)} of {len(rows)} compounds have a "
            f"resolvable deposited file.\n"
            f"Writing now would overwrite the shipped bundle at "
            f"{ENTRANT_DIR / 'instances.jsonl'} with a short one.\n"
            f"The deposit is the 2023 paper's supplementary material and is not "
            f"redistributed here; unpack it\n"
            f"so data/cifs/Automated_Refinement_Results/<compound>/ exists, then "
            f"re-run. See the README Quickstart.")

    f = ENTRANT_DIR / "instances.jsonl"
    f.write_text("".join(json.dumps(x) + "\n" for x in out))

    from bench_shim import MENU
    (ENTRANT_DIR / "follow_up_menu.json").write_text(json.dumps(
        [{"modality": k, "statement": v["statement"]}
         for k, v in MENU.items()], indent=1))

    n_rw = sum(1 for x in out
               if x["evidence_stage_one"]["refinement"]["rwp_pct"] is not None)
    print(f"wrote {f}")
    print(f"  {len(out)} instances, one per compound, claim undecomposed")
    print(f"  stage-one refinement row present on {n_rw} of {len(out)}")
    print(f"wrote {ENTRANT_DIR / 'follow_up_menu.json'}")
    print("\nWithheld: expert flags, symmetry determinations, Correction "
          "verdicts, baseline\ndecisions. Nothing else.")
    return 0


def load_submission(path: Path) -> tuple[list[dict], list[str]]:
    rows, problems = [], []
    for i, line in enumerate(path.read_text().splitlines(), 1):
        if not line.strip():
            continue
        try:
            d = json.loads(line)
        except Exception as exc:
            problems.append(f"line {i}: not JSON ({exc})")
            continue
        iid = d.get("instance_id")
        if not iid or iid.count(":") < 1:
            problems.append(f"line {i}: missing or malformed instance_id")
            continue
        v = d.get("verdict")
        if v == "verified":
            problems.append(
                f"line {i}: verdict 'verified' is not in the grammar. Deciding "
                f"FOR a claim needs the measured patterns, which were never "
                f"deposited")
            continue
        if v not in VALID_VERDICTS:
            problems.append(f"line {i}: verdict {v!r} not one of "
                            f"{sorted(VALID_VERDICTS)}")
            continue
        rows.append(d)
    return rows, problems


class _W:
    """The three witness fields, in the shape bench_shim.witness_reproduced wants."""
    def __init__(self, d): self.where, self.observed, self.required = (
        str(d.get("where", "")), str(d.get("observed", "")),
        str(d.get("required", "")))


def witness_ok(row: dict, for_class: str = "") -> tuple[bool, str]:
    """Is this refutation supported by an ESTABLISHED CONTRADICTION?

    FIXED 28 August 2026. This used to test that three fields were non-empty
    strings, while the module docstring, this comment and ENTRANT.md all
    promised the contradiction test. It was never run: `check_witness` appeared
    once in the file, inside a comment saying it was "run below".

    What that cost. Three plausible sentences bought a flag recovery. An
    entrant refuting all 40 compounds with invented prose recovered every K1
    target, and ENTRANT.md's stated incentive - that unwitnessed refutations
    score worse than abstaining - was false. It was fail-open AND provenance
    asserted-not-implemented, two error classes already named in
    docs/known-defects.md, reintroduced in the entrant path on the day they were
    fixed in the ceiling path.

    Worse, it broke the one thing the adapter exists for. Our own arms pass
    through aggregate.py's fail-closed validation; entrants skipped it, so the
    shared scorebook reported two different measurements on one scale.

    It now calls `bench_shim.witness_reproduced`. That was
    `aggregate.witness_reproduced` until the benchmark was split out of the
    layer; the shim holds a copy, because a benchmark that imports the verifier
    it scores makes our verifier a dependency of everyone else's measurement.

    THE COPY IS NOT WHERE THE ADJUDICATION LIVES, so the split does not
    reintroduce the drift this paragraph was written to rule out. Both
    `witness_reproduced` and its copy are subprocess wrappers; the verdict is
    reached by `tools/check_witness.py`, which is NOT copied and is the single
    file our own arms and every entrant are both judged by. What the shim
    duplicates is 20 lines of tempfile-and-argv marshalling. Reimplementing the
    CHECKER here, rather than shelling out to it, would be the
    reimplementation-instead-of-reuse failure that produced the w_alt error.

    Returns (counts_as_refutation, reason).
    """
    if row.get("verdict") != "refuted":
        return True, ""
    w = row.get("witness")
    if not isinstance(w, dict):
        return False, "refutation with no witness"
    missing = [k for k in ("where", "observed", "required")
               if not str(w.get(k, "")).strip()]
    if missing:
        return False, f"witness missing {missing}"

    # the contradiction test, against OUR claim record and never against the
    # entrant's own `required` text, which the entrant also wrote
    try:
        from bench_shim import witness_reproduced, Claim
        compound = row["instance_id"].split(":", 1)[1]
        # the family the checker adjudicates against is the evidence class the
        # entrant declared, not our decomposition
        # ONE ADJUDICATION PER DECLARED CLASS, NOT ONE PER SUBMISSION.
        #
        # This took the FIRST declared class and adjudicated the witness only
        # under that, then the caller stamped the single pass or fail onto a
        # synthetic child for EVERY declared class. So one file witness paid
        # out for `reference-database` as well - exactly what §3 of ENTRANT.md
        # promises cannot happen, since a file contradiction does not establish
        # "already known". Declaring all three classes and passing the cheapest
        # test collected all three findings.
        family = EVIDENCE_CLASS.get(for_class, "cation-ordering")
        from bench_shim import resolve_cif
        cif = resolve_cif("Automated_Refinement_Results", compound)
        if not cif.exists():
            return False, "no deposited file to test the witness against"
        # THE REQUIREMENT COMES FROM THE CLAIM RECORD, NOT THE SUBMISSION.
        #
        # `check_witness.check_space_group` reads the claimed group from the
        # claim record when one is supplied and falls back to the witness's own
        # `required` text otherwise. This passed only the compound, so every
        # entrant symmetry witness was graded against text the entrant wrote -
        # the exact thing docs/ENTRANT.md 3 says cannot happen, and the enabler
        # for the `P 1` attack in 7a: 38 of the 40 deposited files record their
        # symmetry as `P 1`, so a witness naming any other group as "required"
        # contradicted the file by construction. The claimed group is a label,
        # `prx_proposed_sym`, and the same value the entrant's own instance
        # carries as `claim_record.claimed_space_group`.
        c = Claim(id=row["instance_id"], family=family,
                  assertion={"compound": compound,
                             "space_group_claimed": _claimed_sg(compound)})
        ok = witness_reproduced(_W(w), cif, claim=c)
    except Exception as exc:
        return False, f"witness checker could not run: {type(exc).__name__}"

    if ok is False:
        return False, ("the standalone checker did not establish a "
                       "contradiction between the deposited file and the "
                       "claim record")
    if ok is None:
        return False, ("the standalone checker could not adjudicate this "
                       "witness class; a refutation it cannot judge is not "
                       "counted, which is the same fail-closed rule our own "
                       "arms are held to")
    return True, ""



_CLAIMED_SG: dict = {}


def _claimed_sg(compound: str) -> str:
    """The space group the 2023 paper CLAIMED for this compound.

    Read from the label table, joined by composition, so a formula spelled with
    its elements in a different order still resolves. Empty when the label has
    none, which leaves check_witness to say the required side names no group -
    the fail-closed answer, not the entrant's own text.
    """
    if not _CLAIMED_SG:
        from score_targets import _key
        for r in csv.DictReader((LABELS / "merged_labels.csv").open()):
            _CLAIMED_SG[_key(r["compound"])] = (r.get("prx_proposed_sym") or "").strip()
    from score_targets import _key
    return _CLAIMED_SG.get(_key(compound), "")


# ---------------------------------------------------------------- findings

# ONE VERDICT PER COMPOUND WAS THE WRONG UNIT (28 Aug 2026).
#
# The benchmark's targets are grouped BY EVIDENCE CLASS - K1 needs the
# deposited file, K3 needs a reference corpus, K6 needs the refinement row -
# so the natural unit of a submission is (compound, evidence class), not
# compound. The flat form could not express two things a verifier routinely
# does, and both cost real targets when our own arms were projected through it:
#
#  1. WHAT WAS EXAMINED WITHOUT REFUTING. `refuted_on` exists only on
#     refutations, so a verifier that queried a database, found nothing and
#     abstained declared nothing at all. 23 of 40 projected lines were
#     `cannot_verify` and carried no record of what had been looked at, so K3
#     scored 0 attempted of 2 and K2 32 attempted of 37. Abstaining correctly
#     earned no coverage.
#
#  2. A REFUTATION PER CLASS, WITH ITS OWN WITNESS. One `witness` per line
#     means a verifier refuting on both the file and the database can justify
#     only one of them.
#
# `findings` is the richer form: one entry per evidence class examined, each
# with its own verdict and its own witness. The flat form still parses and is
# translated here, so an existing submission keeps working.

def _findings(d: dict) -> list[dict]:
    """Normalise a submission line into one entry per evidence class.

    Returns [{"evidence_class", "verdict", "witness"}]. Never raises.
    """
    fs = d.get("findings")
    if isinstance(fs, list) and fs:
        out = []
        for f in fs:
            if not isinstance(f, dict):
                continue
            out.append({"evidence_class": f.get("evidence_class", ""),
                        "verdict": f.get("verdict", d.get("verdict", "")),
                        "witness": f.get("witness") or d.get("witness")})
        if out:
            return out

    # ---- the flat form, translated
    ref = d.get("refuted_on") or []
    if isinstance(ref, str):
        ref = [ref]
    exam = d.get("examined") or []
    if isinstance(exam, str):
        exam = [exam]
    seen, out = [], []
    for c in list(ref) + [c for c in exam if c not in ref]:
        if c in seen:
            continue
        seen.append(c)
        out.append({"evidence_class": c,
                    "verdict": "refuted" if c in ref else "cannot_verify",
                    "witness": d.get("witness") if c in ref else None})
    if not out:
        # nothing declared: a single unclassified entry, exactly as before
        out = [{"evidence_class": "", "verdict": d.get("verdict", ""),
                "witness": d.get("witness")}]
    return out


def to_ledger(rows: list[dict], out_dir: Path) -> tuple[Path, Path, dict]:
    """Adapt a submission into the children/ledger pair the scorebook reads.

    An entrant submits ONE ROW PER COMPOUND and declares, for a refutation,
    which evidence class it rests on. Here that becomes one synthetic child
    per declared class, which is the shape the scorebook's evidence-family
    rule reads. Nothing about the entrant's own decomposition is required or
    recorded: it may have used none.

    The entrant is scored by the SAME scorebook as our own arms. A second
    scorer written for submissions would drift, and drift favours whoever
    wrote it.

    Returns (children_path, ledger_path, adjudication). The third element is
    the tally of what the witness checker actually decided, per declared
    refutation, keyed by `witness_reproduced` value with the reasons attached.
    The caller prints its summary FROM THIS, never from a second pass over the
    raw submission - see the note in main().
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    kfields = ["compound", "claim_id", "family", "check_source",
               "security_pass", "security_problems", "form_pass",
               "verdict_raw", "check_status", "witness", "observations",
               "follow_up", "stage_two_file", "witness_reproduced",
               "instance_state", "n_rivals", "rivals_admissible",
               "achievable_min", "floor_max", "sequential_min",
               "instance_notes"]
    krows, per_compound, adjudication = [], {}, {}
    for d in rows:
        compound = d["instance_id"].split(":", 1)[1]
        findings = _findings(d)
        unknown = [f["evidence_class"] for f in findings
                   if f["evidence_class"] and f["evidence_class"]
                   not in EVIDENCE_CLASS]

        # ONE SYNTHETIC CHILD PER EVIDENCE CLASS EXAMINED. A class that was
        # looked at and produced no refutation is `consistent`, which is what
        # makes it count as ATTEMPTED - the coverage a flat submission could
        # not declare.
        seen_fams, i = [], 0
        for f in findings:
            cls = f["evidence_class"]
            fam = EVIDENCE_CLASS.get(cls, "cation-ordering")
            if fam in seen_fams:
                continue
            seen_fams.append(fam)

            this_refuted, wr, why = False, "", ""
            if f["verdict"] == "refuted":
                if not cls:
                    why = ("refutation declares no evidence class; it cannot "
                           "be matched to a finding, so it establishes nothing")
                elif cls not in ADJUDICABLE_CLASSES:
                    wr, why = "UNADJUDICABLE", UNADJUDICABLE_REASON[cls]
                else:
                    ok, why = witness_ok({**d, "witness": f["witness"],
                                          "verdict": "refuted"}, cls)
                    wr = "True" if ok else "False"
                    this_refuted = ok
                adjudication.setdefault(wr or "NO-CLASS", []).append(
                    (compound, cls, why))

            r = dict.fromkeys(kfields, "")
            r.update(compound=compound,
                     claim_id=f"{d['instance_id']}#{fam}",
                     family=fam, check_source="entrant-submission",
                     security_pass="True",
                     verdict_raw=f["verdict"],
                     # WHAT THE CHECK RETURNED, not whether it was validated.
                     # Those are different facts and the ledger keeps them in
                     # different columns: `check_status` is the check's own
                     # verdict, `witness_reproduced` is the independent
                     # adjudication. Collapsing an UNADJUDICABLE refutation to
                     # `consistent` erases it from the refuting families, and
                     # the scorer can then never mark the target REACHED-but-
                     # unvalidatable - which is exactly how a correct finding
                     # on a class the checker cannot read becomes a silent
                     # miss. The evidence-class boundaries partition WHICH
                     # check answers WHICH target; they must not delete the
                     # answer.
                     check_status=("refuted" if f["verdict"] == "refuted"
                                   and cls else
                                   ("consistent"
                                    if f["verdict"] in ("cannot_verify",
                                                        "refuted")
                                    else "inapplicable")),
                     witness=json.dumps(f["witness"]) if f["witness"] else "",
                     witness_reproduced=wr,
                     observations=json.dumps(d.get("observations") or "")
                                  if i == 0 and d.get("observations") else "",
                     follow_up=json.dumps(d.get("follow_up"))
                               if d.get("follow_up") else "",
                     # the INSTANCE state still requires validation: a
                     # refutation counts only on an independent reproduction
                     instance_state="REFUTED" if this_refuted else "",
                     instance_notes="; ".join(x for x in
                         [why, f"unrecognised evidence class {unknown}"
                          if unknown else ""] if x))
            krows.append(r)
            i += 1
            if this_refuted:
                per_compound[compound] = "refuted"
        per_compound.setdefault(compound, "cannot_verify")

    kp = out_dir / "children_rebuilt_submission.csv"
    with kp.open("w") as fh:
        w = csv.DictWriter(fh, fieldnames=kfields); w.writeheader()
        w.writerows(krows)
    lp = out_dir / "ledger_rebuilt_submission.csv"
    with lp.open("w") as fh:
        w = csv.DictWriter(fh, fieldnames=["compound", "verdict"]); w.writeheader()
        w.writerows({"compound": c, "verdict": v}
                    for c, v in sorted(per_compound.items()))
    return kp, lp, adjudication


def main() -> int:
    ap = argparse.ArgumentParser(description="Score an entrant submission.")
    ap.add_argument("submission", nargs="?", help="a JSONL file")
    ap.add_argument("--targets", action="store_true")
    ap.add_argument("--emit-instances", action="store_true")
    a = ap.parse_args()

    if a.emit_instances:
        return emit_instances()
    if not a.submission:
        ap.error("give a submission file, or --emit-instances")

    rows, problems = load_submission(Path(a.submission))
    print(f"\nSUBMISSION - {Path(a.submission).name}")
    print(f"  {len(rows)} accepted instance results")
    if problems:
        print(f"  {len(problems)} REJECTED:")
        for p in problems[:12]:
            print(f"    {p}")
    out = ROOT / "results" / "submissions" / Path(a.submission).stem
    kp, _, adjudication = to_ledger(rows, out)
    print(f"  adapted to {kp.relative_to(ROOT)}")

    # THE WITNESS SUMMARY IS DERIVED FROM THE ADAPTED ROWS, NOT FROM A SECOND
    # PASS OVER THE SUBMISSION (fixed 28 August 2026).
    #
    # It used to call `witness_ok(r)` on each raw submission line. That reads
    # `r["witness"]` - the FLAT format. Since the contract took per-evidence-
    # class `findings`, the witness lives at `r["findings"][i]["witness"]`, so
    # the top-level key is absent and every refutation was reported as
    # "refutation with no witness". Meanwhile the scoring path adapts each
    # finding and adjudicates it correctly. The report therefore opened by
    # announcing that N refutations established nothing and then, eight lines
    # later, credited the targets those same refutations recovered. On the
    # projected opus5 arm it printed 23 failures that did not happen, directly
    # above a scorebook showing K1 7 of 7.
    #
    # Two statements about one adjudication, computed twice, disagreeing: this
    # project's own named error class. The summary now reads the tally
    # `to_ledger` recorded while adjudicating, so the printed reasons and the
    # scored outcomes are one computation and cannot drift.
    failed = adjudication.get("False", []) + adjudication.get("NO-CLASS", [])
    unadj = adjudication.get("UNADJUDICABLE", [])
    if failed:
        print(f"  {len(failed)} refutation(s) did not establish a "
              f"contradiction and are NOT counted")
        print(f"    as refutations. The target each would have recovered "
              f"scores as MISSED - the")
        print(f"    same fail-closed rule our own arms are held to. Reasons:")
        seen: dict = {}
        for _c, _cls, why in failed:
            seen[why] = seen.get(why, 0) + 1
        for why, n in sorted(seen.items(), key=lambda kv: -kv[1])[:4]:
            print(f"      {n:3d}  {why}")
    if unadj:
        print(f"  {len(unadj)} refutation(s) rest on an evidence class the "
              f"standalone checker")
        print(f"    cannot read. Recorded UNVALIDATED: reached, not "
              f"validated, and NEVER a miss.")
    if not failed and not unadj:
        n_ref = sum(len(v) for v in adjudication.values())
        if n_ref:
            print(f"  all {n_ref} declared refutation(s) established a "
                  f"contradiction against the deposited evidence")

    from score_targets import report
    return report(kp, show_targets=a.targets)


if __name__ == "__main__":
    raise SystemExit(main())

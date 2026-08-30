"""
THE NO-LAYER ABLATION. Drive a model through the entrant contract directly.

WHY THIS EXISTS. Every number this project holds measures MODEL + LAYER. There
is no MODEL ALONE, so nothing yet says whether the layer helps, hurts, or is
irrelevant - which is the load-bearing claim of the whole architecture. This
runs the two conditions that bracket it:

  A   BARE          the model gets the claim and the structure file AS TEXT,
                    no execution. Measures reading and recall.
  B   TOOLED-BLIND  one shot at running code it writes itself, but it NEVER
                    SEES THE FILE - only its name. Measures writing a checker
                    against evidence you cannot inspect.
  B2  TOOLED        the same, and the file is inlined in the prompt as well.
                    This is the true "C minus the scaffolding".

  C   LAYERED       what Aletheia_v0/src/run_chain.py already produces.

WHY B AND B2 ARE BOTH KEPT. B was built first and handed the model only the
filename, while A and C both inline the deposited file into the prompt -
`run_probe_sweep.build_prompt` appends its full contents. So B was carrying a
SECOND handicap nobody intended: not only no scaffolding, but no sight of the
evidence. A B-versus-C gap would have confounded the two.

The symptom was visible in the code the model wrote: programs that glob the
directory for any *.cif, regex the header for two alternative tag spellings,
and wrap every step in try/except - which is not defensive style, it is a model
coding against a file it has never seen. Those programs ran 150 to 270 lines
and hit the token ceiling on 11 of 40, where A's never did.

B2 fixes it and is the condition to compare against C. B is kept because
"write a checker against evidence you cannot inspect" is a real and separately
interesting condition, not a mistake to be deleted.

A-versus-C conflates two things - having verified primitives at all, and
having this particular architecture. B-versus-C separates them, and is the
comparison that defends the contribution.

WHY IT GOES THROUGH THE ENTRANT CONTRACT. `tools/score_submission.py` scores a
submission with the same scorebook that scores our own arms, and as of 28 Aug
2026 a layered arm projected through `tools/ledger_to_submission.py` scores
IDENTICALLY by both routes on three of four arms and on all six groups. So the
route adds nothing and the three conditions are comparable. Scoring A or B
against a ledger-scored C would measure the adapter instead.

  .venv/bin/python tools/run_nolayer.py --condition a --model opus5 --dry-run
  .venv/bin/python tools/run_nolayer.py --condition a --model opus5      # GATED
  .venv/bin/python tools/score_submission.py results/nolayer/a-opus5/submission.jsonl

THE SEAL APPLIES HERE TOO. One completion per instance, and the runner refuses
to enter a populated output directory without --fill. No expert label, flag,
verdict or finding enters either prompt: the instance bundle carries the claim
and the evidence and nothing else, which is the same bundle an outside entrant
receives.

CONDITION B RUNS UNGATED MODEL-WRITTEN CODE, AND THAT IS THE POINT - generic
tool use without the layer's security gate is exactly what is being measured.
The containment is therefore the process and the filesystem, not a static
audit: a fresh temporary directory holding one copy of the structure file, a
credential-scrubbed environment, a wall-clock timeout, and the repository not
reachable by a relative path. It is NOT a sandbox. The child can still open a
socket, and no seccomp or container boundary is built here - the same
limitation `Aletheia_v0/src/isolate.py` states about itself.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "bench"))

INSTANCES = ROOT / "data" / "entrant" / "instances.jsonl"
MENU = ROOT / "data" / "entrant" / "follow_up_menu.json"
OUT = ROOT / "results" / "nolayer"

RUNNER_VERSION = "nolayer-0.1.0"
TIMEOUT_S = 120

# The submission grammar, given to the model verbatim in both conditions. It is
# the contract from docs/ENTRANT.md and nothing is added or withheld.
CONTRACT = """\
Return ONE line of JSON. No prose, no markdown fence, no explanation.

{"instance_id": "<the instance_id you were given>",
 "verdict": "refuted" | "cannot_verify" | "inapplicable",
 "findings": [
   {"evidence_class": "deposited-file" | "reference-database" | "refinement-fit",
    "verdict": "refuted" | "cannot_verify",
    "witness": {"where": "...", "observed": "...", "required": "..."}}
 ],
 "observations": {"<quantity>": <value>, ...},
 "follow_up": {"modality": "...", "separates": "...", "observation": "..."}}

THERE IS NO AFFIRMING VERDICT. Deciding FOR a claim would need the measured
diffraction patterns, which were never deposited. A submission containing
"verified" is rejected.

findings: ONE ENTRY PER EVIDENCE CLASS YOU EXAMINED, including classes where
you found nothing. A class you looked at and did not refute is recorded with
verdict "cannot_verify" and no witness. This is how coverage is measured; a
class you do not list counts as never attempted.

  deposited-file      the structure file contradicts the claim
  reference-database  the compound is present in a reference corpus
  refinement-fit      the reported fit or phase fractions contradict the claim

witness: REQUIRED on every finding whose verdict is "refuted". Three fields:
where you looked, what you observed, what the claim required instead. An
independent checker re-reads the deposited file and must be able to establish
a CONTRADICTION from it. Write `observed` as values that checker can locate in
the file:

  observed: "site 3 species {'Mg': 0.5, 'Ni': 0.5}"     verifies
  observed: "one site carries Mg 0.5 / Ni 0.5"          does NOT verify

A refutation whose witness does not establish a contradiction is not counted,
and the target it would have recovered scores as missed. Firing unwitnessed
refutations at every compound scores worse than abstaining.

observations: the values you measured, WHETHER OR NOT YOU REFUTE. Most targets
here are values, not flags. Use these exact keys; a value under a name of your
own is kept and not read:

  space_group_number          int, International Tables number of the DEPOSITED file
  space_group_symbol          str, the same determination as a symbol
  cubic_lattice_parameter_a   float, Angstrom. Cubic or PSEUDO-cubic parameter
                              of the deposited cell. State your conversion.
  mixed_cation_sites          int, sites carrying more than one cation species
  target_weight_fraction_pct  float, weight fraction reported for the target phase
  fit_residual_rwp            float, reported fit residual, per cent

Record every one you can compute, not only those your verdict is about.

follow_up: optional. Name one further experiment that would settle what you
could not, using a modality from the menu you were given.
"""

PROMPT_A = """\
You are checking a published scientific claim against the evidence deposited
to support it. You are told nothing about what any expert concluded.

THE CLAIM
{claim}

THE CLAIM RECORD
{record}

THE EVIDENCE (stage one: what the panel had on the day the claim was made)
The deposited crystal structure file, in full, follows at the end of this
message. Its reported refinement is:
{refinement}

You have NO TOOLS. Read the file as text and reason from it.

A REFERENCE CORPUS IS NOT PROVIDED. If your finding would need one, say so in
a `reference-database` finding with verdict "cannot_verify" rather than
guessing what a database would contain.

FOLLOW-UP MENU
{menu}

{contract}

DEPOSITED STRUCTURE FILE: {path}
{cif}
"""

PROMPT_B = """\
You are checking a published scientific claim against the evidence deposited
to support it. You are told nothing about what any expert concluded.

THE CLAIM
{claim}

THE CLAIM RECORD
{record}

THE EVIDENCE (stage one: what the panel had on the day the claim was made)
The deposited crystal structure file is on disk in your working directory as
{basename}. Its reported refinement is:
{refinement}

YOU MAY RUN CODE. Write ONE self-contained Python 3 program. It will be
executed once, in a fresh directory containing only that structure file, with
a {timeout} second wall-clock limit. You will NOT see its output and will not
be asked to revise it, so commit now to what would count as refutation.

Your program must PRINT exactly one line of JSON to stdout: the submission
described below. Anything else it prints is ignored.

The standard library is available. pymatgen, numpy and scipy are available and
may be imported. THERE IS NO NETWORK and no reference corpus on disk; if your
finding would need one, emit a `reference-database` finding with verdict
"cannot_verify" rather than attempting to fetch anything.

FOLLOW-UP MENU
{menu}

{contract}

Return ONLY the Python program. No prose, no markdown fence.
"""

# B2 = B, plus the deposited file inlined exactly as A and C inline it. The
# program still reads the file from disk at run time; seeing it here only lets
# the model write code that fits the data, which is the position a layered
# check is already in.
PROMPT_B2 = PROMPT_B.replace(
    "Return ONLY the Python program. No prose, no markdown fence.",
    "The contents of that file follow, so you can write code that fits it.\n"
    "Your program must still READ IT FROM DISK at run time.\n\n"
    "DEPOSITED STRUCTURE FILE: {basename2}\n{cif}\n\n"
    "Return ONLY the Python program. No prose, no markdown fence.")


def _load_instances(only: str, limit: int, path: Path | None = None) -> list[dict]:
    src = path or INSTANCES
    rows = [json.loads(x) for x in src.read_text().splitlines() if x.strip()]
    if only:
        want = {c.strip() for c in only.split(",")}
        rows = [r for r in rows if r["compound"] in want]
        missing = want - {r["compound"] for r in rows}
        if missing:
            sys.exit(f"unmatched --only names (nothing run): {sorted(missing)}")
    return rows[:limit] if limit else rows


def _menu_text() -> str:
    if not MENU.exists():
        return "(no menu shipped)"
    m = json.loads(MENU.read_text())
    items = m if isinstance(m, list) else m.get("modalities", [])
    return "\n".join(f"  {x.get('modality')}: {x.get('statement','')}"
                     for x in items) or "(empty)"


def build_prompt(inst: dict, condition: str) -> str:
    cif_path = ROOT / inst["evidence_stage_one"]["structure_file"]
    common = dict(
        claim=inst["claim"],
        record=json.dumps(inst["claim_record"], indent=1),
        refinement=json.dumps(inst["evidence_stage_one"].get("refinement"), indent=1),
        menu=_menu_text(),
        contract=CONTRACT,
    )
    if condition == "a":
        return PROMPT_A.format(path=cif_path.name,
                               cif=cif_path.read_text(), **common)
    if condition == "b2":
        return PROMPT_B2.format(basename=cif_path.name,
                                basename2=cif_path.name,
                                cif=cif_path.read_text(),
                                timeout=TIMEOUT_S, **common)
    return PROMPT_B.format(basename=cif_path.name, timeout=TIMEOUT_S, **common)


# ---------------------------------------------------------------- condition B

def run_program(src: str, cif_path: Path) -> tuple[str, str]:
    """Execute a model-written program beside one copy of the structure file.

    NOT A SANDBOX, and condition B is the condition where that is deliberate:
    the whole point is generic tool use with none of the layer's gating. What
    containment exists is the process and the filesystem - a fresh temporary
    directory, the repository not reachable relatively, a credential-scrubbed
    environment, and a wall clock. The child can still open a socket.
    """
    from bench_shim import scrubbed_env
    with tempfile.TemporaryDirectory(prefix="nolayer-") as d:
        w = Path(d)
        shutil.copy2(cif_path, w / cif_path.name)
        (w / "check.py").write_text(src)
        try:
            p = subprocess.run([sys.executable, "check.py"], cwd=str(w),
                               capture_output=True, text=True,
                               env=scrubbed_env(), timeout=TIMEOUT_S)
        except subprocess.TimeoutExpired:
            return "", f"TIMEOUT after {TIMEOUT_S}s"
        return p.stdout, (p.stderr or "")[-400:]


def parse_line(text: str, instance_id: str) -> tuple[dict | None, str]:
    """Recover the submission object from a model reply or a program's stdout."""
    text = re.sub(r"^```(?:json|python)?|```$", "", text.strip(),
                  flags=re.M).strip()
    cands = [x for x in text.splitlines() if x.strip().startswith("{")]
    if not cands:
        m = re.search(r"\{.*\}", text, flags=re.S)
        cands = [m.group(0)] if m else []
    for c in reversed(cands):
        try:
            d = json.loads(c)
        except Exception:
            continue
        if isinstance(d, dict) and "verdict" in d:
            # OVERWRITE, never setdefault. The runner knows which instance it
            # asked about; a model that echoes the bare compound name instead
            # of the instance_id would be rejected by load_submission for a
            # malformed id, which is a formatting failure being scored as a
            # verification failure.
            d["instance_id"] = instance_id
            return d, ""
    return None, "no parseable submission object in the reply"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    ap.add_argument("--condition", required=True, choices=["a", "b", "b2"],
                    help="a = bare, no tools. b = runs code but never sees the "
                         "file. b2 = runs code AND sees the file (compare this "
                         "one against the layer)")
    ap.add_argument("--model", required=True, help="a key from providers.MODELS")
    ap.add_argument("--instances", default="",
                    help="an alternative instance bundle. Use "
                         "data/entrant/instances_contamination.jsonl to run "
                         "the H1/B1 contamination set through the unlayered "
                         "conditions. The bundle carries no label: which file "
                         "is healed and which is broken lives in "
                         "results/contamination_set.csv, joined by id.")
    ap.add_argument("--only", default="", help="comma-separated compounds")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--max-tokens", type=int, default=8000)
    ap.add_argument("--fill", action="store_true",
                    help="buy only instances with no reply on disk")
    ap.add_argument("--dry-run", action="store_true",
                    help="build and print one prompt; spend nothing")
    a = ap.parse_args()

    rows = _load_instances(a.only, a.limit,
                           Path(a.instances) if a.instances else None)
    if a.dry_run:
        p = build_prompt(rows[0], a.condition)
        print(p)
        print(f"\n--- {len(p)} characters, {len(rows)} instances would be bought ---",
              file=sys.stderr)
        return 0

    tag = ""
    if a.instances:
        tag = "-" + Path(a.instances).stem.replace("instances_", "")
    out = OUT / f"{a.condition}-{a.model}{tag}"
    if out.exists() and any(out.glob("*.reply.txt")) and not a.fill:
        n = len(list(out.glob("*.reply.txt")))
        sys.exit(
            f"REFUSING TO RUN: {out} already holds {n} purchased replies.\n"
            f"Running here without --fill would overwrite them, which destroys\n"
            f"paid elicitations and breaks the seal (one completion per "
            f"instance).\n\n  to complete this run: add --fill")
    out.mkdir(parents=True, exist_ok=True)

    # MODEL ACCESS IS NOT PART OF THIS BENCHMARK. `providers` is the layer's
    # API client and needs credentials; it does not ship, and re-implementing
    # it here would put key handling in a repository that has no business
    # holding keys. Conditions A and B need model calls, so they need it. The
    # scoring path does not, and neither does any entrant: a submission is
    # produced by your own verifier and scored by tools/score_submission.py.
    try:
        import providers
    except ImportError:
        raise SystemExit(
            "this runner elicits from a model and needs `providers`, the "
            "layer's API client.\nIt is not part of the benchmark. Nothing an "
            "entrant does requires it - write your\nsubmission with your own "
            "verifier and score it with tools/score_submission.py.")
    subs, problems = [], []
    for i, inst in enumerate(rows, 1):
        cid = inst["compound"].replace("/", "_")
        rp = out / f"{cid}.reply.txt"
        if a.fill and rp.exists() and rp.read_text().strip():
            reply = rp.read_text()
            meta = None
        else:
            prompt = build_prompt(inst, a.condition)
            t0 = time.monotonic()
            try:
                comp = providers.complete(a.model, prompt,
                                          max_tokens=a.max_tokens)
            except Exception as exc:
                problems.append(f"{inst['compound']}: elicitation failed "
                                f"({type(exc).__name__})")
                print(f"[{i}/{len(rows)}] {inst['compound']}: FAILED "
                      f"{type(exc).__name__}")
                continue
            reply = comp.text
            rp.write_text(reply)
            meta = comp.cost_meta()
            meta["wall_clock_s"] = round(time.monotonic() - t0, 2)
            (out / f"{cid}.meta.json").write_text(json.dumps(meta, indent=1))

        if a.condition in ("b", "b2"):
            cif = ROOT / inst["evidence_stage_one"]["structure_file"]
            stdout, err = run_program(reply, cif)
            (out / f"{cid}.stdout.txt").write_text(stdout or f"[stderr] {err}")
            d, why = parse_line(stdout, inst["instance_id"])
            if d is None:
                why = f"{why}; program stderr: {err}" if err else why
        else:
            d, why = parse_line(reply, inst["instance_id"])

        if d is None:
            problems.append(f"{inst['compound']}: {why}")
            print(f"[{i}/{len(rows)}] {inst['compound']}: unparseable - {why}")
            continue
        subs.append(d)
        cls = [f.get("evidence_class") for f in (d.get("findings") or [])]
        print(f"[{i}/{len(rows)}] {inst['compound']}: {d.get('verdict')} "
              f"| classes {cls or '-'} "
              f"| observations {len(d.get('observations') or {})}")

    sp = out / "submission.jsonl"
    sp.write_text("\n".join(json.dumps(x) for x in subs) + "\n")
    print(f"\nwrote {sp}  ({len(subs)} of {len(rows)} instances)")
    if problems:
        print(f"\n{len(problems)} instance(s) produced no submission line. "
              f"These are NOT scored as wrong - they are absent, and the "
              f"scorebook reports coverage separately:")
        for x in problems[:20]:
            print(f"  {x}")
    print(f"\nscore it with:\n  .venv/bin/python tools/score_submission.py {sp}")
    print(f"\nCompare against the layered arm through the SAME route:\n"
          f"  .venv/bin/python tools/ledger_to_submission.py \\\n"
          f"      results/chain/<arm>-gen2/rebuilt/children_rebuilt_budget1e+07.csv \\\n"
          f"      --out /tmp/layered.jsonl\n"
          f"  .venv/bin/python tools/score_submission.py /tmp/layered.jsonl")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

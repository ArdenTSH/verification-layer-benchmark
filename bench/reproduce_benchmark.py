"""
THE REPRODUCTION HARNESS. Deterministic, model-free, ungated: attempts every
claim the benchmark declares re-derivable, and reports pass or fail.

The layer is a reproduction instrument. This script is the direct test of that:
for each published quantity the benchmark says can be recomputed from material
we hold, it recomputes it and compares. Nothing here interprets a result, and
nothing here asserts anything about chemistry. Each item either reproduces the
published number or does not.

What is attempted, and where the benchmark declares it:

  R1  the populations and the counting rule                    section 3
  R2  the critique's printed error-flag totals                 sections 4.7, 5.1
  R3  the file scan against the critique's E2 flags            section 5.5
  R4  the critique's FINDSYM column                            sections 4.8, 9.1
  R5  the critique's Table II lattice parameters               transcribed 27 Aug
  R6  CARTOGRAPH, the external baseline                        section 4.11
  R7  the mutant demonstration set                             section 6.2
  R8  the rival files against their manifest hashes            section 8.2

R5 is attempted although the benchmark does not mention it: the critique's
Table II prints a cubic lattice parameter per pyrochlore derived from the
A-Lab CIF, and this project has never transcribed that table. It is included
so the omission is visible in the same place as everything else.

What is NOT attempted, because the benchmark rules it out:

  E1, the critique's fit-quality flag: its evidence was never deposited, so no
  one can re-derive it (sections 4.4, 9.1).
  The Correction's own analysis: this project holds no copy of the Correction,
  only a transcription of its per-compound verdicts, so there is nothing to
  recompute against.

Usage:
  .venv/bin/python bench/reproduce_benchmark.py
  .venv/bin/python bench/reproduce_benchmark.py --only R4,R6
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import math
import re
import sys
import warnings
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "bench"))
sys.path.insert(0, str(ROOT / "tools"))
warnings.filterwarnings("ignore")

LABELS = ROOT / "data" / "labels" / "merged_labels.csv"
ERRORS = ROOT / "data" / "labels" / "prx_table1_errors.csv"
TABLE3 = ROOT / "data" / "labels" / "prx_table3.csv"
RESULTS = []


def check(item, name, published, ours, ok, note=""):
    RESULTS.append((item, ok))
    mark = "PASS" if ok else "FAIL"
    print(f"  [{mark}] {name}")
    print(f"         published: {published}")
    print(f"         ours     : {ours}")
    if note:
        print(f"         note     : {note}")


def observe(name, published, ours, note=""):
    """Report a comparison WITHOUT a pass/fail stamp.

    Some comparisons have no correctness standard this project may set. Two
    independent symmetry programs disagreeing on one structure is such a case:
    calling it a failure would mean declaring one of them right about that
    compound, which is a crystallographic judgement, and this layer makes
    none. The agreement count and the tolerance it holds at are reported, the
    disagreements are named, and no verdict is attached.
    """
    print(f"  [ OBS] {name}")
    print(f"         published: {published}")
    print(f"         ours     : {ours}")
    if note:
        print(f"         differs  : {note}")


def rows():
    return list(csv.DictReader(LABELS.open()))


def flags():
    with ERRORS.open() as fh:
        return list(csv.DictReader(x for x in fh if not x.startswith("#")))


# --------------------------------------------------------------------- R1
def R1():
    print("\nR1  the populations and the counting rule (section 3)")
    r = rows()
    adjudicated = [x for x in r if x["correction_verdict"] in
                   ("confirmed", "inconclusive")]
    conf = sum(1 for x in adjudicated if x["correction_verdict"] == "confirmed")
    inc = sum(1 for x in adjudicated
              if x["correction_verdict"] == "inconclusive")
    pairs = sum(1 for x in r if x.get("auto_cif_resolved") == "True")
    check("R1a", "40 adjudicated claims, 36 confirmed and 4 inconclusive",
          "40 = 36 + 4", f"{len(adjudicated)} = {conf} + {inc}",
          (len(adjudicated), conf, inc) == (40, 36, 4))
    check("R1b", "42 deposited structure-file pairs", "42",
          f"{pairs} rows with a resolved automated file", pairs == 42)
    check("R1c", "36 products in the critique's error table", "36",
          f"{len(flags())}", len(flags()) == 36)
    check("R1d", "43 bookkeeping rows", "43", f"{len(r)}", len(r) == 43)


# --------------------------------------------------------------------- R2
def R2():
    print("\nR2  the critique's printed error-flag totals (sections 4.7, 5.1)")
    f = flags()
    got = {k: sum(1 for x in f if x[c] == "1") for k, c in
           (("E1", "e1_poor_fit"), ("E2", "e2_cif_differs"),
            ("E3", "e3_no_ordering_evidence"), ("E4", "e4_already_known"))}
    want = {"E1": 18, "E2": 8, "E3": 24, "E4": 3}
    check("R2", "the transcription reproduces the printed totals",
          str(want), str(got), got == want)


# --------------------------------------------------------------------- R3
def R3():
    print("\nR3  the file scan against the critique's E2 flags (section 5.5)")
    r = rows()
    scan = {x["compound"] for x in r if x["scan_auto_disordered"] == "1"}
    e2 = {x["compound"] for x in r if x["prx_e2"] == "1"}
    check("R3a", "the scan flags 10 of the 42 deposited automated files",
          "10 of 42", f"{len(scan)} of 42", len(scan) == 10)
    check("R3b", "the scan recovers 7 of the critique's 8 E2 flags",
          "7 of 8", f"{len(scan & e2)} of {len(e2)}",
          len(scan & e2) == 7 and len(e2) == 8,
          f"E2 not recovered: {sorted(e2 - scan)}")


# --------------------------------------------------------------------- R4
def R4():
    print("\nR4  the critique's FINDSYM column, recomputed (sections 4.8, 9.1)")
    import bench_shim as library
    r = rows()
    # JOIN BY COMPOSITION, not by printed name. Fixed 27 Aug 2026. The
    # critique's Table III spells two formulas with their elements in a
    # different order from the bookkeeping table - Table III's
    # Ba6Na2Ta2V2O17 is our Ba6Ta2Na2V2O17, its Y3In2Ga3O12 is our
    # Y3Ga3In2O12 - so a name join silently dropped two determinations and
    # this item reported 40 comparisons where the record holds 43. It is the
    # SAME fault class as the file lookup that could only open 40 of 42
    # deposited pairs: a composition written two ways. That was fixed in
    # resolve_cif on 26 Aug and the label join was missed.
    from bench_shim import norm_formula
    paths = {norm_formula(x["compound"]): x["auto_cif"] for x in r
             if x.get("auto_cif_resolved") == "True"}
    want = {}
    with TABLE3.open() as fh:
        for x in csv.DictReader(y for y in fh if not y.startswith("#")):
            m = re.search(r"\((\d{1,3})\)", x.get("indexed_sym", "") or "")
            if m:
                want[x["sample"]] = int(m.group(1))
    for symprec in (0.01, 0.1):
        agree, tried, miss = 0, 0, []
        for c, w in want.items():
            p = paths.get(norm_formula(c))
            if not p:
                continue
            try:
                got = library.space_group_number(
                    library.load_structure(str(ROOT / p)), symprec)
            except Exception:
                continue
            tried += 1
            if got == w:
                agree += 1
            else:
                miss.append(f"{c} theirs {w} ours {got}")
        # no pass/fail: see observe(). Symmetry determination from refined
        # coordinates depends on a declared tolerance, and the critique's
        # program is not ours, so exact agreement on every structure would be
        # the surprising outcome rather than the expected one.
        observe(f"the symmetry the critique computed, at symprec {symprec}",
                f"{tried} printed determinations",
                f"{agree} of {tried} agree", "; ".join(miss) if miss else "none")


# --------------------------------------------------------------------- R5
def R5():
    print("\nR5  the critique's Table II lattice parameters "
          "(transcribed, two methods)")
    import bench_shim as library
    from bench_shim import find_cif
    R2_ = math.sqrt(2)
    # read from the transcription, not hardcoded here: a published value the
    # harness carries in its own source is not a transcription anyone can audit
    t2 = ROOT / "data" / "labels" / "prx_table2.csv"
    printed = {}
    with t2.open() as fh:
        for x in csv.DictReader(y for y in fh if not y.startswith("#")):
            if x["alab_cubic_a"]:
                printed[x["compound"]] = float(x["alab_cubic_a"])
    conv = {
        "mean(a,b)*sqrt2": lambda a, b, c, V: (a + b) / 2 * R2_,
        "c": lambda a, b, c, V: c,
        "(4V/3)^(1/3)": lambda a, b, c, V: (4 / 3 * V) ** (1 / 3),
    }
    hits = 0
    detail = []
    for cmp, w in printed.items():
        try:
            s = library.load_structure(find_cif(cmp))
            a, b, c = s.lattice.abc
            found = [n for n, fn in conv.items()
                     if abs(fn(a, b, c, s.volume) - w) <= 0.0005]
            if found:
                hits += 1
                detail.append(f"{cmp} via {found[0]}")
            else:
                detail.append(f"{cmp} NO MATCH")
        except Exception as exc:
            detail.append(f"{cmp} failed {type(exc).__name__}")
    check("R5", "the cubic lattice parameter derived from each A-Lab CIF",
          "5 printed values", f"{hits} of 5 reproduced to 0.0005 A",
          hits == 5, "; ".join(detail))


# --------------------------------------------------------------------- R6
def R6():
    print("\nR6  CARTOGRAPH, the external baseline (section 4.11)")
    from reproduce_baselines import phase_fractions, percentile, rho_alab
    r = rows()
    ev = [x for x in r if x["correction_verdict"] in
          ("confirmed", "inconclusive")]
    inc = {x["compound"] for x in ev
           if x["correction_verdict"] == "inconclusive"}
    con = {x["compound"] for x in ev
           if x["correction_verdict"] == "confirmed"}
    frac = phase_fractions()
    rho = {x["compound"]: rho_alab(frac.get(x["compound"], {})) for x in ev}
    hit = {c for c, v in rho.items() if v is not None and v > 0.776}
    four = sorted(hit & inc)
    published_four = ["CaGd2Zr(GaO3)4", "KBaGdWO6", "Mg3MnNi3O8",
                      "Mn7(P2O7)4"]
    check("R6a", "the four inconclusive claims it flags, by name",
          str(published_four), str(four), four == published_four)
    check("R6b", "confirmed claims passed", "32 of 36",
          f"{36 - len(hit & con)} of 36", len(hit & con) == 4)
    d = percentile([rho[c] for c in con if rho.get(c) is not None], 0.95)
    check("R6c", "the calibration constant", "0.776, bootstrap [0.496, 1.088]",
          f"{d:.4f}", 0.496 <= d <= 1.088,
          "inside their published interval; not equal to their point value")
    b = {c: (None if frac.get(c, {}).get("rwp_manual") is None
             else frac[c]["rwp_manual"] / 20.0) for c in rho}
    t = percentile([b[c] for c in con if b.get(c) is not None], 0.95)
    h = {c for c, v in b.items() if v is not None and v > t}
    check("R6d", "the Rwp-only ablation", "0 of 4 and 2 of 36",
          f"{len(h & inc)} of 4 and {len(h & con)} of 36",
          len(h & inc) == 0 and len(h & con) == 2)


# --------------------------------------------------------------------- R7
def R7():
    print("\nR7  the mutant demonstration set (section 6.2)")
    # THE SHIPPED SET IS THE ONE UNDER TEST. `data/mutants_demo.csv` is what
    # the benchmark distributes; `results/` is where a fresh generation lands
    # and is gitignored, so looking only there failed R7 in every checkout.
    p = ROOT / "data" / "mutants_demo.csv"
    if not p.exists():
        p = ROOT / "results" / "mutants_demo.csv"
    if not p.exists():
        check("R7", "the mutant set", "7 mutants", "file absent", False)
        return
    m = [x for x in csv.DictReader(p.open())]
    live = [x for x in m if x.get("excluded_equivalent") != "True"]
    prices = [float(x["difficulty_n_star"]) for x in live
              if x["difficulty_n_star"]]
    # R7a tests the property the mutant set exists to have, not its size.
    #
    # The benchmark's rule is that a claim handed to a model never contains its
    # own answer (section 6.2): the truth of a mutant lives in this table,
    # joined by id at analysis time, and never on any surface the model reads.
    # That is the only thing about the set that can be wrong in a way that
    # matters, and it is what makes a planted-truth instance usable at all.
    #
    # A count is not that property. Comparing a number in this file against a
    # file our own generator writes tests that we did not change our generator,
    # which is a statement about us and not about the record - the same
    # objection R5 states about a published value the harness carries in its
    # own source.
    truthed = [x for x in m if (x.get("truth") or "").strip()]
    hashed = [x for x in m if (x.get("evidence_sha256") or "").strip()]
    fams = sorted({x.get("family", "") for x in m if x.get("family")})
    check("R7a", "every mutant carries its truth OUTSIDE the claim, and its "
          "evidence by hash",
          "truth and hash on every row, more than one family",
          f"{len(truthed)} of {len(m)} truthed, {len(hashed)} of {len(m)} "
          f"hashed, families {','.join(fams)}",
          bool(m) and len(truthed) == len(m) and len(hashed) == len(m)
          and len(fams) > 1)
    check("R7b", "decision prices span 51 to 1,650,000 counts",
          "51 to 1.65e6",
          f"{min(prices):.0f} to {max(prices):.3g}" if prices else "none",
          bool(prices) and min(prices) < 60 and max(prices) > 1.6e6)

    # R7c RESOLVES the hashes R7a only counts. Carrying a hash and carrying the
    # file it names are different properties, and the second is the one that
    # makes the truth table joinable: a row whose hash does not resolve has no
    # evidence, whatever its label says. Both constructed sets write to
    # data/mutants/<compound>/<compound>.cif, so a compound in both has one file
    # and two labels - which is how the demonstration set's Ba2ZrSnO6 came to
    # point at the contamination set's healed file, asserting the reverse of its
    # own truth. Rows whose evidence is the deposit are skipped, not failed:
    # the deposit is fetched, not shipped.
    resolved = stale = absent = 0
    for x in m:
        uri, want = x.get("evidence_uri", ""), x.get("evidence_sha256", "")
        if not uri or not want:
            continue
        f = ROOT / uri
        if uri.startswith("data/cifs/"):
            continue                      # the un-redistributed deposit
        if not f.exists():
            absent += 1
        elif hashlib.sha256(f.read_bytes()).hexdigest() == want:
            resolved += 1
        else:
            stale += 1
    check("R7c", "every recorded hash resolves to the file it names",
          "each shipped mutant's evidence present and matching",
          f"{resolved} resolve, {stale} present but DIFFERENT, {absent} absent",
          stale == 0 and absent == 0)


# --------------------------------------------------------------------- R8
def R8():
    print("\nR8  the rival files against their manifest hashes (section 8.2)")
    man = ROOT / "data" / "rivals" / "MANIFEST.md"
    if not man.exists():
        check("R8", "the rival manifest", "hashes for every shipped file",
              "MANIFEST.md absent", False)
        return
    text = man.read_text()
    pairs = re.findall(r"([\w./-]+\.cif)[^\n]*?([0-9a-f]{64})", text)
    if not pairs:
        pairs = [(m2, m1) for m1, m2 in
                 re.findall(r"([0-9a-f]{64})[^\n]*?([\w./-]+\.cif)", text)]
    # SHIPPED means shipped. The manifest also records the ICSD entries fetched
    # under institutional access, which .gitignore excludes because they may not
    # be redistributed - so requiring every hashed entry to be present failed R8
    # in every clean checkout, for the one reason that is by design. They are
    # counted and named as withheld, which is what a licence holder needs in
    # order to re-fetch by code and confirm the hash themselves.
    ok = bad = missing = withheld = 0
    for name, want in pairs:
        cands = list((ROOT / "data" / "rivals").rglob(Path(name).name))
        if not cands:
            if name.startswith("icsd/"):
                withheld += 1
            else:
                missing += 1
            continue
        got = hashlib.sha256(cands[0].read_bytes()).hexdigest()
        ok += got == want
        bad += got != want
    check("R8", "every shipped rival file matches its recorded hash",
          f"{len(pairs) - withheld} redistributable entries "
          f"({withheld} withheld under licence)",
          f"{ok} match, {bad} differ, {missing} not found",
          bool(pairs) and bad == 0 and missing == 0)


def rate(ledger_path: str):
    """THE BENCHMARK RATING: how much of the ceiling an arm actually climbed.

    SUPERSEDED, AND KEPT ONLY FOR ITS REASONING. This mode read a TIERED
    ceiling key - tiers A, B and C - which the per-target scorebook replaced
    and which this repository does not ship. See the note at the head of
    `bench/score_targets.py` on why one number over mixed denominators was the
    wrong shape. Use `tools/score_submission.py` instead. The docstring stays
    because the two rules in its last paragraph still govern the scorebook.

    IT REFUSES UNCONDITIONALLY, and that is deliberate. The tiered key was
    called `ceiling.json`, and on 29 August 2026 the CURRENT key was renamed
    from `ceiling_v2.json` to that same name. So the path this mode used to
    read now resolves to a file with a different schema. Checking whether the
    file exists is no longer a safe guard - it exists, and it is the wrong
    one - so the mode does not read it at all.

    The ceiling is the set of expert findings recoverable from the deposit.
    Tier A was the target list:
    derivable from the deposited files AND expressible in the check
    vocabulary, so a model-written check can reach it. Tier B is derivable but
    not expressible, because no primitive exposes the refinement table - that
    is a rung this project has not built, and it is reported as out of
    vocabulary rather than as a miss. Tier C is above the ceiling for everyone
    and is excluded from every denominator.

    Two rules keep the number honest. The denominator is the experts': a flag
    the layer raises that no expert asserted is a false alarm, never a
    discovery. And nothing is hand-held: the model is never told what the
    experts found, so a recovery counts only if the layer arrived at it from
    the claim and the file.
    """
    raise SystemExit(
        "--rate is superseded and its key is not shipped.\n"
        "It produced ONE number across groups with different expert "
        "denominators; the per-target\n"
        "scorebook replaced it. Its tiered key was named ceiling.json, which "
        "is now the name of the\n"
        "CURRENT key with a different schema, so this mode does not read that "
        "path at all.\n\nScore a submission with:\n\n"
        "    .venv/bin/python tools/score_submission.py <submission>.jsonl")
    led = list(csv.DictReader(Path(ledger_path).open()))
    r = rows()
    lab = {x["compound"]: x for x in r}
    inled = {x["compound"] for x in led}
    # a compound with no check ever elicited is not a result either way
    examined = {x["compound"] for x in led
                if int(x.get("checks_missing") or 0) < int(
                    x.get("checks_total") or 1)}
    flagged = {x["compound"] for x in led if x["verdict"] == "refuted"}
    flagged &= examined

    print(f"\nBENCHMARK RATING - {Path(ledger_path).name}")
    print(f"  compounds in ledger {len(inled)}; examined {len(examined)}; "
          f"the layer flags {len(flagged)}")

    e2 = {c for c, x in lab.items() if x["prx_e2"] == "1"} & examined
    hit = flagged & e2
    print(f"\n  TIER A - the target list")
    print(f"    A2  E2, file differs from the claim : "
          f"{len(hit)} of {len(e2)} recovered")
    if e2 - hit:
        print(f"          not recovered: {', '.join(sorted(e2 - hit))}")
    # A1: did the ARM recover a symmetry finding? The critique determined a
    # symmetry per deposited file; where that differs from the claimed group,
    # the file contradicts the claim and a check could reach it. Scored on the
    # subset where the critique's own determination differs from the claim, so
    # the target is a finding rather than an agreement.
    import re as _re
    claimed, indexed = {}, {}
    with (ROOT / "data" / "labels" / "prx_table3.csv").open() as fh:
        for x in csv.DictReader(y for y in fh if not y.startswith("#")):
            cm = _re.search(r"\((\d{1,3})\)", x.get("proposed_sym", "") or "")
            im = _re.search(r"\((\d{1,3})\)", x.get("indexed_sym", "") or "")
            if cm and im:
                claimed[x["sample"]] = int(cm.group(1))
                indexed[x["sample"]] = int(im.group(1))
    a1_targets = {c for c in claimed
                  if claimed[c] != indexed[c]} & examined
    a1_hit = a1_targets & flagged
    print(f"    A1  symmetry differs from the claim : "
          f"{len(a1_hit)} of {len(a1_targets)} recovered")
    if a1_targets - a1_hit:
        miss = sorted(a1_targets - a1_hit)
        print(f"          not recovered: {', '.join(miss[:8])}"
              + (" ..." if len(miss) > 8 else ""))
    overlap = e2 & a1_targets
    if overlap:
        print(f"          NOTE {len(overlap)} of the A1 targets are also "
              f"E2-flagged, so A1 adds no")
        print(f"          independent denominator here; the union is "
              f"{len(e2 | a1_targets)} compounds")
    print(f"    A3  Table II lattice parameters     : "
          f"transcribed (data/labels/prx_table2.csv), 5 values; not an "
          f"arm-level")
    print(f"                                          target - it is a "
          f"derived quantity, not a per-compound finding")
    print(f"    A4  prose structural claims         : "
          f"7 of ~30 not transcribed; not yet a target")

    fa = flagged - {c for c, x in lab.items()
                    if x["prx_e2"] == "1" or x["prx_e4"] == "1"}
    print(f"\n  FALSE ALARMS (flagged, no expert assertion): "
          f"{len(fa)} of {len(flagged)} flags"
          + (f" - {', '.join(sorted(fa))}" if fa else ""))

    print(f"\n  TIER B - out of vocabulary, not counted as misses")
    for k, v in ceiling["tiers"]["B"]["items"].items():
        print(f"    {k}: {v['kind']}")
    print(f"    reason: {ceiling['tiers']['B']['why_not'][:96]}...")

    print(f"\n  TIER C - above the ceiling, excluded from all denominators")
    for k, v in ceiling["tiers"]["C"]["items"].items():
        print(f"    {k}")

    # the wired target is the union of A1 and A2: both are per-compound
    # findings a check could reach from the deposited file
    targets = e2 | a1_targets
    hits = targets & flagged
    print(f"\n  RATING: {len(hits)}/{len(targets)} of the wired Tier A target "
          f"({100 * len(hits) / len(targets):.0f}%), with {len(fa)} false "
          f"alarms")
    print(f"    A1 and A2 are wired. A3 (5 lattice parameters, now "
          f"transcribed) and A4")
    print(f"    (7 prose claims, not transcribed) are reproducible "
          f"deterministically and are")
    print(f"    not yet scored per arm, so this rating still covers only part "
          f"of Tier A.")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default="")
    ap.add_argument("--rate", default="",
                    help="score a chain ledger against the ceiling")
    args = ap.parse_args()
    if args.rate:
        rate(args.rate)
        return 0
    want = {x.strip().upper() for x in args.only.split(",") if x.strip()}
    print("REPRODUCTION HARNESS - every claim the benchmark declares "
          "re-derivable")
    print("no model calls; nothing here interprets a result or asserts "
          "chemistry")
    for fn in (R1, R2, R3, R4, R5, R6, R7, R8):
        if want and fn.__name__ not in want:
            continue
        try:
            fn()
        except Exception as exc:
            print(f"\n{fn.__name__}  ERRORED: {type(exc).__name__}: {exc}")
            RESULTS.append((fn.__name__, False))
    passed = sum(1 for _, ok in RESULTS if ok)
    print(f"\n{'=' * 62}")
    print(f"reproduced {passed} of {len(RESULTS)} attempted checks")
    failed = [n for n, ok in RESULTS if not ok]
    if failed:
        print(f"not reproduced: {', '.join(failed)}")
    print("not attempted: E1 (evidence never deposited); the Correction's own")
    print("analysis (this project holds no copy, only a verdict "
          "transcription)")
    # The exit status is the only part of this a machine reads. Printing FAIL
    # and returning 0 tells CI, and every `&&` in a shell, that the
    # reproduction succeeded. Any failed check makes the status non-zero.
    #
    # Note what this means in the shipped state: R7c fails by design - the
    # Ba2ZrSnO6 mutant's label is the opposite of its truth, recorded in
    # docs/known-defects.md - so a correct checkout exits 1 until that is
    # repaired. That is the honest reading: a declared-reproducible check does
    # not reproduce. If a known defect should stop poisoning the status, name
    # it explicitly rather than returning 0 for everything.
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())

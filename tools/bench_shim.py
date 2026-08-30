"""The layer-owned code the BENCHMARK needs, copied so the benchmark can ship
without the layer.

WHY THIS FILE EXISTS AT ALL.

The benchmark and the layer are being separated into two repositories. The
benchmark is the artifact a stranger runs to score their own verifier; the
layer is our verifier, which is one entrant among others. A benchmark that
imports the thing it scores is not a benchmark - the entrant would have to
install our verifier to be measured against it, and any change we made to our
verifier would silently move the scale everyone else is measured on.

Six small call sites in the benchmark surface reached into layer modules. Each
pulled in far more than it used: `aggregate.witness_reproduced` is a 32-line
subprocess wrapper around `tools/check_witness.py`, but importing `aggregate`
executes `claim.py` and `decide.py` at module scope - about 1285 lines of
decision machinery the scorer never calls. `library.refinement_row` reads a
spreadsheet, but importing `library` executes `disorder`, `simulate` and
`distinguish`, the physics core of the layer.

That reasoning was applied to the imports and not to the file. `bench/library.py`
shipped anyway - for the mutant generator, which is the only thing that imports
it - and carried the layer's own refinement-row reader beside the copy below,
dead and with an unresolvable `import followups` inside it. Stripped 29 August
2026: `bench/library.py` now holds only what the generator uses, and the
refinement row lives here and nowhere else in this repository.

So the functions are COPIED HERE, NOT IMPORTED. Copying is the right call
rather than the lazy one because the copied code is small, closed, and reads
only data files that travel with the benchmark. The alternative - importing
across the repository boundary - would make the benchmark depend on the
verifier it scores, which is the coupling the split exists to remove.

WHAT IS COPIED, AND FROM WHERE.

`src/` below is the LAYER REPOSITORY's source tree, not a path in this one -
these line numbers locate each function where it was copied from, and that
repository is deliberately not shipped here. Some of those modules were
extracted into `bench/` alongside this file (`build_labels`, `library`); the
citations still name the origin, because what they record is provenance and
not a place to go looking.

  witness_reproduced      src/aggregate.py:77    verbatim
  WITNESS_CHECKER         src/aggregate.py:64    repointed at this file's tree
  Claim                   src/claim.py:60        REDUCED - see the note on it
  resolve_cif             src/build_labels.py:48 verbatim
  norm_formula            src/build_labels.py:79 verbatim
  refinement_row          src/library.py:375     verbatim but for its imports
  _refinement_table       src/library.py:353     verbatim but for its imports
  _parse_refinement_cell  src/library.py:306     verbatim
  _phase_core             src/library.py:278     verbatim
  _STAGE_COLUMN           src/library.py:275     verbatim
  load_structure          src/library.py:61      verbatim
  MENU                    src/followups.py:56    verbatim
  CONTAMINATION_NOTE      src/followups.py:132   verbatim
  scrubbed_env            src/isolate.py:105     verbatim

"Verbatim but for its imports" means the body is unchanged and the only edits
are to the import lines, which used to reach into sibling layer modules and now
resolve inside this file.

DEPENDENCIES ARE KEPT AS THE ORIGINAL HAD THEM.

`witness_reproduced` and everything it touches is stdlib-only, exactly as in
`aggregate.py`, and stays that way: it shells out to `tools/check_witness.py`,
which is itself stdlib-only, so the witness-adjudication path of the scorer
runs with no third-party package at all.

`refinement_row` and `load_structure` are NOT stdlib and are not made so.
`refinement_row` needs pandas and openpyxl to read the deposited refinement
workbook, `_phase_core` and `norm_formula` need pymatgen to compare
compositions, and `load_structure` needs pymatgen to read a structure file.
Re-implementing composition parsing to avoid pymatgen would be exactly the
reimplementation-instead-of-reuse failure this project keeps naming, and the
scorer already requires all three packages. So they are imported inside the
functions that need them, which is where the originals imported them too - the
stdlib-only witness path never touches them.

THIS FILE IS A COPY AND WILL DRIFT.

Nothing here is generated, and nothing keeps it in step with the layer. That is
accepted: after the split these are two separate programs that happen to have
shared an ancestor, and the benchmark's copy is the definition the benchmark is
scored by. `tools/check_witness.py` is the one piece NOT copied - both the
layer and the benchmark shell out to the same file, so the adjudication a
submission gets and the one our own arms get cannot drift apart.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from dataclasses import dataclass
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# from src/aggregate.py:64 - the standalone checker, which is NOT copied: the
# layer and the benchmark run the same file so their adjudications cannot drift
WITNESS_CHECKER = ROOT / "tools" / "check_witness.py"


# ------------------------------------------------------------------- claim
#
# from src/claim.py:60, REDUCED TO WHAT IS READ.
#
# The layer's Claim carries eight fields and is the envelope its whole decision
# path is built on: evidence refs, provenance, context, a parent pointer for
# decompositions, and a versions dict. `witness_reproduced` serialises exactly
# three of them - id, family, assertion - into the JSON it hands the checker,
# and the scorer builds a Claim for no other purpose.
#
# Copying all eight would drag `Ref` and `ENVELOPE_VERSION` and imply the
# benchmark has a claim envelope, which it does not: an entrant is never shown
# our decomposition and the scorer never decomposes anything. So this carries
# the three fields that are read and nothing else. It is deliberately NOT the
# layer's Claim and should not grow back toward it.

@dataclass(frozen=True)
class Claim:
    id: str          # the instance id, echoed into the checker's claim record
    family: str      # the evidence class the witness is adjudicated under
    assertion: dict  # payload; the checker reads assertion["compound"]


# from src/isolate.py:60,105. Carried here 29 August 2026 because
# `tools/run_nolayer.py` imported `isolate` for this one function and the module
# does not ship, so the ablation runner could not start. It is eleven lines of
# stdlib and it is credential handling, which is the last thing that should be
# reimplemented slightly differently in a second place.
_SECRET_HINTS = ("KEY", "TOKEN", "SECRET", "PASSWORD", "CREDENTIAL", "COOKIE",
                 "SESSION", "AUTH")


def scrubbed_env() -> dict:
    """A copy of the environment with anything credential-shaped removed."""
    import os
    out = {}
    for k, v in os.environ.items():
        if any(h in k.upper() for h in _SECRET_HINTS):
            continue
        out[k] = v
    # belt and braces: the project's own variable, by name, whatever it is
    out.pop("FOUNDRY_API_KEY", None)
    out.pop("AZURE_OPENAI_API_KEY", None)
    out.pop("ANTHROPIC_API_KEY", None)
    out.pop("OPENAI_API_KEY", None)
    return out


# ------------------------------------------------------- witness adjudication

def witness_reproduced(witness, cif_path: str | Path,
                       claim: Claim | None = None) -> bool | None:
    """Run the standalone checker. True/False = its verdict; None = the
    checker could not judge (unsupported class or bad input, exit 2).

    The claim record is passed through so family-level requirements are
    adjudicated against what was CLAIMED, not against the witness's own
    'required' text - which the untrusted model that wrote the check also
    wrote, and so cannot be the standard the contradiction is tested against.
    """
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as fh:
        json.dump({"where": witness.where, "observed": witness.observed,
                   "required": witness.required}, fh)
        wpath = fh.name
    cpath = None
    if claim is not None:
        with tempfile.NamedTemporaryFile("w", suffix=".json",
                                         delete=False) as ch:
            json.dump({"id": claim.id, "family": claim.family,
                       "assertion": claim.assertion}, ch)
            cpath = ch.name
    try:
        cmd = [sys.executable, str(WITNESS_CHECKER), wpath, str(cif_path)]
        if cpath:
            cmd.append(cpath)
        r = subprocess.run(cmd, capture_output=True, timeout=60)
        return {0: True, 1: False}.get(r.returncode)
    finally:
        Path(wpath).unlink(missing_ok=True)
        if cpath:
            Path(cpath).unlink(missing_ok=True)


# ------------------------------------------------------------ file resolution

def norm_formula(name: str) -> str:
    """Composition-normalised join key, tolerant of permuted formulas.

    from src/build_labels.py:79
    """
    try:
        from pymatgen.core import Composition
        return Composition(name).reduced_formula
    except Exception:
        return name.strip()


def resolve_cif(stage: str, name: str) -> Path:
    """Find a compound's deposited file, by name first and by COMPOSITION when
    the name misses.

    from src/build_labels.py:48

    The deposit and the Correction's spreadsheet do not always spell a formula
    with its elements in the same order: the spreadsheet's Ba6Ta2Na2V2O17 is
    the deposit's folder Ba6Na2Ta2V2O17, and the folder Y3Ga3In2O12 contains a
    file named Y3In2Ga3O12.cif. Building the path from the spreadsheet name
    alone therefore missed two of the 42 deposited pairs, and one of them,
    Ba6Ta2Na2V2O17, is in the evaluation population - so every check on it was
    skipped for want of evidence and its ledger row read as a verdict rather
    than as an absence.

    Section 5.3 of the benchmark already described this fallback as the way the
    pair is resolved; it did not exist in the code until 26 August 2026. The
    composition comparison is the same normalisation used to join the label
    tables to each other.
    """
    root = ROOT / "data" / "cifs" / stage
    direct = root / name / f"{name}.cif"
    if direct.exists():
        return direct
    want = norm_formula(name)
    if not root.exists():
        return direct
    for cand in sorted(root.rglob("*.cif")):
        if norm_formula(cand.stem) == want:
            return cand
    return direct


def load_structure(ref: str | Path):
    """VALIDATED (scan, gate one).

    from src/library.py:61. The original resolved `Structure` from a module-
    level pymatgen import; here it is imported in the body so that merely
    importing this shim does not require pymatgen - the witness path does not.
    """
    from pymatgen.core import Structure
    return Structure.from_file(str(ref))


# --------------------------------------------------------- refinement table

# from src/followups.py:132
CONTAMINATION_NOTE = (
    "stage-two evidence in this deposit is an expert re-refinement performed "
    "after the dispute was resolved; it encodes the outcome implicitly. "
    "Declared, scored separately, never pooled with stage one.")

_REFINEMENT_CACHE: dict = {}          # from src/library.py:273
_STAGE_COLUMN = {"one": "auto", "two": "manual"}   # from src/library.py:275


def _phase_core(formula: str) -> str:
    """The composition part of a printed phase label.

    from src/library.py:278

    The table annotates some phases with a polytype or a provenance tag:
    "Ba6Ta2Na2V2O17 (12H-type)", "Zn3Ni4(SbO6)2_ICSD109468". The annotation is
    information and is kept in `formula`; this returns the part that can be
    matched as a composition. Only a trailing annotation is stripped, and only
    when stripping it makes the string parse - so a formula that legitimately
    ends in a bracketed group, like CaGd2Zr(GaO3)4, is never truncated.
    """
    import re as _re
    from pymatgen.core import Composition
    cand = str(formula).strip().rstrip(",;")
    def ok(x):
        try:
            Composition(x)
            return True
        except Exception:
            return False
    if ok(cand):
        return cand
    for pat in (r"\s*\([^()]*\)\s*$", r"_[A-Za-z0-9]+\s*$"):
        stripped = _re.sub(pat, "", cand).strip()
        if stripped and stripped != cand and ok(stripped):
            return stripped
    return cand


def _parse_refinement_cell(text: str) -> dict:
    """One table cell into phases and Rwp.

    from src/library.py:306

    THE BRACKET CONVENTION, established by inspecting all 48 rows on 27 August
    2026: a weight fraction in brackets appears only where the refinement
    identified TWO OR MORE phases. Of the 28 automated cells carrying no
    bracket, every one names exactly one phase and none names more - so a bare
    formula is a single-phase fit at 100 per cent, not a missing measurement.
    Reading those blanks as absent data understated the table badly: the merged
    label file carried an automated weight fraction for only 14 of 43 rows,
    when in truth every row has one.

    The 100 per cent completion fires ONLY when the cell holds exactly one
    phase line and that line carried no bracket at all. A cell whose bracket
    failed to parse is left with wt_pct None rather than being silently
    promoted to a whole sample, because a parse failure is not evidence of a
    single-phase fit.
    """
    import re as _re
    raw = str(text or "").strip()
    if not raw or raw.lower() == "nan":
        return {"phases": [], "rwp": None, "empty": True}
    phases, rwp, saw_bracket = [], None, False
    for line in raw.split("\n"):
        t = line.strip()
        if not t or t.lower() == "nan":
            continue
        m = _re.match(r"Rwp\s*=\s*([\d.]+)", t, _re.I)
        if m:
            rwp = float(m.group(1))
            continue
        # tolerate trailing punctuation after the bracket: "X [13.39%],"
        m = _re.match(r"^(.*?)\s*\[\s*([\d.]+)\s*%?\s*\]\s*[.,;]?\s*$", t)
        if m:
            saw_bracket = True
            phases.append({"formula": m.group(1).strip(),
                           "formula_core": _phase_core(m.group(1)),
                           "wt_pct": float(m.group(2))})
        else:
            phases.append({"formula": t, "formula_core": _phase_core(t),
                           "wt_pct": None})
    if len(phases) == 1 and not saw_bracket and phases[0]["wt_pct"] is None:
        phases[0] = {**phases[0], "wt_pct": 100.0,
                     "wt_pct_source": "bracket convention: sole phase listed"}
    return {"phases": phases, "rwp": rwp, "empty": False}


def _refinement_table() -> dict:
    """The parsed table, keyed by composition-normalised formula. Cached.

    from src/library.py:353. `norm_formula` now resolves in this file rather
    than in build_labels; the body is otherwise unchanged.
    """
    if _REFINEMENT_CACHE:
        return _REFINEMENT_CACHE
    import pandas as _pd
    root = Path(__file__).resolve().parent.parent
    xl = root / "data" / "cifs" / "Refinement-Table.xlsx"
    d = _pd.read_excel(xl)
    d.columns = ["formula", "concl", "auto", "manual",
                 "notes"] + list(d.columns[5:])
    d = d.dropna(subset=["formula"])
    for _, r in d.iterrows():
        name = str(r["formula"]).strip()
        _REFINEMENT_CACHE[norm_formula(name)] = {
            "printed_formula": name,
            "auto": _parse_refinement_cell(r["auto"]),
            "manual": _parse_refinement_cell(r["manual"]),
        }
    return _REFINEMENT_CACHE


def refinement_row(compound: str, stage: str = "one") -> dict:
    """The deposited refinement row for one compound, at one evidence stage.

    from src/library.py:375

    Returns, always with the same keys so an absence is a row and never a null:

      compound          as asked for
      printed_formula   as printed in the table, which may permute the elements
      stage             "one" or "two"
      resolved          whether the compound was found in the table
      rwp               fit residual per cent, or None
      phases            [{"formula": str, "wt_pct": float|None}, ...] as listed
      n_phases          how many phases the refinement identified
      note              provenance, and the contamination declaration at stage two

    The compound is matched by composition, not by string, because the deposit
    and the spreadsheet do not always spell a formula with its elements in the
    same order - the failure that made two of 42 deposited files unreachable.

    STAGE TWO IS NOT FREELY AVAILABLE in the layer, which releases it only
    against a matching follow-up request. The benchmark applies that rule at
    the point of emission instead: `emit_instances` writes stage one and
    withholds stage two, and the scorer reads stage two only where it is
    scoring a target that has already been elicited.
    """
    stage = str(stage)
    if stage not in _STAGE_COLUMN:
        raise ValueError(f"unknown stage: {stage!r}; use 'one' or 'two'")
    tbl = _refinement_table()
    hit = tbl.get(norm_formula(compound))
    base = {"compound": compound, "stage": stage,
            "printed_formula": None, "resolved": False,
            "rwp": None, "phases": [], "n_phases": 0}
    if hit is None:
        return {**base, "note": "compound absent from the deposited "
                                "refinement table"}
    cell = hit[_STAGE_COLUMN[stage]]
    note = ("automated refinement, present in the deposit in 2023"
            if stage == "one" else CONTAMINATION_NOTE)
    return {**base, "printed_formula": hit["printed_formula"],
            "resolved": bool(cell["phases"]) or cell["rwp"] is not None,
            "rwp": cell["rwp"], "phases": list(cell["phases"]),
            "n_phases": len(cell["phases"]), "note": note}


# ------------------------------------------------------------- follow-up menu
#
# from src/followups.py:56. The benchmark uses MENU for ONE thing: writing
# `data/entrant/follow_up_menu.json`, the list of follow-ups an abstaining
# entrant may ask for. It reads only `modality` and `statement`. The layer's
# MENU additionally carries `power_basis` for each entry, which is how the
# layer prices a follow-up; that is a layer concern and the pricing text is
# kept here only so the two menus can be diffed by eye.

MENU: dict[str, dict] = {
    "xrd-longer-counting": {
        "statement": ("powder X-ray diffraction on the same instrument, "
                      "longer counting, under the assumed instrument model"),
        "power_basis": ("the pricing axis itself: the converse floor for the "
                        "claim-rival pair under the assumed instrument model"),
        "priceable": True,
    },
    "neutron-powder": {
        "statement": ("neutron powder diffraction on the same specimen"),
        "power_basis": ("tabulated coherent scattering lengths, which do not "
                        "track atomic number, so pairs that are near-identical "
                        "to X-rays can separate sharply"),
        "priceable": True,
    },
    "anomalous-xrd-edge": {
        "statement": ("X-ray diffraction at an absorption edge of one of the "
                      "constituent elements"),
        "power_basis": ("would need tabulated f' and f'' at the chosen edge "
                        "and an edge-aware forward model; neither is in the "
                        "library"),
        "priceable": False,
    },
    "higher-resolution-xrd": {
        "statement": ("higher-resolution synchrotron powder diffraction"),
        "power_basis": ("would need a resolution function distinct from the "
                        "assumed instrument model; the library carries one "
                        "instrument"),
        "priceable": False,
    },
    "electron-diffraction": {
        "statement": ("selected-area electron diffraction on single grains"),
        "power_basis": ("dynamical scattering; no kinematic forward model in "
                        "the library applies"),
        "priceable": False,
    },
    "elemental-analysis": {
        "statement": ("independent elemental analysis of the specimen"),
        "power_basis": ("a different observable: composition, not a "
                        "diffraction profile, so the pricing axis does not "
                        "apply"),
        "priceable": False,
    },
    "re-refinement-expanded-phase-set": {
        "statement": ("re-refinement of the existing pattern against an "
                      "expanded set of candidate phases"),
        "power_basis": ("documentary, not computable: whether a larger phase "
                        "set fits better is the outcome of a refinement, not "
                        "a quantity derivable from two simulated profiles"),
        "priceable": False,
    },
}


# ------------------------------------------------------- deposit path, by name
# from src/control_test.py. The harness resolves a deposited file by compound
# name; resolve_cif above already does this and tolerates the two compounds the
# deposit spells with their elements in a different order, so find_cif is that
# function under the name the harness calls it by.

def find_cif(name: str, stage: str = "Automated_Refinement_Results"):
    return resolve_cif(stage, name)


# ------------------------------------------------- the refinement workbook rows
# from src/build_labels.py. reproduce_baselines reads the published refinement
# table; the workbook parser is stdlib (zipfile + ElementTree), so it comes
# across whole rather than pulling build_labels and its pymatgen label logic.

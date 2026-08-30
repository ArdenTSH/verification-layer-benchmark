"""
The primitive library. Additions bump LIBRARY_VERSION and signatures never
mutate in place. Every check run records the version it saw.

Relation to primitives.py: that module is the BLIND-PROBE HANDOUT, a deliberately
minimal Ctx (structure introspection only, no simulation, no reference lookup),
frozen as part of the gate-two protocol. This module is the full vocabulary that
compiled checks compose once past the probe. The probe subset is a strict subset of
what this module can express; keep it that way.

Status legend per primitive:
  VALIDATED    ran inside a reported result (scan, gate one, gate one ionic)
  IMPLEMENTED  code exists and is smoke-tested
  STUB         signature frozen; calling raises with the reason

Purity rule (map A.3): everything here is deterministic. The single impure primitive is
reference_structures, a STUB by design that activates once a snapshot is pinned, since
an unpinned reference lookup would put a moving database inside the trusted base.

Known stated limitations carried from gate one: neutral-atom against ionic form
factors is a declared parameter (CL-12, CL-14); symprec is always explicit (the
FeSb3Pb4O13 lesson); all distinguishability numbers are fixed-parameter lower bounds
on confusability.
"""

from __future__ import annotations

import sys
import warnings
from pathlib import Path

import numpy as np

warnings.filterwarnings("ignore")
sys.path.insert(0, str(Path(__file__).resolve().parent))

from pymatgen.core import Structure  # noqa: E402

import disorder as _disorder  # noqa: E402
import simulate as _simulate  # noqa: E402
import distinguish as _distinguish  # noqa: E402

NEUTRON_WAVELENGTH = 1.5406   # A; DECLARED, see simulate_pattern
# OWNER'S RULING: NOTHING HERE HAS REACHED 1.0.0, so no component carries a
# version at or above it. 1.0.0 is reserved for a finished layer and is not
# near. LIBRARY_VERSION counts rule versions from zero, which is why five of
# them read 0.4.0 rather than 1.4.0. The mapping from the pre-ruling strings
# stayed in the research repository with the ledgers that carry them.
LIBRARY_VERSION = "0.4.0"
# 1.3.0 adds sequential_price, trusted-base pricing only. The blind-probe
# handout (primitives.py) is unchanged: the one-primitive-per-generation
# rule governs the CHECK vocabulary, and no check can call this.


# ------------------------------------------------------------------ structures

def load_structure(ref: str | Path) -> Structure:
    """VALIDATED (scan, gate one)."""
    return Structure.from_file(str(ref))


def site_occupancies(struct: Structure) -> list[dict]:
    """Per-site species amounts and a mixed flag. VALIDATED (scan.py logic)."""
    out = []
    for i, site in enumerate(struct):
        amts = dict(site.species.get_el_amt_dict())
        mixed = len(amts) > 1 or any(abs(a - 1.0) > 1e-6 for a in amts.values())
        out.append({"index": i, "species": amts, "mixed": mixed,
                    "frac_coords": [float(c) for c in site.frac_coords]})
    return out


def space_group(struct: Structure, symprec: float) -> str:
    """symprec is REQUIRED, never defaulted: the FeSb3Pb4O13 discrepancy showed the
    answer can change with it. VALIDATED (scan, gate one)."""
    try:
        return struct.get_space_group_info(symprec=symprec)[0]
    except Exception:
        return "?"


def arrangement_symmetry(struct: Structure, merge: list[set[str]] | None,
                         symprec: float) -> int:
    """International Tables number of the symmetry the ARRANGEMENT admits,
    optionally with element groups treated as indistinguishable. The
    primitive, from the opus arm (CL-31): three checks hand-rolled coordinate
    matching across 400-plus lines to ask "does this claimed-P1 deposit admit
    higher symmetry?" and "is the claimed group broken only by the A/B
    decoration?", and two crashed on syntax slips doing it. merge=[{"Mg","Fe"}]
    sums those species' occupancies onto one placeholder per site before the
    symmetry search, so arrangement_symmetry(s, [{"Mg","Fe"}], 0.1) DIFFERING
    from the plain arrangement's number means the decoration alone carries the
    symmetry claim. The International Tables number is an identifier, not a
    quantity: comparing two numbers with > or < is not a symmetry argument
    (corrected 26 Aug 2026; see primitives.Ctx.arrangement_symmetry).
    merge=None is the plain arrangement. symprec REQUIRED. 0 on failure."""
    try:
        s = struct.copy()
        for group in (merge or []):
            names = {str(g) for g in group}
            rep = sorted(names)[0]
            for i, site in enumerate(s):
                amts = site.species.get_el_amt_dict()
                in_group = {el: a for el, a in amts.items() if str(el) in names}
                if not in_group:
                    continue
                keep = {el: a for el, a in amts.items() if str(el) not in names}
                keep[rep] = keep.get(rep, 0.0) + sum(in_group.values())
                s.replace(i, keep)
        return int(s.get_space_group_info(symprec=symprec)[1])
    except Exception:
        return 0


def space_group_number(struct: Structure, symprec: float) -> int:
    """International Tables number, 1 to 230, or 0 on failure. Notation-free: the
    haiku sweep produced seven false refutations from string inequality between
    equivalent symbols (P2_1 against P21 and kin, CL-30); numbers cannot differ
    in typesetting. Canonicalisation belongs in the trusted base, not in each
    check. symprec REQUIRED, same rule as space_group."""
    try:
        return int(struct.get_space_group_info(symprec=symprec)[1])
    except Exception:
        return 0


def disordered_rival(struct: Structure, groups: list[set[str]]) -> Structure:
    """The null hypothesis generated from the claim itself: occupancy-average the
    given cation groups. VALIDATED (gate one). Mean-field: no diffuse scattering,
    so distinguishability against it is a lower bound."""
    return _disorder.merge_sites(struct, groups)


def ordered_model(struct: Structure, method: str, group: set[str] | None = None) -> Structure:
    """Construct the ordered claim from a disordered deposit. method is
    "rocksalt-parity" (isovalent pairs, Ewald-degenerate) or "ewald-minimal".
    VALIDATED (gate one: both landed on the claimed space groups unprompted)."""
    from orderings import rocksalt_order, ewald_order
    if method == "rocksalt-parity":
        if not group:
            raise ValueError("rocksalt-parity needs the cation group")
        return rocksalt_order(struct, group)
    if method == "ewald-minimal":
        return ewald_order(struct)
    raise ValueError(f"unknown method: {method}")


# ------------------------------------------------------------------ patterns

def _need_gate_one_ionic(family: str):
    """The two non-default scattering families need a module that does not ship.

    `run_gate_one_ionic` carries the Waasmaier-Kirfel peak builder and the
    shared `peaks_to_profile`, and it lives in the layer repository. It was
    never extracted, so `form_factors="neutron"` and `form_factors="ionic"`
    raised a bare ImportError naming a module a reader of THIS repository
    cannot find. The mutant generator never asks for either - every call it
    makes takes the default "neutral" - so the paths are unreachable here
    rather than broken. Say which it is, instead of failing as though the
    install were incomplete.
    """
    raise NotImplementedError(
        f"form_factors={family!r} needs run_gate_one_ionic, which is the "
        f"layer's and is not part of this benchmark. Only the default "
        f"'neutral' family ships here; it is the one the mutant generator "
        f"prices with, and a price from one scattering family is never "
        f"comparable with a price from another anyway (CL-14).")


def simulate_pattern(struct: Structure, instrument: dict | None = None,
                     form_factors: str = "neutral",
                     ion_map: dict[str, str] | None = None) -> tuple[np.ndarray, np.ndarray]:
    """(grid, normalised profile). form_factors "neutral" uses pymatgen (VALIDATED,
    gate one); "ionic" uses Waasmaier-Kirfel with the given element-to-ion map
    (VALIDATED, gate one ionic). CL-14: absolute comparisons across form-factor
    families are unreliable below delta-Z of about 2; state the family used."""
    if form_factors == "neutral":
        return _simulate.profile(struct, instrument)
    if form_factors == "neutron":
        # NEUTRON. The same forward model with the
        # scattering table swapped: coherent scattering lengths instead of
        # X-ray form factors. Scattering lengths do not track atomic number,
        # so pairs that are near-identical to X-rays can separate sharply -
        # which is the whole reason neutron diffraction is the designated
        # exchange experiment. CL-14's cross-family caveat applies with full
        # force: a neutron price and an X-ray price are NOT comparable
        # magnitudes and must never be quoted against each other.
        from pymatgen.analysis.diffraction.neutron import NDCalculator
        peaks_to_profile = _need_gate_one_ionic("neutron")
        inst = {**_simulate.DEFAULT_INSTRUMENT, **(instrument or {})}
        # The X-ray default wavelength is the tube designation "CuKa", which is
        # meaningless for neutrons. NEUTRON_WAVELENGTH is DECLARED, not
        # published: 1.5406 A, the numeric equivalent of Cu Ka1, chosen so the
        # diffraction geometry is held fixed and the ONLY thing that changes
        # between the X-ray and neutron prices is the scattering table. Any
        # other choice would confound scattering contrast with geometry.
        wl = inst.get("neutron_wavelength", NEUTRON_WAVELENGTH)
        pat = NDCalculator(wavelength=wl).get_pattern(
            struct, two_theta_range=(inst["two_theta_min"], inst["two_theta_max"]))
        grid = np.arange(inst["two_theta_min"],
                         inst["two_theta_max"] + inst["step"], inst["step"])
        return grid, peaks_to_profile(np.asarray(pat.x, dtype=float),
                                      np.asarray(pat.y, dtype=float), instrument)
    if form_factors == "ionic":
        _need_gate_one_ionic("ionic")
        inst = {**_simulate.DEFAULT_INSTRUMENT, **(instrument or {})}
        px, py = wk_peaks(struct, ion_map or {},
                          (inst["two_theta_min"], inst["two_theta_max"]))
        grid = np.arange(inst["two_theta_min"], inst["two_theta_max"] + inst["step"],
                         inst["step"])
        return grid, peaks_to_profile(px, py, instrument)
    raise ValueError(f"unknown form_factors: {form_factors}")


def compare_patterns(a: np.ndarray, b: np.ndarray, metric: str = "hellinger2") -> float:
    """VALIDATED (gate one). Metrics: hellinger2, bhattacharyya, sym_kl."""
    fn = {"hellinger2": _distinguish.hellinger2,
          "bhattacharyya": _distinguish.bhattacharyya,
          "sym_kl": _distinguish.sym_kl}.get(metric)
    if fn is None:
        raise ValueError(f"unknown metric: {metric}")
    return fn(a, b)


def distinguishability(a: np.ndarray, b: np.ndarray, delta: float = 0.05,
                       empirical: bool = False) -> float:
    """n*: counts needed to separate the two profiles at error rate delta. Closed
    form by default; empirical=True runs the Monte Carlo likelihood-ratio test
    (slower, honest, floor at its grid minimum). VALIDATED (gate one, both)."""
    if empirical:
        return _distinguish.empirical_n_star(a, b, delta=delta)
    return _distinguish.n_star(a, b, delta=delta)


def price_floor(a: np.ndarray, b: np.ndarray, delta: float = 0.05) -> float:
    """The converse floor: no test decides the pair below this many counts (the
    Le Cam two-point bound; see distinguish.n_star_floor). The ONLY quantity
    that may certify UNDECIDABLE-AT-BUDGET."""
    return _distinguish.n_star_floor(a, b, delta=delta)


def sequential_price(a: np.ndarray, b: np.ndarray, delta: float = 0.05) -> float:
    """The sequential price beside the fixed-exposure n*: expected counts for
    a test free to stop, demand over the KL yield, conservative direction
    (see distinguish.n_star_seq for the convention). A reported column,
    never a verdict input."""
    return _distinguish.n_star_seq(a, b, delta=delta)


# ------------------------------------------------------------------ chemistry

def charge_balance(composition: str) -> bool:
    """Can the composition be charge-balanced with common oxidation states?
    IMPLEMENTED (pymatgen oxi_state_guesses); smoke-tested only."""
    from pymatgen.core import Composition
    try:
        return len(Composition(composition).oxi_state_guesses()) > 0
    except Exception:
        return False


# ------------------------------------------------- what used to follow here

# THE LAYER'S REFINEMENT ROW AND REFERENCE-CORPUS STUBS ARE NOT IN THIS
# REPOSITORY. Removed 29 August 2026, on extraction review.
#
# This module ships for ONE reason: `bench/mutate.py` imports eight names from
# it - load_structure, site_occupancies, disordered_rival, ordered_model,
# simulate_pattern, compare_patterns, distinguishability, LIBRARY_VERSION - to
# build mutants and price their difficulty. Nothing on the scoring path imports
# this file at all; the scorer reaches `refinement_row`, `resolve_cif` and
# `load_structure` through `tools/bench_shim.py`, which is the whole point of
# the shim.
#
# What sat below was the layer's own copy of the refinement-row reader and its
# reference-corpus stubs. Every one of them was DEAD in this repository, and
# three reached for modules that do not ship:
#
#   refinement_row, _refinement_table, _parse_refinement_cell, _phase_core
#       duplicated verbatim in bench_shim, which is what every caller uses.
#       `refinement_row` carried an unguarded `import followups` for a single
#       CONTAMINATION_NOTE string, and no `followups.py` ships - so the
#       function raised ImportError on any path that reached it. Nothing did.
#   set_coverage
#       no caller.
#   _load_snapshot, snapshot_available, reference_structures, refinement_quality
#       the reference-corpus stubs. They resolve `data/reference/MANIFEST.md`,
#       which is licence-bound and deliberately not redistributed, and the
#       last of the four raised NotImplementedError by design.
#
# Shipping `followups.py` to satisfy an import nothing calls would have added
# layer code to the benchmark to support dead code - the exact coupling the
# split exists to remove. Deleting is the direction that agrees with the shim.

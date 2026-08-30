"""
WEEK ONE GO / NO-GO.

The critics' Error-3 argument is a scattering-contrast argument, stated explicitly in
PRX Energy 3, 011002 (2024):

  "the x-ray scattering factors between M and Sb are very similar for M = In, Hf, and Sn,
   meaning that any ordering of these elements in the synthesized materials would be very
   difficult to detect via XRD"

  "The small difference in x-ray scattering factor between Sn and Zr means that simulated
   patterns of the ordered Ba2SnZrO6 phase show only very small changes compared with the
   disordered phase"

  "Although the B-site ordering in the predicted phase lowers the symmetry, the intensities
   of the additional reflections are very weak"

That is a preregistered, published, expert-stated prediction about the ranking of exactly
the quantity we compute. Test it before building anything else.

TWO PREDICTIONS, both stated before looking:

  P1  All six named compounds score LOW on distinguishability, i.e. n* far above any
      plausible counting budget for an 8-minute benchtop scan.

  P2  The score does NOT track |Z_M - Z_Sb|. In Pb2(M,Sb)O6.5 the lead (Z=82) dominates the
      total scattering, so superlattice intensity goes as |f_M - f_Sb|^2 against a
      Pb-dominated background. Iron (26) against antimony (51) is a large atomic-number
      difference and hafnium (72) against antimony is larger still, yet the critics class
      both as undetectable. A naive Z-difference heuristic therefore gets this WRONG and a
      full structure-factor calculation may get it right. If our score merely reproduces
      ΔZ, it is a heuristic wearing a lab coat and it has not earned anything.

POSITIVE CONTROL. Rather than depending on an external compound, substitute a light element
onto the M site of one of the pyrochlores. Same structure type, same Pb background, only
the scattering contrast changes. This isolates the variable exactly and needs no new data.

  P3  The light-substituted analogue scores HIGH, by a wide margin.

If P1 and P3 hold, the metric is calibrated against expert physics with a language model
nowhere in sight. If P1 fails, the premise of the project is wrong and everything
downstream is void. Report either way.

USAGE
  1. Download the Nature Supplementary Data ZIP into data/ and unzip into data/cifs/.
     https://media.springernature.com/original/springer-static/esm/art%3A10.1038%2Fs41586-023-06734-w/MediaObjects/41586_2023_6734_MOESM3_ESM.zip
  2. python Aletheia_v0/src/run_gate_one.py

Superseded by run_gate_one.py, which adds the peak-intensity tolerance fix, constructed
ordered models for the two cases whose deposit is already disordered, and the instrument
sweep. This file holds the predictions and the case list, which the runners import.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from pymatgen.core import Structure, Element

sys.path.insert(0, str(Path(__file__).resolve().parent))

from disorder import merge_sites            # noqa: E402
from simulate import profile, superlattice_fraction, DEFAULT_INSTRUMENT  # noqa: E402
from distinguish import hellinger2, n_star, empirical_n_star             # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
CIF_ROOT = ROOT / "data" / "cifs"

# Predicted LOW distinguishability by the critics, with the cation pair they name.
CASES: list[tuple[str, set[str], str]] = [
    ("FeSb3Pb4O13", {"Fe", "Sb"}, "Pb-Sb pyrochlore; dZ = 25"),
    ("InSb3Pb4O13", {"In", "Sb"}, "Pb-Sb pyrochlore; dZ = 2"),
    ("Sn2Sb2Pb4O13", {"Sn", "Sb"}, "Pb-Sb pyrochlore; dZ = 1"),
    ("Zr2Sb2Pb4O13", {"Zr", "Sb"}, "Pb-Sb pyrochlore; dZ = 11"),
    ("Hf2Sb2Pb4O13", {"Hf", "Sb"}, "Pb-Sb pyrochlore; dZ = 21"),
    ("Ba2ZrSnO6", {"Zr", "Sn"}, "double perovskite; dZ = 10"),
]

# Positive control: light element substituted onto the M site of a pyrochlore.
CONTROL_PARENT = "Sn2Sb2Pb4O13"
CONTROL_SUBSTITUTION = ("Sn", "Al")  # Z 50 -> 13, against Sb at 51

# NOTE. The critics also cite a Zn/Ni/Sb spinel (Gama et al.) as a case where ordering
# WOULD have been visible, and say it matches "the exact composition predicted in the
# A-lab paper". The Table III transcription carries one Zn/Ni/Sb row, Zn3Ni4(SbO6)2
# (data/labels/prx_table3.csv). Identifying that row with the cited spinel is a chemical
# judgment this file does not make, so the synthetic control above is the one used.


def find_cif(name: str) -> Path:
    hits = sorted(CIF_ROOT.rglob(f"{name}.cif"))
    if not hits:
        raise FileNotFoundError(
            f"{name}.cif not found under {CIF_ROOT}. Unzip the Nature Supplementary Data first."
        )
    # Prefer the automated (as-claimed) structure; the manual one is the expert's revision.
    for h in hits:
        if "Automated" in str(h):
            return h
    return hits[0]


def score_pair(ordered: Structure, groups: list[set[str]], instrument=None) -> dict:
    disordered = merge_sites(ordered, groups)
    grid, p1 = profile(ordered, instrument)
    _, p0 = profile(disordered, instrument)
    return dict(
        h2=hellinger2(p1, p0),
        n_star=n_star(p1, p0),
        n_star_mc=empirical_n_star(p1, p0),
        superlattice_frac=superlattice_fraction(p1, p0),
    )


def main() -> int:
    rows = []

    for name, group, note in CASES:
        try:
            s = Structure.from_file(find_cif(name))
            r = score_pair(s, [group])
        except Exception as exc:  # keep going; record the failure
            print(f"  FAILED {name}: {type(exc).__name__}: {exc}")
            continue
        zs = sorted(Element(e).Z for e in group)
        r.update(compound=name, note=note, dZ=abs(zs[-1] - zs[0]), kind="predicted-low")
        rows.append(r)

    # Positive control by light substitution.
    try:
        parent = Structure.from_file(find_cif(CONTROL_PARENT))
        old, new = CONTROL_SUBSTITUTION
        ctrl = parent.copy()
        ctrl.replace_species({old: new})
        r = score_pair(ctrl, [{new, "Sb"}])
        r.update(
            compound=f"{CONTROL_PARENT} [{old}->{new}]",
            note="SYNTHETIC POSITIVE CONTROL, same structure type, high contrast",
            dZ=abs(Element(new).Z - Element("Sb").Z),
            kind="predicted-high",
        )
        rows.append(r)
    except Exception as exc:
        print(f"  FAILED control: {type(exc).__name__}: {exc}")

    if not rows:
        print("no cases ran")
        return 1

    rows.sort(key=lambda r: r["h2"])

    print()
    print(f"{'compound':34s} {'kind':15s} {'dZ':>4s} {'H^2':>10s} {'n*':>12s} "
          f"{'n*(MC)':>12s} {'superlat':>9s}")
    print("-" * 104)
    for r in rows:
        print(f"{r['compound']:34s} {r['kind']:15s} {r['dZ']:4d} {r['h2']:10.3e} "
              f"{r['n_star']:12.3e} {r['n_star_mc']:12.3e} {r['superlattice_frac']:9.4f}")

    lows = [r for r in rows if r["kind"] == "predicted-low"]
    highs = [r for r in rows if r["kind"] == "predicted-high"]

    print()
    print("P1  all critic-named compounds score low:", end=" ")
    if highs and lows:
        print("PASS" if max(r["h2"] for r in lows) < min(r["h2"] for r in highs) else "FAIL")
    else:
        print("not evaluable (control missing)")

    if len(lows) > 2:
        dz = np.array([r["dZ"] for r in lows], dtype=float)
        h2 = np.array([r["h2"] for r in lows], dtype=float)
        # Spearman without scipy
        rk = lambda a: np.argsort(np.argsort(a)).astype(float)  # noqa: E731
        a, b = rk(dz), rk(h2)
        rho = float(np.corrcoef(a, b)[0, 1])
        print(f"P2  score does not track dZ within the low set: rho = {rho:+.3f}", end="  ")
        print("PASS (weak)" if abs(rho) < 0.5 else "FAIL - metric may be a dZ heuristic")

    print()
    print("Interpretation. n* is 'counts needed to separate at 5% error', up to an O(1)")
    print("constant. An 8-minute benchtop scan is of order 1e5 to 1e7 total counts. Any")
    print("compound whose n* sits far above that band was undetermined by the measurement")
    print("actually performed, regardless of what the refinement reported.")
    print()
    print("Instrument assumptions used (NONE of these are published for A-Lab):")
    for k in ("wavelength", "step", "U", "V", "W", "eta", "background_frac"):
        print(f"  {k:16s} {DEFAULT_INSTRUMENT[k]}")
    print()
    print("Before reporting anything: re-run with a sweep over these and confirm the")
    print("RANKING is stable. See distinguish.stability_sweep.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

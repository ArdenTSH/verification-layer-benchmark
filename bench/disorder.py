"""
Build the disordered rival hypothesis directly from the claimed ordered structure.

This is the core move of the null-hypothesis design: the null is generated from the claim
itself, so no external structure database is needed. That removes both the Materials
Project circularity and the DFT lattice-parameter contamination that would otherwise
dominate the distinguishability score, because the ordered and disordered structures
share a lattice exactly.

Physics note. Occupancy-averaging produces the AVERAGE structure. Superlattice
reflections acquire zero structure factor and vanish; parent reflections are unchanged.
That is the correct mean-field null. It does NOT capture diffuse scattering from
short-range order, which is real information a measurement could in principle use.
An ensemble calculation (Monte Carlo or SQS over supercell configurations) would
capture that diffuse scattering, so the mean-field number here is a LOWER BOUND on
distinguishability.

"""

from __future__ import annotations

from collections import defaultdict

from pymatgen.core import Structure


def merge_sites(structure: Structure, merge_groups: list[set[str]]) -> Structure:
    """
    Replace every site containing an element of a merge group with a composite
    partial-occupancy site carrying that group's global average composition.

    Parameters
    ----------
    structure : the claimed (ordered) structure
    merge_groups : e.g. [{"Fe", "Sb"}] for a B-site-ordered Pb-Sb pyrochlore,
                   or [{"Zr", "Sn"}] for Ba2ZrSnO6.

    Returns
    -------
    A new Structure with the same lattice and site positions, disordered on those groups.
    """
    out = structure.copy()

    for group in merge_groups:
        group = {str(e) for e in group}

        # Global amount of each element in the group, summed over all sites.
        totals: dict[str, float] = defaultdict(float)
        member_idx: list[int] = []
        for i, site in enumerate(out):
            amts = site.species.get_el_amt_dict()
            if not (set(amts) & group):
                continue
            member_idx.append(i)
            for el, amt in amts.items():
                if el in group:
                    totals[el] += amt

        if not member_idx:
            raise ValueError(f"no sites matched merge group {group}")

        grand = sum(totals.values())
        if grand <= 0:
            raise ValueError(f"zero total occupancy for merge group {group}")
        frac = {el: amt / grand for el, amt in totals.items()}

        # Rewrite each member site, preserving any non-group species on it.
        for i in member_idx:
            amts = out[i].species.get_el_amt_dict()
            group_amt = sum(a for el, a in amts.items() if el in group)
            new = {el: a for el, a in amts.items() if el not in group}
            for el, f in frac.items():
                new[el] = new.get(el, 0.0) + group_amt * f
            out.replace(i, new)

    return out


def suggest_merge_groups(structure: Structure, cn_tol: float = 0.0) -> list[set[str]]:
    """
    Heuristic: group cation species that sit on sites with the same coordination number.

    THIS IS A CONVENIENCE, NOT A METHOD. Cation ordering is a chemical judgement and the
    critics' whole point is that judgement is what the automation skipped. Always inspect
    and override. The control test in control_test.py specifies groups explicitly and does
    not use this function.
    """
    from pymatgen.analysis.local_env import CrystalNN

    cnn = CrystalNN()
    by_cn: dict[int, set[str]] = defaultdict(set)
    for i, site in enumerate(structure):
        els = set(site.species.get_el_amt_dict())
        if els <= {"O", "N", "F", "S", "Cl"}:
            continue  # skip anions
        try:
            cn = round(cnn.get_cn(structure, i))
        except Exception:
            continue
        by_cn[cn] |= els

    return [g for g in by_cn.values() if len(g) > 1]


def is_disordered(structure: Structure) -> bool:
    """True if any site carries more than one species or fractional occupancy."""
    for site in structure:
        amts = site.species.get_el_amt_dict()
        if len(amts) > 1 or any(abs(a - 1.0) > 1e-6 for a in amts.values()):
            return True
    return False

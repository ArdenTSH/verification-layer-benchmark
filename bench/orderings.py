"""
Ordered-model constructions, extracted from Aletheia_v0/src/run_gate_one.py.

The gate-one runner is a pricing EXPERIMENT and does not belong in a benchmark
repository. Two functions from it do: the constructions that build an ordered
model where a deposit is already disordered, which the mutant generator needs
to make an M1 mutant assert an ordering the file does not carry.

rocksalt_order  parity assignment, for cations of the same charge, where
                electrostatics cannot rank one ordering above another.
ewald_order     lowest-Ewald-energy assignment, for cations of different charge.

Which of the two applies is a valence judgement and is recorded per mutant.
"""

from __future__ import annotations

import numpy as np

def rocksalt_order(s: Structure, group: set[str]) -> Structure:
    """Parity-assigned rock-salt ordering on the mixed sublattice, 2x2x2 supercell.
    For isovalent pairs where Ewald ranking is degenerate. Matches the claimed Fm-3m."""
    s = s.copy()
    s.make_supercell([2, 2, 2])
    mixed = [
        i for i, site in enumerate(s)
        if len(site.species.get_el_amt_dict()) > 1
        and set(site.species.get_el_amt_dict()) & group
    ]
    if not mixed:
        raise ValueError("no mixed sites to order")
    els = sorted(group)
    f0 = s[mixed[0]].frac_coords
    for i in mixed:
        d = np.rint((s[i].frac_coords - f0) * 2.0).astype(int)
        s.replace(i, els[int(d.sum()) % 2])
    return s

def ewald_order(s: Structure) -> Structure:
    """Ewald-minimal ordering for aliovalent mixed sites."""
    from pymatgen.transformations.standard_transformations import (
        OrderDisorderedStructureTransformation,
    )

    s = s.copy()
    s.add_oxidation_state_by_element({el: OXI[el] for el in s.composition.get_el_amt_dict()})
    ordered = OrderDisorderedStructureTransformation().apply_transformation(s)
    ordered.remove_oxidation_states()
    return ordered

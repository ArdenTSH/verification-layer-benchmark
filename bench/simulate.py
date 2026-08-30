"""
Forward model: structure -> normalised powder diffraction profile on a 2-theta grid.

INSTRUMENT PARAMETERS ARE NOT PUBLISHED FOR A-LAB. The paper gives only:
  instrument   Aeris Minerals benchtop (Malvern Panalytical)
  2-theta      10 to 100 degrees
  scan time    8 minutes
No wavelength, no step size, no counting time, no slits, no detector. The critics
hit the same wall and fit peak profiles empirically. Everything below marked NOT
PUBLISHED is an assumption. Every headline number must be reported with a sweep over
these, and the stability of the RANKING is the thing to check. If the ranking is not
stable under the sweep, that is the result.

"""

from __future__ import annotations

import numpy as np
from pymatgen.core import Structure
from pymatgen.analysis.diffraction.xrd import XRDCalculator

# Caglioti coefficients in deg^2. These are placeholder benchtop-ish values.
# CALIBRATE against a digitised A-Lab pattern before trusting any absolute number.
DEFAULT_INSTRUMENT = dict(
    wavelength="CuKa",       # NOT PUBLISHED. Aeris Minerals ships Cu as standard.
    two_theta_min=10.0,      # published
    two_theta_max=100.0,     # published
    step=0.02,               # NOT PUBLISHED
    U=0.005,                 # NOT PUBLISHED
    V=-0.002,                # NOT PUBLISHED
    W=0.006,                 # NOT PUBLISHED
    eta=0.5,                 # pseudo-Voigt Lorentzian fraction, NOT PUBLISHED
    background_frac=0.02,    # flat background as a fraction of total counts.
)


def caglioti_fwhm(two_theta_deg: np.ndarray, U: float, V: float, W: float) -> np.ndarray:
    """FWHM(2theta) in degrees. FWHM^2 = U tan^2(theta) + V tan(theta) + W."""
    t = np.tan(np.radians(two_theta_deg) / 2.0)
    f2 = U * t**2 + V * t + W
    return np.sqrt(np.clip(f2, 1e-6, None))


def _pseudo_voigt(x: np.ndarray, x0: float, fwhm: float, eta: float) -> np.ndarray:
    sigma = fwhm / (2.0 * np.sqrt(2.0 * np.log(2.0)))
    gauss = np.exp(-0.5 * ((x - x0) / sigma) ** 2) / (sigma * np.sqrt(2.0 * np.pi))
    gamma = fwhm / 2.0
    lorentz = gamma / (np.pi * ((x - x0) ** 2 + gamma**2))
    return eta * lorentz + (1.0 - eta) * gauss


def profile(structure: Structure, instrument: dict | None = None) -> tuple[np.ndarray, np.ndarray]:
    """
    Return (two_theta_grid, p) where p is a normalised probability distribution over the
    grid: the expected fraction of detected counts landing in each channel.

    Handles fractional site occupancies natively via pymatgen's XRDCalculator, which is
    what makes the mean-field disordered rival work.
    """
    inst = {**DEFAULT_INSTRUMENT, **(instrument or {})}

    calc = XRDCalculator(wavelength=inst["wavelength"])
    pat = calc.get_pattern(
        structure,
        two_theta_range=(inst["two_theta_min"], inst["two_theta_max"]),
        scaled=False,
    )

    grid = np.arange(
        inst["two_theta_min"], inst["two_theta_max"] + inst["step"], inst["step"]
    )
    y = np.zeros_like(grid)

    if len(pat.x):
        widths = caglioti_fwhm(np.asarray(pat.x), inst["U"], inst["V"], inst["W"])
        for x0, i0, w in zip(pat.x, pat.y, widths):
            # 6 FWHM either side is plenty and keeps this O(peaks * window)
            lo = np.searchsorted(grid, x0 - 6 * w)
            hi = np.searchsorted(grid, x0 + 6 * w)
            if hi > lo:
                y[lo:hi] += i0 * _pseudo_voigt(grid[lo:hi], x0, w, inst["eta"])

    total = y.sum()
    if total <= 0:
        raise ValueError("simulated pattern has zero intensity in range")
    y = y / total

    b = inst["background_frac"]
    if b > 0:
        y = (1.0 - b) * y + b / len(grid)

    return grid, y


def superlattice_fraction(
    p_ordered: np.ndarray, p_disordered: np.ndarray, rel_tol: float = 0.05
) -> float:
    """
    Fraction of the ordered pattern's intensity that sits in channels where the disordered
    pattern has essentially nothing. A physically interpretable companion to the abstract
    distance: "this much of the signal is the ordering, and nothing else."
    """
    mask = p_disordered < rel_tol * p_ordered
    return float(p_ordered[mask].sum())

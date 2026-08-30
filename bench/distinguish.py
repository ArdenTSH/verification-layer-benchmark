"""
Verification complexity: how many counts would you have needed to tell these apart?

Given two normalised profiles p1 (claim) and p0 (rival) over the same 2-theta grid,
a diffraction measurement with N total detected counts is a multinomial draw. By Stein's
lemma the sample size needed to separate the hypotheses at error rate delta scales as
log(1/delta) / D, with D an information divergence.

Use squared Hellinger distance, not KL, for the closed-form number. KL diverges wherever
one pattern has a sharp peak and the other has zero intensity, which happens constantly
in diffraction. The background term in simulate.profile() regularises this and is
physically correct anyway. The background level is not a detail: superlattice reflections
from cation ordering can be a fraction of a percent of the main peak, and whether they sit
above background IS the A-Lab failure mode.

empirical_n_star() is the honest version: it runs the actual likelihood-ratio test under
Poisson noise and finds the N at which the error rate drops below delta. Prefer it for
anything reported. The closed forms are for ranking 42 compounds quickly.

CAVEAT that must be stated in any write-up. This compares two FIXED structures. The real
comparison is between two MODELS WITH FREE PARAMETERS, and a disordered model with more
free parameters can be tuned to mimic an ordered one. The correct quantity is
distinguishability after refitting each model to the other's data, a penalised likelihood
ratio. Everything here is therefore a LOWER BOUND on confusability, i.e. an upper bound on
distinguishability. Do not dress the proxy up as the theorem.

"""

from __future__ import annotations

import numpy as np

_EPS = 1e-15


def _norm(p: np.ndarray) -> np.ndarray:
    p = np.clip(np.asarray(p, dtype=float), _EPS, None)
    return p / p.sum()


def hellinger2(p: np.ndarray, q: np.ndarray) -> float:
    """Squared Hellinger distance in [0, 1]. 0 = identical, 1 = disjoint support."""
    p, q = _norm(p), _norm(q)
    return float(1.0 - np.sum(np.sqrt(p * q)))


def bhattacharyya(p: np.ndarray, q: np.ndarray) -> float:
    p, q = _norm(p), _norm(q)
    return float(-np.log(np.clip(np.sum(np.sqrt(p * q)), _EPS, None)))


def sym_kl(p: np.ndarray, q: np.ndarray) -> float:
    p, q = _norm(p), _norm(q)
    return float(np.sum(p * np.log(p / q)) + np.sum(q * np.log(q / p)))


def kl(p: np.ndarray, q: np.ndarray) -> float:
    """Directed Kullback-Leibler divergence D(p || q)."""
    p, q = _norm(p), _norm(q)
    return float(np.sum(p * np.log(p / q)))


def n_star_seq(p: np.ndarray, q: np.ndarray, delta: float = 0.05) -> float:
    """
    Sequential price: expected counts for a test free to stop when the
    evidence suffices (the SPRT reading; the anytime-validity literature,
    VERIFY), as demand over the KL yield. Convention: the conservative
    direction, min(D(p||q), D(q||p)) in the denominator - the cost under
    the more expensive hypothesis to leave. Reported as a column beside
    the fixed-exposure n*; NEVER verdict-bearing, because the recorded
    measurement was fixed-exposure.
    """
    d = min(kl(p, q), kl(q, p))
    if d <= _EPS:
        return float("inf")
    return float(np.log(1.0 / delta) / d)


def n_star(p: np.ndarray, q: np.ndarray, delta: float = 0.05) -> float:
    """
    ACHIEVABLE-SIDE SURROGATE, not a lower bound. Closed-form counts SUFFICIENT
    to separate p from q at error rate delta, up to an O(1) constant.
    Convention used here: N* = log(1/delta) / H^2. Report the convention
    alongside the number; only ratios and rankings are meaningful.

    THIS NUMBER CAN NEVER CERTIFY IMPOSSIBILITY. "n_star > budget" says the
    sufficient bound is not met, not that no test succeeds within the budget;
    inferring undecidability from it is invalid and was doing so in the shipped
    decision rule until 26 Aug 2026. Use n_star_floor for any statement that
    something CANNOT be decided.
    """
    h2 = hellinger2(p, q)
    if h2 <= _EPS:
        return float("inf")
    return float(np.log(1.0 / delta) / h2)


def n_star_floor(p: np.ndarray, q: np.ndarray, delta: float = 0.05) -> float:
    """
    CONVERSE FLOOR: no test whatsoever, however clever, decides p against q with
    both errors <= delta using fewer than this many counts. Le Cam two-point
    with Bhattacharyya tensorisation (propositions-rigor Theorem 1):

        n >= ln(1 / (4 delta (1 - delta))) / (2 ln(1 / (1 - H^2)))

    This is the only quantity that may support UNDECIDABLE-AT-BUDGET. It sits a
    factor of about 3.6 below the achievable surrogate at delta = 0.05, so the
    band between them is genuinely undetermined - the BOUND-INCONCLUSIVE region
    of the decision rule.

    Returns 0.0 when the demand is non-positive (delta >= 0.5: nothing is
    required), and inf when the two patterns are identical.
    """
    h2 = hellinger2(p, q)
    if h2 <= _EPS:
        return float("inf")
    if h2 >= 1.0:
        return 0.0
    demand = np.log(1.0 / (4.0 * delta * (1.0 - delta)))
    if demand <= 0.0:
        return 0.0
    return float(demand / (2.0 * np.log(1.0 / (1.0 - h2))))


def empirical_n_star(
    p: np.ndarray,
    q: np.ndarray,
    delta: float = 0.05,
    n_grid: np.ndarray | None = None,
    trials: int = 400,
    rng: np.random.Generator | None = None,
) -> float:
    """
    Monte Carlo likelihood-ratio test under Poisson counting noise.

    Draws counts ~ Poisson(N * p) and ~ Poisson(N * q), scores each with the log-likelihood
    ratio, thresholds at zero, and returns the smallest N on the grid where BOTH error
    rates fall at or below delta. Returns inf if no N on the grid achieves it.

    Criterion corrected 26 Aug 2026: this thresholded the AVERAGE of the two
    error rates (0.5*(err_p+err_q) < delta), which Definition 1 does not permit -
    an average under delta admits one error far above it. Numbers produced by
    the earlier criterion are not comparable with numbers produced by this one.
    """
    rng = rng or np.random.default_rng(0)
    p, q = _norm(p), _norm(q)
    llr_weight = np.log(p / q)

    if n_grid is None:
        n_grid = np.unique(np.round(np.logspace(2, 9, 36)).astype(np.int64))

    for N in n_grid:
        kp = rng.poisson(N * p, size=(trials, len(p)))
        kq = rng.poisson(N * q, size=(trials, len(q)))
        err_p = float(np.mean(kp @ llr_weight <= 0.0))   # p misread as q
        err_q = float(np.mean(kq @ llr_weight >= 0.0))   # q misread as p
        if max(err_p, err_q) <= delta:
            return float(N)

    return float("inf")


def stability_sweep(
    build_profiles,
    instrument_variants: list[dict],
    delta: float = 0.05,
) -> list[float]:
    """
    Recompute n_star across instrument assumptions. build_profiles(instrument) must return
    (p_claim, p_rival). Since none of the A-Lab instrument parameters were published, the
    only defensible claim is one that survives this sweep. Report the spread, and if the
    RANKING across compounds is not stable, report that instead of the numbers.
    """
    out = []
    for inst in instrument_variants:
        p, q = build_profiles(inst)
        out.append(n_star(p, q, delta=delta))
    return out

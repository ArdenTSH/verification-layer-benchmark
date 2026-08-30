"""
The claim envelope. Field semantics change only by an explicit ENVELOPE_VERSION
bump, never silently.

The spine is domain-independent; the domain lives in each family's payload schema.
The six ledger requirements (Part 5 of the ledger document in the project's research
log, kept privately) are baked into the fields:

  1. stable ids, exact provenance (Claim.id, Claim.provenance: file plus line, or DOI
     plus span, something a human can open)
  2. evidence resolved at intake (Ref.resolved, Ref.sha256, Ref.kind)
  3. absence is a first-class fact (a Ref with resolved=False is a row, not a null)
  4. the residual is structured fields, never free text (Residual)
  5. append-only and versioned (Claim.versions and VerdictRecord.versions record the
     envelope, extraction pipeline, and library versions per record)
  6. fixed spine, extensible payload (Claim.assertion's schema is set per family in
     FAMILIES; the dataclasses here never grow domain fields)

Naming note. primitives.Verdict is a CHECK's output (refuted, consistent,
inapplicable). VerdictRecord here is the LEDGER's aggregated row for a claim. They
are different objects on purpose; the harness maps the first into the second.

Ground-truth labels for mutation-generated claims live OUTSIDE the envelope (the
generator keeps its own claim_id to truth table). A claim handed to a model must
never contain its own answer.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field, asdict
from pathlib import Path

ENVELOPE_VERSION = "0.1.0"


# ---------------------------------------------------------------- evidence

@dataclass(frozen=True)
class Ref:
    uri: str                 # path, or DOI plus span; a human can open it
    kind: str                # "cif" | "csv" | "xlsx" | "figure" | "document" | ...
    resolved: bool           # did the artifact resolve at intake
    sha256: str | None = None
    note: str = ""           # for resolved=False: why not; this row is a data product


def resolve_ref(path: str | Path, kind: str) -> Ref:
    """Resolve a local artifact at intake: existence plus content hash."""
    p = Path(path)
    if not p.exists():
        return Ref(uri=str(p), kind=kind, resolved=False, note="file absent at intake")
    h = hashlib.sha256(p.read_bytes()).hexdigest()
    return Ref(uri=str(p), kind=kind, resolved=True, sha256=h)


# ---------------------------------------------------------------- the claim

@dataclass(frozen=True)
class Claim:
    id: str                        # stable forever, never reused. convention below.
    family: str                    # key into FAMILIES
    assertion: dict                # payload; required keys set by the family
    evidence: tuple[Ref, ...]      # everything the claim points at
    provenance: str                # who asserted it, where, verbatim if short
    context: dict = field(default_factory=dict)   # instrument, settings, budget
    parent: str | None = None      # compound claim this decomposes from
    versions: dict = field(default_factory=lambda: {"envelope": ENVELOPE_VERSION})

    def to_probe_dict(self) -> dict:
        """Projection to the flat dict shape probe.Ctx expects."""
        out = {"compound": self.assertion.get("compound", ""), **self.assertion}
        out["source"] = self.provenance
        return out


# ID convention: "<corpus>:<subject>:<family>[:<n>]", e.g. "alab:Ba2ZrSnO6:cation-ordering"
# or "mutant:Sr2HfGeO6:cation-ordering:003". Never reused, including for corrections:
# a corrected claim gets a new id and a parent pointer to the old one.


# ---------------------------------------------------------------- verdict side

@dataclass(frozen=True)
class Witness:
    where: str      # locator someone with no access to our code can open
    observed: str   # what was found there
    required: str   # what the claim needed instead


@dataclass(frozen=True)
class Rival:
    description: str
    source: str                # "generated-from-claim" | "prx-table3" | "cod" | ...
    structure: Ref | None = None


@dataclass(frozen=True)
class FollowUp:
    """One candidate follow-up an abstaining verifier may ask for.

    The residual used to carry a single hardcoded string, so every abstention
    asked for the same thing regardless of what it abstained about, and a
    stage-two release had nothing to condition on. A FollowUp is one option in
    a plural menu.

    `power` is the discriminating power where the trusted base can compute it,
    in the same units as the pricing axis (detected counts to separate at the
    stated error rate). It is None where no forward model applies, and
    `power_basis` then states why rather than leaving a bare null.

    `supply` is a property of THE INSTANCE, never of the modality. A modality
    the benchmark cannot supply still belongs in the menu: the menu is the
    vocabulary of requests, and what a given instance can honour is a separate
    fact recorded beside it. An instance holding neutron data scores the same
    request differently from one that does not, using the same vocabulary.
    """
    modality: str                    # a key from followups.MENU
    separates: tuple[str, ...] = ()  # which surviving rivals, by description
    power: float | None = None       # counts to separate, where computable
    power_basis: str | None = None   # what made it computable, or why not
    cost: str | None = None
    supply: str = "unavailable"      # "benchmark-supplies"|"stage-two"|"unavailable"
    origin: str = "trusted-base-menu"   # or "model-proposed"


@dataclass(frozen=True)
class Residual:
    rivals_surviving: tuple[str, ...]        # descriptions or rival ids
    separating_measurement: str | None       # e.g. "neutron powder diffraction"
    estimated_cost: str | None               # counts, or instrument time
    n_star: float | None                     # counts needed under the stated model
    # -- the plural half, added 27 Aug 2026. Appended with defaults so every
    #    existing positional construction keeps working unchanged.
    options: tuple[FollowUp, ...] = ()   # what COULD be asked for
    requested: FollowUp | None = None    # what the verifier DID ask for
    coverage: dict | None = None         # set-adequacy evidence, when computed

    @property
    def suppliable(self) -> tuple[FollowUp, ...]:
        """The options this instance could actually honour."""
        return tuple(o for o in self.options if o.supply != "unavailable")


@dataclass(frozen=True)
class CheckRun:
    check_id: str
    artifact_sha256: str        # hash of the check source, logged before execution
    library_version: str
    status: str                 # "refuted" | "consistent" | "inapplicable"
    witness: Witness | None = None
    undetermined: tuple[str, ...] = ()


@dataclass(frozen=True)
class VerdictRecord:
    claim_id: str
    status: str                 # "refuted" | "cannot_verify" | "verified"
    modality: str               # "compiled" | "judge"; storage partitioned on this,
                                # aggregation never mixes, rows never shared
    checks: tuple[CheckRun, ...]
    residual: Residual
    versions: dict              # envelope, library, aggregation-policy versions

    def __post_init__(self):
        if self.status == "verified":
            # "verified" is only ever emergent: every rival refuted, nothing refuting
            # the claim. A single check can never produce it; the aggregator asserts
            # this invariant again at write time.
            assert self.checks, "verified requires the full check record"


# -------------------------------------------------------------------- families

# The extensible half. Adding a family or a payload key is a minor version bump;
# changing the meaning of an existing key is forbidden (add a new key instead).
FAMILIES: dict[str, dict] = {
    "phase-present": {
        "question": "is a phase matching the claimed structure present in the sample",
        "payload": ["compound", "claimed_structure"],        # + optional "pattern"
        "rung": 3,   # needs a rival set to mean anything
    },
    "weight-fraction": {
        "question": "is the claimed phase above the stated weight fraction",
        "payload": ["compound", "threshold"],
        "rung": 3,
    },
    "cation-ordering": {
        "question": "does the material have the cation ordering the structure asserts",
        "payload": ["compound", "space_group_claimed", "structure_type"],
        "rung": 1,   # the deposited file alone can refute (the A-Lab episode's check)
    },
    "novelty": {
        "question": "is the compound absent from the reference corpus",
        "payload": ["compound", "reference_snapshot"],
        "rung": 2,
    },
}


# Language that asserts PURITY - that the specimen is the target phase and
# nothing else. THIS IS A KEYWORD LIST AND IT IS WRONG SOMETIMES. Measured on
# ten hand-written statements, 27 Aug 2026: 3 wrong, one of them a NEGATED
# claim ("we cannot claim the sample is phase-pure") flagged as an assertion of
# purity, and two misses ("contains only the target phase", "essentially free
# of other crystalline material").
_PURITY_LANGUAGE = (
    "phase-pure", "phase pure", "single-phase", "single phase",
    "no secondary", "no impurity", "no impurities", "without secondary",
    "free of secondary", "100%", "100 %", "100 per cent", "entirely",
    "exclusively the",
)

_PCT = None   # compiled on first use


def stated_fraction(text: str) -> float | None:
    """Any explicit fraction the statement itself asserts, as 0-1, or None.

    SOUND. It parses a number the statement contains; it infers nothing from
    wording. "at least 85% of the product" gives 0.85 and nothing else does.
    """
    global _PCT
    import re as _re
    if _PCT is None:
        _PCT = _re.compile(r"(\d{1,3}(?:\.\d+)?)\s*(?:%|per ?cent)")
    best = None
    for m in _PCT.finditer(str(text or "")):
        v = float(m.group(1))
        if 0 <= v <= 100:
            best = v / 100.0 if best is None else max(best, v / 100.0)
    return best


def statement_payload_consistent(family: str, assertion: dict) -> list[str]:
    """Does a child's prose say the same thing as its structured payload?

    Total: returns problems, never raises. Empty list means nothing detected.

    **DIAGNOSTIC ONLY. THIS DOES NOT GATE ANYTHING AND MUST NOT.** It was
    briefly wired into `validate()` on 27 August and removed the same day, for
    the reason below.

    THE FAILURE IT LOOKS FOR IS REAL. Every one of the 90 weight-fraction
    children in one arm carries `threshold: 0.5` - a default the model
    invented, since the paper states no threshold - while the statement beside
    it says things like "the sample is phase-pure, with no secondary
    crystalline phases". Fifty per cent is "the target is the major phase";
    phase-pure is "there is nothing else". The kernel prices the payload and a
    model-written check reads the statement, so a witness can be written
    against an assertion that was never priced.

    THE DETECTION IS IN TWO PARTS AND ONLY ONE IS SOUND.

      sound      : an explicit percentage in the statement compared against the
                   threshold. It parses a number; it infers nothing.
      HEURISTIC  : purity WORDING matched against a keyword list. Measured 3
                   wrong in 10, including a negated claim flagged as an
                   assertion. Findings from this half carry
                   "heuristic-keyword-match" in their text and must be read by
                   a human before anyone acts on one.

    This project removed a keyword classifier from the witness checker on 26
    August after it routed genuine ordering refutations to a predicate that
    could not adjudicate them. Building a second one a day later and letting
    it gate would repeat that exactly. Safety here does not depend on it:
    `entailment.classify` marks EVERY weight-fraction child STRONGER whatever
    its wording, so no such refutation propagates regardless of what this
    function returns.
    """
    problems: list[str] = []
    if family != "weight-fraction":
        return problems
    text = str(assertion.get("statement", "") or "")
    thr = assertion.get("threshold")
    if not text or thr is None:
        return problems
    try:
        thr = float(thr)
    except (TypeError, ValueError):
        return problems

    stated = stated_fraction(text)
    if stated is not None and abs(stated - thr) > 1e-9:
        problems.append(
            f"statement/payload mismatch (SOUND, parsed): the statement states "
            f"{stated:.2%} while the payload asserts threshold={thr}")
        return problems

    low = text.lower()
    hit = next((w for w in _PURITY_LANGUAGE if w in low), None)
    if hit is not None and thr < 1.0:
        problems.append(
            f"possible statement/payload mismatch (heuristic-keyword-match, "
            f"measured 3 wrong in 10): the statement contains {hit!r}, which "
            f"usually asserts purity, while the payload asserts only "
            f"threshold={thr}. NEGATIONS ARE NOT DETECTED. Read the statement "
            f"before acting on this")
    return problems


def validate(claim: Claim) -> list[str]:
    """Total: returns problems, never raises. Empty list means well-formed."""
    problems = []
    fam = FAMILIES.get(claim.family)
    if fam is None:
        problems.append(f"unknown family: {claim.family}")
    else:
        for key in fam["payload"]:
            if key not in claim.assertion:
                problems.append(f"missing payload key for {claim.family}: {key}")
    if not claim.id or claim.id.count(":") < 2:
        problems.append("id must follow <corpus>:<subject>:<family>")
    if not claim.evidence:
        problems.append("a claim with no evidence refs is not checkable; record the "
                        "absence as an unresolved Ref instead of omitting it")
    return problems


def as_row(obj) -> dict:
    """Flatten any envelope dataclass for CSV or JSON storage."""
    return asdict(obj)

#!/usr/bin/env python3
"""Standalone witness checker. Stdlib only; shares no code with the layer.

A kernel refutation carries a witness {"where","observed","required"}. Believing it should
not require trusting the kernel, pymatgen, or a symmetry engine: this program is the whole
trusted base. It re-reads the deposited CIF with its own parser and reports whether the
witness's observation is really in the file, and whether it contradicts what the claim
required. Verdicts are about the WITNESS, never the claim: WITNESS REPRODUCED (the printed
file lines bear it out), WITNESS NOT REPRODUCED, or UNSUPPORTED CLASS. Four predicates,
ALL of which are tried (no keyword routing): occupancy; stoichiometry (element ratios are
compared, never strings, so a reduced formula and a cell-content formula of one
composition agree); lattice-metric; symmetry-tag (documentary: the checker compares what
the file SAYS in its tags, it never recomputes symmetry).

The optional third argument is the CLAIM RECORD. Supply it whenever the contradiction is a
family-level requirement rather than a number: the witness's "required" field is written by
the same untrusted model that wrote the check, so validating a contradiction against it is
circular. The claim record is trusted data and says what was actually claimed.

This program is a certifying-algorithm checker in the sense of the
certifying-algorithms survey (Mehlhorn et al.; VERIFY): the computation that
produced the verdict is untrusted, the witness is the certificate, and this
checker is simple enough to be correct by inspection. Each witness class
satisfies a one-line formal predicate; run with --predicates to print them,
so "independently checkable" names a predicate, not a hope.

Validation rule (26 Aug 2026): EVERY predicate is tried, not one guessed from
keywords. REPRODUCED iff some predicate establishes a CONTRADICTION between
what the file says and what the claim required; NOT REPRODUCED if a predicate
applied and found none; UNSUPPORTED if none could apply. Presence of the
witnessed values in the file is necessary and never sufficient - the earlier
occupancy and lattice predicates returned reproduced on presence alone, so a
witness whose observed and required were identical validated.

Usage: python tools/check_witness.py <witness.json> <deposited.cif> [<claim.json>]
       python tools/check_witness.py --predicates
Exit:  0 reproduced, 1 not reproduced, 2 unsupported class or bad input.
"""
import json, os, re, sys

PREDICATES = {
    "occupancy":
        "PRESENCE: EXISTS a site group G in file F sharing rounded fractional "
        "coordinates (and matching the witnessed coordinates when given) "
        "such that FORALL (element e, value v) named in witness.observed: "
        "sum of occupancies of e over G = v within 0.01. AND CONTRADICTION: "
        "either the occupancies named in witness.required differ from G's by "
        "more than 0.01, or the CLAIM RECORD's family requires these species "
        "on distinct fully occupied sites while G is shared or partial. "
        "Presence without contradiction is NOT REPRODUCED; a required side "
        "carrying no number, with no claim record supplied, is UNSUPPORTED",
    "stoichiometry":
        "LET c = the element counts of F's _atom_site loop (occupancy x "
        "multiplicity). The witnessed formula's element ratios equal c's "
        "within 0.02 per element, AND, when a required-side formula is "
        "given, the contrast the witness asserts holds under the same "
        "ratio comparison (never string comparison)",
    "lattice-metric":
        "PRESENCE: FORALL (parameter p, value v) named in witness.observed "
        "with p in {a, b, c, alpha, beta, gamma}: F carries the tag for p and "
        "its stated value equals v within max(0.02, 0.2 percent). AND "
        "CONTRADICTION: EXISTS a parameter named in witness.required whose "
        "required value differs from F's stated value by more than that same "
        "tolerance. Agreement on every required parameter is NOT REPRODUCED; "
        "a required side naming no parameter is UNSUPPORTED",
    "symmetry-tag":
        "F states a space-group symbol tag whose normalised text appears "
        "in witness.observed and not in witness.required (documentary: "
        "nothing is recomputed; the predicate is about what F SAYS)",
}

EL = r"[A-Z][a-z]?"
FORM = r"(?:\((?:%s\d*\.?\d*)+\)\d*\.?\d*|%s\d*\.?\d*){2,}" % (EL, EL)
LTAG = {"a": "_cell_length_a", "b": "_cell_length_b", "c": "_cell_length_c",
        "alpha": "_cell_angle_alpha", "beta": "_cell_angle_beta", "gamma": "_cell_angle_gamma"}

def num(tok):
    return float(re.sub(r"\(\d+\)$", "", tok))  # '14.270(22)' -> 14.270

def parse_cif(path):
    lines = open(path, errors="replace").read().splitlines()
    tags, atoms, i = {}, [], 0
    while i < len(lines):
        s = lines[i].strip()
        m = re.match(r"^(_\S+)\s+(\S.*)$", s)
        if m:
            tags[m.group(1).lower()] = (m.group(2).strip().strip("'\""), i + 1)
        elif s.lower().startswith("loop_"):
            hdr = [t.lower() for t in s.split()[1:]]
            while i + 1 < len(lines) and lines[i + 1].strip().startswith("_"):
                i += 1
                hdr += [t.lower() for t in lines[i].split()]
            col = lambda row, *ns, **kw: next((row[hdr.index(n)] for n in ns if n in hdr), kw.get("d"))
            while "_atom_site_fract_x" in hdr and i + 1 < len(lines):
                row = lines[i + 1].split()
                if len(row) != len(hdr) or row[0][0] in "_#":
                    break
                i += 1
                atoms.append({"el": re.match(EL, col(row, "_atom_site_type_symbol", "_atom_site_label")).group(0),
                              "x": num(col(row, "_atom_site_fract_x")), "y": num(col(row, "_atom_site_fract_y")),
                              "z": num(col(row, "_atom_site_fract_z")), "occ": num(col(row, "_atom_site_occupancy", d="1")),
                              "mult": num(col(row, "_atom_site_symmetry_multiplicity",
                                              "_atom_site_site_symmetry_multiplicity", d="1")), "line": i + 1})
        i += 1
    return {"lines": lines, "tags": tags, "atoms": atoms}

def cite(cif, ln):
    return "  line %d: %s" % (ln, cif["lines"][ln - 1].strip())

def _requires_ordered(claim):
    """Does the CLAIM (not the witness prose) require an ordered arrangement?

    Read from the claim record, which is trusted data, rather than inferred
    from the witness's required text, which is written by the untrusted model
    that also wrote the check. Testing a contradiction against a model's own
    account of what the claim required is circular: the model could assert any
    requirement and have it 'validated'.

    A cation-ordering claim asserts, by the family's definition, that named
    metal species occupy distinct crystallographic sites. A deposited file in
    which those species share one partially occupied site contradicts it. That
    is a structural rule about the family, not a keyword rule about prose. An
    earlier version matched words like 'ordered' and 'distinct' in the witness
    text; that heuristic was removed on 26 Aug 2026.
    """
    if not isinstance(claim, dict):
        return False
    if claim.get("requires_ordered") is True:
        return True
    return str(claim.get("family", "")) == "cation-ordering"


def _occupancy_pairs(text):
    return [(e, float(v)) for e, v in
            re.findall(r"'?(%s)'?\s*[:=]\s*(\d*\.\d+|\d+)\b" % EL, str(text))
            if float(v) <= 1.0]


def check_occupancy(w, cif, claim=None):
    obs = str(w["observed"])
    pairs = _occupancy_pairs(obs)
    if not pairs:
        return None, ["occupancy witness, but no element:occupancy pairs readable from 'observed'"]
    m = re.search(r"[\[(]\s*(-?\d+\.\d+)\s*,\s*(-?\d+\.\d+)\s*,\s*(-?\d+\.\d+)\s*[\])]",
                  obs + " " + str(w.get("where", "")))
    groups = {}
    for a in cif["atoms"]:
        groups.setdefault((round(a["x"], 3), round(a["y"], 3), round(a["z"], 3)), []).append(a)
    cands = [g for _, g in sorted(groups.items()) if m is None or
             all(abs(g[0][c] - float(t)) <= 2e-3 for c, t in zip("xyz", m.groups()))]
    for g in cands:
        sp = {}
        for a in g:
            sp[a["el"]] = sp.get(a["el"], 0.0) + a["occ"]
        if all(abs(sp.get(e, -9.0) - v) <= 0.01 for e, v in pairs):
            found = ["witnessed occupancies %s found at site (%g, %g, %g):" %
                     (dict(pairs), g[0]["x"], g[0]["y"], g[0]["z"])] + \
                    [cite(cif, a["line"]) for a in g]
            # PRESENCE is established. A refutation additionally needs
            # CONTRADICTION: the required side must be incompatible with what
            # the file says. Before 26 Aug 2026 this function returned True
            # here, so a witness whose observed and required were identical
            # was reported REPRODUCED (adversarial findings, #2 and N5).
            req = str(w["required"])
            req_pairs = _occupancy_pairs(req)
            if req_pairs:
                if all(abs(sp.get(e, -9.0) - v) <= 0.01 for e, v in req_pairs):
                    return False, found + [
                        "the required occupancies %s are the SAME as the "
                        "file's; the witness states no contradiction, so it "
                        "cannot support a refutation" % dict(req_pairs)]
                return True, found + [
                    "the required occupancies %s differ from the file's %s at "
                    "this site; observation and requirement are incompatible"
                    % (dict(req_pairs), {k: round(v, 4) for k, v in sp.items()})]
            if _requires_ordered(claim):
                mixed = len(sp) > 1 or any(abs(v - 1.0) > 1e-6
                                           for v in sp.values())
                if mixed:
                    return True, found + [
                        "the CLAIM RECORD (family %r) requires these species "
                        "on distinct fully occupied sites, and this site is "
                        "shared or partial (%s); the two cannot both hold"
                        % (claim.get("family", "?"),
                           {k: round(v, 4) for k, v in sp.items()})]
                return False, found + [
                    "the claim record requires an ordered arrangement and "
                    "this site is neither shared nor partial; no contradiction"]
            return None, found + [
                "no numeric requirement was given and no claim record was "
                "supplied, so the CONTRADICTION is not established here; "
                "presence alone never validates a refutation. Pass the claim "
                "record as the third argument to adjudicate a family-level "
                "requirement."]
    ev = ["no site in the file carries the witnessed occupancies %s" % dict(pairs)]
    for g in cands[:1] or list(groups.values())[:1]:
        ev += ["the nearest inspected site actually reads:"] + [cite(cif, a["line"]) for a in g]
    return False, ev

def counts_of(formula):
    toks, stack, i = re.findall(r"%s|\d+\.?\d*|[()]" % EL, formula), [{}], 0
    while i < len(toks):
        t = toks[i]; i += 1
        n = 1.0
        if t != "(" and i < len(toks) and re.match(r"[\d.]", toks[i]):
            n = float(toks[i]); i += 1
        if t == "(":
            stack.append({})
        else:
            for e, c in (stack.pop().items() if t == ")" else [(t, 1.0)]):
                stack[-1][e] = stack[-1].get(e, 0.0) + c * n
    return stack[0]

def find_formula(text):
    for m in re.finditer(FORM, text):
        c = counts_of(m.group(0))
        if len(c) >= 2 and re.search(r"\d", m.group(0)):
            return m.group(0), c
    return None, None

def same_ratio(c1, c2, tol=0.02):
    t1, t2 = sum(c1.values()), sum(c2.values())
    return set(c1) == set(c2) and all(abs(c1[e] / t1 - c2[e] / t2) <= tol for e in c1)

def check_stoichiometry(w, cif, claim=None):
    counts = {}
    for a in cif["atoms"]:
        counts[a["el"]] = counts.get(a["el"], 0.0) + a["occ"] * a["mult"]
    obs_f, obs_c = find_formula(str(w["observed"]))
    req_f, req_c = find_formula(str(w["required"]))
    if not counts or not (obs_c or req_c):
        return None, ["stoichiometry witness, but no _atom_site loop or no readable formula"]
    ev = ["occupancy-x-multiplicity contents of the file's _atom_site loop (lines %d-%d): %s" %
          (cif["atoms"][0]["line"], cif["atoms"][-1]["line"], {e: round(n, 4) for e, n in sorted(counts.items())})]
    # A COMPOSITION MATCH IS NOT A CONTRADICTION UNLESS SOMETHING WAS REQUIRED.
    # Fixed 29 August 2026. `ok = same_ratio(counts, obs_c)` stamped
    # "contradiction established" whenever the FIRST formula in the witness's
    # prose matched the deposited file - i.e. whenever the check named the
    # compound it was looking at. Nothing is contradicted by that. With no
    # formula on the required side there is no assertion for the file to
    # differ from, so this predicate has nothing to adjudicate and must say so.
    #
    # THIS IS NOT A RETURN TO KEYWORD ROUTING. adjudicate() still tries every
    # predicate; the 26 August repair stands. What changes is that this
    # predicate stops claiming a contradiction it never established.
    #
    # MEASURED CONSEQUENCE: it fired on weight-fraction witnesses, whose prose
    # naturally opens with the target's own name and whose `required` is a
    # quantity statement carrying no formula. Because stoichiometry is second
    # in the order and refinement-row - the only predicate that reads a weight
    # fraction - is sixth, K6 credit was decided by which formula a sentence
    # happened to mention first. Verified: the same witness flips REPRODUCED
    # by prepending the target formula, and a witness reading "single-phase
    # fit with no impurity" - asserting no contradiction at all - was stamped
    # REPRODUCED.
    # THE REQUIREMENT COMES FROM THE CLAIM RECORD WHERE ONE EXISTS.
    # Added 29 August 2026. This was the only one of the six predicates that
    # never read `claim`: the other five test the file against what was
    # CLAIMED, and this one tested it against the witness's own `required`
    # text, which the untrusted model that wrote the check also wrote. So a
    # witness could require a composition nobody asserted - any formula the
    # file does not match - and collect a contradiction for it. The claim
    # asserts the compound IS its stated composition, so that is the
    # requirement, and the contradiction is the file differing from it.
    claimed_f = ""
    if isinstance(claim, dict):
        claimed_f = str(claim.get("assertion", {}).get("compound", "") or "")
    if claimed_f:
        _, claimed_c = find_formula(claimed_f)
        if claimed_c:
            agree = same_ratio(counts, claimed_c)
            ev.append("requirement read from the claim record: the claim "
                      "asserts the compound is %r, and the file's contents %s "
                      "it, compared as element ratios"
                      % (claimed_f, "MATCH" if agree else "DIFFER FROM"))
            if agree:
                ev.append("no compositional contradiction: the deposited file "
                          "carries the composition the claim asserts")
            return (not agree), ev

    if obs_c and not req_c:
        return None, [
            "stoichiometry witness names %r, which is the deposited "
            "composition, but the required side names no formula: there is "
            "no compositional assertion for the file to contradict, so this "
            "predicate does not apply" % obs_f]
    ok = same_ratio(counts, obs_c) if obs_c else True
    if obs_c:
        ev.append("witnessed composition %r %s the file's, compared as element ratios" %
                  (obs_f, "MATCHES" if ok else "DOES NOT MATCH"))
    if req_c:
        agree = same_ratio(counts, req_c)
        ev.append("required-side formula %r: the file %s it, compared as element ratios (never as strings)" %
                  (req_f, "MATCHES" if agree else "DIFFERS FROM"))
        if obs_c is None:
            ok = not agree
        elif agree:
            ev.append("the witnessed composition is in the file but does not contradict the required "
                      "formula once both are reduced to ratios")
            ok = False
    return ok, ev

def _cell_params(text):
    return re.findall(r"\b(alpha|beta|gamma|a|b|c)\s*[=:]\s*(-?\d+\.?\d*)",
                      str(text))


def check_lattice(w, cif, claim=None):
    want = _cell_params(w["observed"])
    if not want:
        return None, ["lattice witness, but no named cell parameter (a/b/c/alpha/beta/gamma = value) in 'observed'"]
    ok, ev = True, []
    for name, val in want:
        if LTAG[name] not in cif["tags"]:
            return False, ["the file carries no %s tag" % LTAG[name]]
        raw, ln = cif["tags"][LTAG[name]]
        hit = abs(num(raw) - float(val)) <= max(0.02, 0.002 * abs(num(raw)))
        ev += ["%s witnessed as %s; the file SAYS:" % (name, val),
               cite(cif, ln) + ("" if hit else "   <- does not match the witnessed value")]
        ok = ok and hit
    if not ok:
        return False, ev
    # PRESENCE established; now CONTRADICTION, as for occupancy (findings #2).
    req = _cell_params(w["required"])
    if not req:
        return None, ev + [
            "the required side names no cell parameter this checker can "
            "compare, so the CONTRADICTION is not established; the observed "
            "values being in the file never validates a refutation by itself"]
    for name, val in req:
        if LTAG[name] not in cif["tags"]:
            continue
        raw, _ = cif["tags"][LTAG[name]]
        if abs(num(raw) - float(val)) > max(0.02, 0.002 * abs(num(raw))):
            return True, ev + [
                "the claim required %s = %s and the file states %s; "
                "observation and requirement are incompatible"
                % (name, val, raw)]
    return False, ev + [
        "every required cell parameter agrees with the file within tolerance; "
        "the witness states no contradiction"]

SG_SYMBOL = re.compile(r"\b([PABCIFR])\s*[0-9mnacdbe/_\-\.]{1,12}\b", re.I)
SG_NUMBER = re.compile(r"(?:#|\bno\.?\s*|\bnumber\s+)(\d{1,3})\b", re.I)

# Two-letter tokens that are element symbols before they are space groups.
# Pm, Cm and Fm are genuinely both; a bare one in prose is not evidence of a
# symmetry requirement, so it is not read as one. Where the requirement really
# is such a group, the claim record carries it (see check_symmetry).
ELEMENT_LOOKALIKES = {
    "p", "pd", "pt", "pb", "pr", "pm", "po", "pa", "ac", "ag", "al", "am",
    "ar", "as", "at", "au", "b", "ba", "be", "bh", "bi", "bk", "br", "c",
    "ca", "cd", "ce", "cf", "cl", "cm", "cn", "co", "cr", "cs", "cu", "i",
    "in", "ir", "f", "fe", "fl", "fm", "fr", "ra", "rb", "re", "rf", "rg",
    "rh", "rn", "ru",
}


def _norm_sg(s):
    return re.sub(r"[\s_'\"]", "", str(s)).lower()


def _sg_tokens(text):
    """Space-group designations named in a piece of text: normalised H-M
    symbols and International Tables numbers. Conservative by design - a token
    that is more plausibly an element symbol is not counted, because a false
    symbol here manufactures a contradiction that does not exist."""
    syms = set()
    for m in SG_SYMBOL.finditer(str(text)):
        tok = _norm_sg(m.group(0))
        if tok in ELEMENT_LOOKALIKES and not re.search(r"[0-9/\-]", tok):
            continue
        syms.add(tok)
    nums = set()
    for m in SG_NUMBER.finditer(str(text)):
        n = int(m.group(1))
        if 1 <= n <= 230:
            nums.add(n)
    return syms, nums


def check_symmetry(w, cif, claim=None):
    hit = [t for t in ("_symmetry_space_group_name_h-m", "_space_group_name_h-m_alt") if t in cif["tags"]]
    if not hit:
        return None, ["the file states no space-group symbol tag"]
    raw, ln = cif["tags"][hit[0]]
    ev = ["documentary read: what the file SAYS in its symmetry tags, nothing recomputed:", cite(cif, ln)]
    file_num = None
    for t in ("_symmetry_int_tables_number", "_space_group_it_number"):
        if t in cif["tags"]:
            ev.append(cite(cif, cif["tags"][t][1]))
            try:
                file_num = int(float(cif["tags"][t][0]))
            except Exception:
                pass

    # PRESENCE: the file's stated symbol must be what the witness observed
    if _norm_sg(raw) not in _norm_sg(w["observed"]):
        return False, ev + [
            "the file's stated symbol %r does not appear in the witness's "
            "observed text; if that value came from recomputed symmetry, this "
            "checker cannot and will not reproduce it" % raw]

    # CONTRADICTION: the required side must name a DIFFERENT group. Absence of
    # the file's symbol from the required text is not a contradiction - a
    # required side that names no space group at all would satisfy it
    # vacuously, which is how this predicate failed open until 26 Aug 2026
    # (second adversarial pass): any witness quoting the deposited tag was
    # certified, and because adjudicate takes any established contradiction,
    # that also rescued witnesses other predicates had refused.
    # the requirement is read from the CLAIM RECORD when one is supplied -
    # trusted data - and only otherwise from the witness's own required text
    claimed = ""
    if isinstance(claim, dict):
        claimed = str(claim.get("assertion", {}).get("space_group_claimed", "")
                      or claim.get("space_group_claimed", ""))
    if claimed and claimed.lower() not in ("unstated", "unknown", "not stated"):
        req_syms, req_nums = _sg_tokens(claimed)
        ev.append("requirement read from the claim record: %r" % claimed)
    else:
        req_syms, req_nums = _sg_tokens(w["required"])
    if not req_syms and not req_nums:
        return None, ev + [
            "the required side names no space group, so the CONTRADICTION is "
            "not established; the file's symbol merely being absent from the "
            "required text is not a contrast"]
    if req_syms:
        if _norm_sg(raw) in req_syms:
            return False, ev + [
                "the required side names the same group %r the file states; "
                "no contradiction" % raw]
        return True, ev + [
            "the file states %r and the claim required %s; the tags and the "
            "requirement name different groups"
            % (raw, ", ".join(sorted(req_syms)))]
    if file_num is None:
        return None, ev + [
            "the required side names only an International Tables number and "
            "the file carries no number tag to compare it with"]
    if file_num in req_nums:
        return False, ev + [
            "the required side names the same International Tables number %d "
            "the file states; no contradiction" % file_num]
    return True, ev + [
        "the file states International Tables number %d and the claim "
        "required %s; they differ"
        % (file_num, ", ".join(str(n) for n in sorted(req_nums)))]



# ---------------------------------------------------------------------------
# EVIDENCE THAT DOES NOT LIVE IN THE DEPOSITED FILE
#
# Until 28 August 2026 this program opened exactly one artifact, the deposited
# structure file, and its four predicates all read it. Handed a witness citing
# a reference-corpus entry or a refinement row it ran those predicates anyway,
# found no contradiction IN THE CIF, and returned False - "applied, no
# contradiction" - which reads as "the arm was wrong". It was not equipped to
# say so, and the cost was measured: 79 novelty refutations across four arms
# that could never be validated, K3 pinned at 0 for every arm, and K6 unable
# to exceed the do-nothing line because no weight-fraction refutation could
# ever be adjudicated.
#
# THE INDEPENDENCE THAT MATTERS IS PRESERVED. This program still shares no code
# with the layer and still imports nothing outside the standard library: the pinned
# corpus is gzip+json, and the refinement workbook is a zip of XML read with
# zipfile and xml.etree. It re-derives each observation from the primary
# artifact itself rather than calling the layer that produced the witness -
# which is the same relationship it already had to the CIF.
#
# WHAT TRAVELS. A corpus verdict is licence-bound: the snapshot is not
# redistributable, so a reader without it cannot reproduce that verdict. That
# condition is returned in the evidence rather than hidden.

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_CORPUS_CACHE = {}
_XLSX_CACHE = {}


def _load_corpus(name):
    """The pinned reference snapshot, {system: [[formula, id, sg, dev], ...]}."""
    if name in _CORPUS_CACHE:
        return _CORPUS_CACHE[name]
    import gzip
    path = os.path.join(ROOT, "data", "reference", name + ".json.gz")
    try:
        with gzip.open(path) as fh:
            _CORPUS_CACHE[name] = json.load(fh)
    except Exception:
        _CORPUS_CACHE[name] = None
    return _CORPUS_CACHE[name]


def _load_xlsx_rows():
    """The refinement workbook, as rows of strings. zipfile + xml.etree only."""
    if "rows" in _XLSX_CACHE:
        return _XLSX_CACHE["rows"]
    import zipfile
    import xml.etree.ElementTree as ET
    M = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
    out = []
    try:
        z = zipfile.ZipFile(os.path.join(ROOT, "data", "cifs",
                                         "Refinement-Table.xlsx"))
        shared = []
        if "xl/sharedStrings.xml" in z.namelist():
            r = ET.fromstring(z.read("xl/sharedStrings.xml"))
            for si in r.findall("{%s}si" % M):
                shared.append("".join(x.text or "" for x in si.iter("{%s}t" % M)))
        sheet = [n for n in z.namelist() if n.startswith("xl/worksheets/sheet")][0]
        root = ET.fromstring(z.read(sheet))
        for tr in root.iter("{%s}row" % M):
            cells = []
            for c in tr.findall("{%s}c" % M):
                v = c.find("{%s}v" % M)
                val = "" if v is None else (
                    shared[int(v.text)] if c.get("t") == "s" else v.text)
                cells.append(val or "")
            out.append(cells)
    except Exception:
        out = []
    _XLSX_CACHE["rows"] = out
    return out


def check_reference_corpus(w, cif, claim=None):
    """Is the compound already present in the pinned reference snapshot?

    Applies only when the witness names a snapshot or cites entry identifiers.
    The contradiction is established against the CLAIM RECORD - a novelty claim
    asserts the compound is previously unreported - and never against the
    witness's own `required` text.
    """
    blob = "%s %s %s" % (w.get("where", ""), w.get("observed", ""),
                         w.get("required", ""))
    snaps = re.findall(r"(icsd[\w]*|cod[\w]*)_?(?:filtered)?[\w]*", blob, re.I)
    cited = set(re.findall(r"\b(\d{4,7})\b", str(w.get("observed", ""))))
    if not snaps and not cited:
        return None, ["no reference snapshot or entry identifier named in the "
                      "witness; this predicate does not apply"]

    name = "icsd_filtered_info_2025_v3" if re.search(r"icsd", blob, re.I) \
        else "cod_filtered_info_2024"
    corpus = _load_corpus(name)
    if corpus is None:
        return None, ["the pinned snapshot %r is not on disk; a corpus verdict "
                      "is licence-bound and cannot be reproduced without it"
                      % name]

    compound = (claim or {}).get("assertion", {}).get("compound") or \
        (claim or {}).get("compound") or ""
    els = sorted(set(re.findall(r"[A-Z][a-z]?", compound)))
    system = "-".join(sorted(els))
    entries = corpus.get(system)
    if entries is None:
        for k in corpus:
            if sorted(k.split("-")) == els:
                entries = corpus[k]; system = k; break
    if entries is None:
        return False, ["the pinned snapshot holds no entry for the chemical "
                       "system %r, so it does not contradict a novelty claim"
                       % system]

    ids = {str(e[1]) for e in entries if len(e) > 1}
    found = sorted(cited & ids)
    ev = ["snapshot %r, system %r: %d entries" % (name, system, len(entries)),
          "LICENCE-BOUND: a reader without this snapshot cannot reproduce "
          "this verdict"]
    if cited and not found:
        ev.append("the witness cites %s and the snapshot contains none of them"
                  % sorted(cited))
        return False, ev
    if found:
        hit = [e for e in entries if str(e[1]) in found]
        ev.append("the snapshot CONTAINS the cited entr%s %s: %s"
                  % ("y" if len(found) == 1 else "ies", found,
                     [(e[0], e[1]) for e in hit]))
        ev.append("a novelty claim asserts the compound is previously "
                  "unreported; a present entry of this composition "
                  "contradicts that")
        return True, ev
    ev.append("the witness names a snapshot but cites no entry identifier the "
              "checker can confirm, so presence is not established")
    return False, ev


def check_refinement_row(w, cif, claim=None):
    """Do the reported phase fractions say what the witness says they say?

    Reads the deposited refinement workbook directly. Presence of the cited
    figures is necessary and never sufficient: the contradiction is between
    what the refinement reported and what the claim required.
    """
    obs = str(w.get("observed", ""))
    nums = [float(x) for x in re.findall(r"(\d+\.\d+)\s*(?:wt)?\s*%", obs)]
    if not re.search(r"refinement|wt\s*%|rwp|phase", obs, re.I) or not nums:
        return None, ["no refinement figures in the witness; this predicate "
                      "does not apply"]

    rows = _load_xlsx_rows()
    if not rows:
        return None, ["the refinement workbook could not be read"]
    compound = (claim or {}).get("assertion", {}).get("compound") or \
        (claim or {}).get("compound") or ""
    row = None
    for r in rows:
        if r and str(r[0]).strip() == compound:
            row = r; break
    if row is None:
        return None, ["no row for %r in the refinement workbook" % compound]

    # WHICH STAGE THE WITNESS NAMED (29 Aug 2026). Column 2 is the automated
    # analysis (stage one); column 3 is the expert re-refinement (stage two).
    # This predicate read column 2 unconditionally, so a witness that cites
    # ctx.refinement_row(stage="two") was checked against stage-one figures,
    # none of which match, and was refused. The refusal looked like the
    # verifier inventing numbers when it had quoted the released row exactly.
    #
    # DETECTION IS ON `where` ONLY, and deliberately so. `where` is the call
    # the check actually made; `observed` is prose the model wrote and may
    # say "stage two" about a stage-one row. Across the 1,024 witnesses banked
    # before this change, exactly one mentions stage two anywhere and its
    # `where` names no stage, so every existing witness keeps the column it
    # was judged against and no banked verdict moves.
    where = str(w.get("where", ""))
    cites_two = bool(re.search(r"refinement_row\s*\([^)]*\btwo\b", where, re.I)
                     or re.search(r"stage\s*=?\s*['\"]two['\"]", where, re.I))
    cites_one = bool(re.search(r"refinement_row\s*\([^)]*\bone\b", where, re.I)
                     or re.search(r"stage\s*=?\s*['\"]one['\"]", where, re.I))
    auto = row[2] if len(row) > 2 else ""
    manual = row[3] if len(row) > 3 else ""
    if cites_two and not cites_one:
        cells, which = [manual], "manual-analysis (stage two)"
    elif cites_two and cites_one:
        # the check compared the two stages; either row may carry the figure
        cells, which = [auto, manual], "automated and manual analysis cells"
    else:
        cells, which = [auto], "automated-analysis"
    table, rwp = [], []
    for cell in cells:
        table += [float(x) for x in re.findall(r"\[(\d+\.?\d*)%\]", cell)]
        rwp += re.findall(r"Rwp\s*=\s*(\d+\.?\d*)", cell)
    ev = ["refinement workbook, %s cell for %r: %s"
          % (which, compound, " | ".join(cells).replace(chr(10), " | ")[:200])]

    confirmed = [n for n in nums
                 if any(abs(n - t) <= 0.011 for t in table)
                 or any(abs(n - float(x)) <= 0.011 for x in rwp)]
    if not confirmed:
        ev.append("none of the witnessed figures %s appears in the reported "
                  "row %s" % (nums, table))
        return False, ev
    ev.append("witnessed figures %s confirmed against the reported row"
              % confirmed)

    thr = (claim or {}).get("assertion", {}).get("threshold")
    target = table[0] if table else None
    if thr is not None and target is not None:
        pct = float(thr) * 100 if float(thr) <= 1 else float(thr)
        if target < pct:
            ev.append("the refinement reports the target phase at %.2f wt%%, "
                      "below the %.1f wt%% the claim asserts" % (target, pct))
            return True, ev
        ev.append("the reported target fraction %.2f wt%% meets the claim's "
                  "%.1f wt%%, so the row does not contradict it" % (target, pct))
        return False, ev
    if target is not None and target < 100.0:
        ev.append("the refinement reports the target phase at %.2f wt%% with "
                  "other phases present; the claim record states no threshold, "
                  "so this is recorded and NOT counted as a contradiction"
                  % target)
        return False, ev
    return False, ev


CLASSES = (("occupancy", check_occupancy),
           ("stoichiometry", check_stoichiometry),
           ("lattice-metric", check_lattice),
           ("symmetry-tag", check_symmetry),
           ("reference-corpus", check_reference_corpus),
           ("refinement-row", check_refinement_row))


def adjudicate(w, cif, claim=None):
    """Validate a witness by TRYING EVERY PREDICATE, not by guessing one from
    keywords. Returns (verdict, class that decided, evidence, all attempts).

    Replaces keyword classification, 26 Aug 2026 (adversarial findings N2, and
    a failure found while repairing it). Real witnesses are prose that names
    occupancies, a cell and a space group at once, because that is how a
    crystallographer argues; any keyword rule routes some genuine refutations
    to a predicate that cannot adjudicate them. The old rule sent ordering
    refutations to the occupancy checker, which then passed them on presence
    alone; ordering them differently merely moved which true refutations came
    back UNSUPPORTED.

    The rule instead: a witness is REPRODUCED if ANY predicate establishes a
    contradiction between what the file says and what the claim required -
    one genuine contradiction is a refutation, whatever else the prose
    mentions. If no predicate establishes one but at least one APPLIED and
    found none, the witness is NOT REPRODUCED. If no predicate could apply at
    all, it is UNSUPPORTED. Every attempt is reported, so a reader sees which
    predicate decided and what the others said.
    """
    attempts = []
    established = None      # (class, evidence) of the predicate that decided
    refused = None          # (class, evidence) of a predicate that applied
    for name, fn in CLASSES:
        try:
            ok, ev = fn(w, cif, claim)
        except Exception as exc:
            attempts.append((name, "error: %s" % type(exc).__name__))
            continue
        attempts.append((name, {True: "contradiction established",
                                False: "applied, no contradiction",
                                None: "not applicable"}[ok]))
        if ok is True and established is None:
            established = (name, ev)
        elif ok is False and refused is None:
            refused = ("%s (no contradiction)" % name, ev)
    # the reported justification must be the one that produced the verdict:
    # reporting a 'no contradiction' evidence block under a REPRODUCED
    # headline misleads the auditor the checker exists to serve
    if established is not None:
        return True, established[0], established[1], attempts
    if refused is not None:
        return False, refused[0], refused[1], attempts
    return None, None, [], attempts


# NOTE. A keyword classifier lived here until 26 Aug 2026: it guessed a single
# predicate from words in the witness text ("occupan", "space group", "cell").
# It was removed, not merely bypassed. Guessing which contradiction a witness
# asserts from its vocabulary was wrong in both directions - it routed genuine
# ordering refutations to a predicate that could not adjudicate them, and its
# ordering determined which true refutations were lost. adjudicate() tries every
# predicate instead, and each one establishes a contradiction or declines.


def main(argv):
    if len(argv) == 2 and argv[1] == "--predicates":
        print("The four witness-class predicates (the checker verifies the "
              "predicate, never the claim):\n")
        for kind, pred in PREDICATES.items():
            print("%s:\n  %s\n" % (kind, pred))
        return 0
    if len(argv) not in (3, 4):
        print(__doc__)
        return 2
    w = json.load(open(argv[1]))
    w = w.get("witness", w)
    if not all(k in w for k in ("where", "observed", "required")):
        print("not a witness: needs keys 'where', 'observed', 'required'")
        return 2
    cif = parse_cif(argv[2])
    claim = None
    if len(argv) == 4:
        try:
            claim = json.load(open(argv[3]))
        except Exception as exc:
            print("claim record unreadable (%s); continuing without it, so "
                  "family-level requirements cannot be adjudicated" % exc)
    ok, decided, ev, attempts = adjudicate(w, cif, claim)
    print("witness  : %s\ndeposited: %s" % (argv[1], argv[2]))
    print("predicates tried:")
    for name, note in attempts:
        print("  %-16s %s" % (name, note))
    print("decided by: %s\n" % (decided or "none"))
    print({True: "WITNESS REPRODUCED", False: "WITNESS NOT REPRODUCED",
           None: "UNSUPPORTED CLASS"}[ok])
    for line in ev or ["no predicate could adjudicate this witness; this "
                       "checker decides occupancy, stoichiometry, "
                       "lattice-metric and symmetry-tag contradictions only"]:
        print("  " + line)
    print("\nchecked the witness against the deposited file only; nothing above judges "
          "the chemistry or affirms the claim")
    return {True: 0, False: 1, None: 2}[ok]

if __name__ == "__main__":
    sys.exit(main(sys.argv))

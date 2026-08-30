# Rival structures for the named-rival pricing run

*Fetched 23 Aug 2026: six files from the Crystallography Open Database
(COD) REST interface, one from the ICSD via PSDI institutional access.
Input acquisition only: no pricing has run against these files.
Status: UNROWED until register rows exist. The rival identities come from
the critics (PRX Energy 3, 011002, 2024, Table III, transcription
data/labels/prx_table3.csv) and, where stated, from the Correction's own
rival list. Nothing here is a chemical judgement of ours: every identity
is a published identification; every departure from a published file is a
declared construction.*

## Selection rule (mechanical, in order)

1. Exact reduced-composition match to the named rival, where one exists.
2. Space group must match the critics' stated symmetry for that rival.
3. Entry must carry coordinates.
4. Lowest COD number among the remainder.

COD is fully open; these files are redistributable. A third party can
re-fetch every file by its COD number and confirm the hash.

## Fetched files (data/rivals/cod/)

| Rival (named by) | For claim | ICSD code cited | COD file | pymatgen check (symprec 0.1) | SHA-256 |
|---|---|---|---|---|---|
| Gd2O3 [critics] | KBaGdWO6 | 40473 | 2106881.cif | Gd2O3, Ia-3 (206) - matches stated Ia-3 | e3845bb78718186b94058728465f167deeb1ca804da4f5d60863dc10a1c16369 |
| Mn2(PO3)4 [critics] | Mn7(P2O7)4 | 145534 | 1534609.cif | Mn(PO3)2, C2/c (15) - matches stated C12/c1 | 5cbd189aba591b574239933cfcdb28ee5e348a937ee364caac6d13356dd3e952 |
| NiO [critics] | Mg3MnNi3O8 | 9866 | 1010093.cif | NiO, Fm-3m (225) - matches stated Fm-3m | 3ed7bcc3f5935677d626f5f5cc0fdabaac2f6ac1dc770ef7014edcc860ffbd17 |
| (Ni;Mn)(Ni;Mn)2O4 spinel [critics] | Mg3MnNi3O8 | 84517 | 1530384.cif | Mn2NiO4, Fd-3m (227) - matches stated Fd-3m; same phase type, end-member composition (see constructions) | e89d67a3f51076abc29418ef0f19718be35013f55591177d9c09b9e168aaef72 |
| Ni6MnO8 [Correction] | Mg3MnNi3O8 | 80301 | 9013975.cif | Mn(Ni3O4)2 = MnNi6O8, Fm-3m (225) | 49253ac6a8b08ffe073bd502cd1b7eda5311c3edf40f2844d8e5bd84aae5e358 |
| Gd3Ga5O12 parent garnet (for the critics' garnet rival) | CaGd2Zr(GaO3)4 | parent of 202850 | 9013458.cif | Gd3Ga5O12, Ia-3d (230) - matches stated Ia-3d | 084e8bcd9f584e82dc124eea4761cf4f9b60831679dcbee23a9ac8b4cfdc4f10 |

## Fetched via institutional access (data/rivals/icsd/) - not redistributable

Obtained 23 Aug 2026 by the owner through PSDI (UK academic ICSD web
access). Held privately for the pricing run; the public benchmark ships
the collection code, the hash, and any derived pattern, never this file.
A third party with ICSD access re-fetches by code and confirms the hash.

| Rival (named by) | For claim | ICSD code | File | pymatgen check (symprec 0.1) | SHA-256 |
|---|---|---|---|---|---|
| Ba2GdWO6 [critics] | KBaGdWO6 (primary rival) | 138973 | icsd/138973.cif | Ba2GdWO6, Fm-3m (225) - matches stated Fm-3m | dd9f4d330611ad4d4e55271adeed2f459112e393ead656e132ebbc8d3046021b |

## Licence-walled: named in the record, no open equivalent found

These ICSD entries have no COD match by the selection rule. A third party
with ICSD access re-fetches them by code; the benchmark carries the code,
our derived pattern, and the hash of whatever construction substitutes.

| ICSD code | Phase | For claim | Standing |
|---|---|---|---|
| 138973 | Ba2GdWO6, Fm-3m double perovskite | KBaGdWO6 (primary rival) | RESOLVED 23 Aug 2026: fetched via PSDI institutional access (table above). No COD 1:1 Gd:W entry exists (the one Ba-Gd-W-O hit, COD 1533181, is a 2:1 phase and fails rule 1) |
| 202850 | Ca0.95Zr0.95Gd2.05Ga4.05O12 garnet | CaGd2Zr(GaO3)4 | Parent garnet fetched (COD 9013458); the substituted composition is a declared construction on it |
| 84517 | (Ni;Mn)(Ni;Mn)2O4 mixed spinel | Mg3MnNi3O8 | COD 1530384 is the same phase type at end-member composition; site mixing is a declared construction on it |
| 80306 | Mg3MnNi3O8 (the claim itself as a known phase, per the Correction) | Mg3MnNi3O8 | No COD hit; documentary note only |

## Declared constructions (to be built at pricing time, provenance-labelled)

Per the rival-generation architecture decision (12 Aug 2026): rival sets
for verdicts come only from declared closed sources; occupancy or
composition adjustments on a fetched parent are constructions and their
provenance travels with every number, the CL-28 pattern.

1. Garnet rival: COD 9013458 with the critics' stated Ca and Zr
   substitution applied as site occupancies.
2. Spinel rival: COD 1530384 with cation mixing applied per the ICSD 84517
   identification.
3. Ba2GdWO6: RESOLVED 23 Aug 2026 by the ICSD fetch above; no
   construction needed.

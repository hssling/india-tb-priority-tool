# Where to invest against TB in India: a State and district priority tool

Status: under construction. No estimate has been computed yet.

This repository will hold a pre-registered, reproducible tool that ranks India's
States/UTs (and, as a demonstration, the districts of Madhya Pradesh and
Maharashtra) by where closing a gap in the TB care pathway would avert the most
harm, with uncertainty, tiers and trajectory.

- Design: `docs/superpowers/specs/2026-11-21-tb-priority-tool-design.md`
- Plan: `docs/superpowers/plans/2026-11-21-tb-priority-tool.md`
- What the sources print (structure only): `docs/data_inventory.md`

## Sources

The source documents are not redistributed. `data/source_manifest.csv` lists
each file with its origin, size and SHA-256 digest. With the sibling
repositories `tb_state_score` and `tb_acf_campaign` checked out next to this
one, and the author-supplied Lok Sabha answers in `data_raw/pq/`, run

    python -I tools/fetch_sources.py
    python -I -m pytest -q

## Licences

Code: MIT (`LICENSE`). Derived data: CC BY 4.0 (`LICENSE-DATA`).

Author: Siddalingaiah H S (ORCID 0000-0002-4771-8285), Department of Community
Medicine, Shridevi Institute of Medical Sciences and Research Hospital, Tumkur.

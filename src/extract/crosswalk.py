"""Printed State/UT names -> printed unit -> coarsened unit (analysis plan §4).

Every edition prints its own spelling of each State/UT. This module maps a
printed name, for a given data year, in two steps:

1. ``printed_unit(raw, year)``: the canonical name of the printed row (36 rows
   per year). The 2018 and 2019 data years print Dadra and Nagar Haveli and
   Daman and Diu as two rows and have no Ladakh row; from 2021 they print one
   merged "Dadra and Nagar Haveli and Daman and Diu" row and a Ladakh row.
2. ``unit_name(raw, year)``: the coarsened unit (33 units in every year). By
   the plan's ruling, units are coarsened to the 2018 structure: DNH and DD
   (or the merged DNH&DD row) -> Gujarat, Lakshadweep -> Kerala, Ladakh ->
   Jammu and Kashmir.

The crosswalk is explicit: every accepted spelling is listed in SPELLINGS.
A name that is not listed, or that is not a printed row in that data year,
raises KeyError naming the raw string. The national row is not a unit;
``is_national`` recognises it.
"""
from __future__ import annotations

import re

YEARS: tuple[int, ...] = (2018, 2019, 2021, 2022, 2023)

DNH = "Dadra and Nagar Haveli"
DD = "Daman and Diu"
DNHDD = "Dadra and Nagar Haveli and Daman and Diu"

# The 33 coarsened units (plan §4), alphabetical.
UNITS: tuple[str, ...] = (
    "Andaman and Nicobar Islands", "Andhra Pradesh", "Arunachal Pradesh", "Assam",
    "Bihar", "Chandigarh", "Chhattisgarh", "Delhi", "Goa", "Gujarat", "Haryana",
    "Himachal Pradesh", "Jammu and Kashmir", "Jharkhand", "Karnataka", "Kerala",
    "Madhya Pradesh", "Maharashtra", "Manipur", "Meghalaya", "Mizoram", "Nagaland",
    "Odisha", "Puducherry", "Punjab", "Rajasthan", "Sikkim", "Tamil Nadu",
    "Telangana", "Tripura", "Uttar Pradesh", "Uttarakhand", "West Bengal",
)

# Printed rows merged into a coarsened unit (plan §4, ruling "Unit coarsening").
MERGED_INTO: dict[str, str] = {
    DNH: "Gujarat",
    DD: "Gujarat",
    DNHDD: "Gujarat",
    "Lakshadweep": "Kerala",
    "Ladakh": "Jammu and Kashmir",
}

_COMMON = tuple(u for u in UNITS) + ("Lakshadweep",)
# The printed rows of each data year (36 in every year).
PRINTED: dict[int, tuple[str, ...]] = {
    2018: tuple(sorted(_COMMON + (DNH, DD))),
    2019: tuple(sorted(_COMMON + (DNH, DD))),
    2021: tuple(sorted(_COMMON + (DNHDD, "Ladakh"))),
    2022: tuple(sorted(_COMMON + (DNHDD, "Ladakh"))),
    2023: tuple(sorted(_COMMON + (DNHDD, "Ladakh"))),
}

NATIONAL = "India"
_NATIONAL_SPELLINGS = frozenset({"india", "grand total"})


def _norm(s: str) -> str:
    """'&' = 'and', whitespace collapsed, case folded."""
    s = s.replace("&", " and ")
    return re.sub(r"\s+", " ", s).strip().casefold()


# Spellings seen in the tables used that differ from a canonical name by more
# than "&"/"and", case or spacing (those are matched by _norm), normalised ->
# canonical printed row. The canonical names themselves are added below.
_ALIASES: dict[str, str] = {
    # ITR 2019 Annexure 1.4.a prints "Lakshwadeep" [sic].
    "Lakshwadeep": "Lakshadweep",
}

SPELLINGS: dict[str, str] = {_norm(n): n for y in YEARS for n in PRINTED[y]}
SPELLINGS.update({_norm(k): v for k, v in _ALIASES.items()})


def is_national(raw: str) -> bool:
    return _norm(raw) in _NATIONAL_SPELLINGS


def printed_unit(raw: str, year: int) -> str:
    """Canonical printed row for `raw` in data year `year`; KeyError naming raw."""
    if year not in PRINTED:
        raise KeyError(f"no crosswalk for data year {year} (printed name {raw!r})")
    name = SPELLINGS.get(_norm(raw))
    if name is None:
        raise KeyError(f"printed unit name not in the crosswalk: {raw!r} (data year {year})")
    if name not in PRINTED[year]:
        raise KeyError(f"printed unit name {raw!r} is not a printed row in data year {year}")
    return name


def coarsen(printed: str) -> str:
    """Coarsened unit of a canonical printed row."""
    return MERGED_INTO.get(printed, printed)


def unit_name(raw: str, year: int) -> str:
    """Coarsened unit (one of UNITS) for printed name `raw` in data year `year`.

    Raises KeyError naming `raw` when the name is not in the crosswalk or is
    not a printed row in that year.
    """
    return coarsen(printed_unit(raw, year))


def members(unit: str, year: int) -> tuple[str, ...]:
    """Printed rows of `year` that make up coarsened `unit` (the unit itself first)."""
    if unit not in UNITS:
        raise KeyError(f"not a coarsened unit: {unit!r}")
    rest = sorted(p for p in PRINTED[year] if p != unit and coarsen(p) == unit)
    return (unit, *rest)


def is_prefix(text: str, year: int) -> bool:
    """True if `text` is a whole printed name of `year`, the national label, or
    the start of one (whole words)."""
    n = _norm(text)
    if not n:
        return False
    keys = [k for k, v in SPELLINGS.items() if v in PRINTED[year]] + list(_NATIONAL_SPELLINGS)
    return any(k == n or k.startswith(n + " ") for k in keys)


def is_complete(text: str, year: int) -> bool:
    """True if `text` is a whole printed name of `year` or the national label."""
    if is_national(text):
        return True
    try:
        printed_unit(text, year)
    except KeyError:
        return False
    return True


assert len(UNITS) == 33
assert all(len(PRINTED[y]) == 36 for y in YEARS)
assert all({coarsen(p) for p in PRINTED[y]} == set(UNITS) for y in YEARS)

"""Load Hero Data, Quest Data from TSVs into Python structures."""

from __future__ import annotations
import csv
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

TSV_DIR = Path(__file__).parent.parent / "sheet" / "formulas"


def _col_to_idx(col: str) -> int:
    """Excel column letter(s) to 0-based index. A→0, Z→25, AA→26."""
    idx = 0
    for ch in col.upper():
        idx = idx * 26 + (ord(ch) - ord("A") + 1)
    return idx - 1


def _parse_cell_ref(ref: str) -> tuple[int, int]:
    """'AB12' → (col_idx, row_idx) both 0-based."""
    m = re.match(r"([A-Za-z]+)(\d+)", ref)
    if not m:
        raise ValueError(f"Bad cell ref: {ref!r}")
    return _col_to_idx(m.group(1)), int(m.group(2)) - 1


def load_tsv_as_grid(path: Path) -> dict[tuple[int, int], Any]:
    """Parse a cell-reference TSV into {(col, row): value} dict."""
    grid: dict[tuple[int, int], Any] = {}
    with open(path, encoding="utf-8", newline="") as f:
        reader = csv.reader(f, delimiter="\t")
        for raw in reader:
            # skip comment lines and the header row
            if not raw or raw[0].startswith("#") or raw[0] == "cell":
                continue
            cell_ref, typ, content, *rest = raw
            cached = rest[0] if rest else ""
            value = cached if (typ == "F" and cached != "") else content
            if value == "" or value is None:
                continue
            # try numeric coercion
            try:
                value = float(value)
            except (ValueError, TypeError):
                pass
            col, row = _parse_cell_ref(cell_ref)
            grid[(col, row)] = value
    return grid


def grid_to_rows(
    grid: dict[tuple[int, int], Any],
    header_row: int,
    start_row: int,
    col_start: int,
    col_end: int,
) -> tuple[list[str], list[dict[str, Any]]]:
    """
    Extract a rectangular region from the grid.
    header_row / start_row / col_start / col_end are all 0-based.
    Returns (headers, list_of_row_dicts).
    """
    headers = [
        str(grid.get((c, header_row), f"col{c}"))
        for c in range(col_start, col_end + 1)
    ]
    rows = []
    row = start_row
    while True:
        # a row exists if at least one cell in the range is populated
        cells = {
            c: grid.get((c, row))
            for c in range(col_start, col_end + 1)
            if (c, row) in grid
        }
        if not cells:
            break
        record = {headers[c - col_start]: grid.get((c, row), "") for c in range(col_start, col_end + 1)}
        rows.append(record)
        row += 1
    return headers, rows


# ---------------------------------------------------------------------------
# Hero Data
# ---------------------------------------------------------------------------

@dataclass
class HeroData:
    name: str
    hero_class: str
    innate_skill_tier: float
    aurasong: str
    hp: float
    atk: float
    defense: float
    threat: float
    crit_chance: float
    crit_multiplier: float
    evasion: float
    element: float
    element_type: str
    armadillo: float
    lizard: float
    shark: float
    dinosaur: float
    mundra: float
    dmg_bonus_pct: float
    def_bonus_pct: float
    artifact: str = ""
    import_string: str = ""


def load_hero_data(tsv_dir: Path = TSV_DIR) -> dict[str, HeroData]:
    grid = load_tsv_as_grid(tsv_dir / "Hero Data.tsv")

    def g(col: int, row: int, default=0):
        return grid.get((col, row), default)

    heroes: dict[str, HeroData] = {}
    # row 1 = group headers (0-based row 0), row 2 = col headers (row 1), data starts row 3 (row 2)
    row = 2  # 0-based
    while True:
        name = g(0, row, None)
        if name is None:
            break
        name = str(name).strip()
        heroes[name] = HeroData(
            name=name,
            hero_class=str(g(1, row, "")),
            innate_skill_tier=float(g(2, row, 0) or 0),
            aurasong=str(g(3, row, "")),
            hp=float(g(4, row, 0) or 0),
            atk=float(g(5, row, 0) or 0),
            defense=float(g(6, row, 0) or 0),
            threat=float(g(7, row, 0) or 0),
            crit_chance=float(g(8, row, 0) or 0),
            crit_multiplier=float(g(9, row, 0) or 0),
            evasion=float(g(10, row, 0) or 0),
            element=float(g(11, row, 0) or 0),
            element_type=str(g(12, row, "")),
            armadillo=float(g(13, row, 0) or 0),
            lizard=float(g(14, row, 0) or 0),
            shark=float(g(15, row, 0) or 0),
            dinosaur=float(g(16, row, 0) or 0),
            mundra=float(g(17, row, 0) or 0),
            dmg_bonus_pct=float(g(18, row, 0) or 0),
            def_bonus_pct=float(g(19, row, 0) or 0),
            artifact=str(g(20, row, "")),
            import_string=str(g(21, row, "")),
        )
        row += 1
    return heroes


# ---------------------------------------------------------------------------
# Quest Data
# ---------------------------------------------------------------------------

DIFFICULTIES = ["Easy", "Medium", "Hard", "Extreme"]


@dataclass
class QuestData:
    name: str
    lcog: str
    is_boss: str
    aoe_chance: float
    hp: dict[str, float] = field(default_factory=dict)          # difficulty → value
    defense_cap: dict[str, float] = field(default_factory=dict)
    attack: dict[str, float] = field(default_factory=dict)
    aoe_damage: dict[str, float] = field(default_factory=dict)
    barrier_hp: dict[str, float] = field(default_factory=dict)
    barrier: list[str] = field(default_factory=list)            # up to 3 element types


def load_quest_data(tsv_dir: Path = TSV_DIR) -> dict[str, QuestData]:
    grid = load_tsv_as_grid(tsv_dir / "Quest Data.tsv")

    def g(col: int, row: int, default=""):
        return grid.get((col, row), default)

    quests: dict[str, QuestData] = {}
    # col layout (0-based): A=0 show, B=1 zone, C=2 lcog, D=3 boss, E=4 aoe_chance
    # F-I (5-8) HP Easy/Med/Hard/Extreme
    # J-M (9-12) DefCap
    # N-Q (13-16) Attack
    # R-U (17-20) AoE Damage
    # V-Y (21-24) Barrier HP
    # Z-AB (25-27) Barrier 1/2/3
    row = 2  # data starts row 3 (0-based row 2), headers at row 1
    while True:
        zone = g(1, row, None)
        if zone is None:
            break
        zone = str(zone).strip()
        if zone:
            q = QuestData(
                name=zone,
                lcog=str(g(2, row, "")),
                is_boss=str(g(3, row, "")),
                aoe_chance=float(g(4, row, 0) or 0),
                hp={d: float(g(5 + i, row, 0) or 0) for i, d in enumerate(DIFFICULTIES)},
                defense_cap={d: float(g(9 + i, row, 0) or 0) for i, d in enumerate(DIFFICULTIES)},
                attack={d: float(g(13 + i, row, 0) or 0) for i, d in enumerate(DIFFICULTIES)},
                aoe_damage={d: float(g(17 + i, row, 0) or 0) for i, d in enumerate(DIFFICULTIES)},
                barrier_hp={d: float(g(21 + i, row, 0) or 0) for i, d in enumerate(DIFFICULTIES)},
                barrier=[str(g(25 + i, row, "")) for i in range(3)],
            )
            quests[zone] = q
        row += 1
        if row > 200:
            break
    return quests

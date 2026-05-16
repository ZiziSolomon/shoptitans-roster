"""
Validate Python MC results against the Google Sheet Quest Sim.

Current sheet config (matches premade Hero 1 + Hero 2 vs LCoG Diff 11 Hard):
  Quest Zone = Lost City of Gold Diff 11, Difficulty = Hard
  Hero 1: Blue/Spellcaster T4  HP=1351 ATK=149846 DEF=5795 Threat=10 Crit=0%  CritDmg=x2.0 Eva=25%  Armadillo=60
  Hero 2: Blue/Spellcaster T4  HP=1351 ATK=113092 DEF=5548 Threat=10 Crit=40% CritDmg=x6.5 Eva=0%   Lizard=21
  No champion, no aurasong, no booster.
  (Batch 3 test config: H1 swapped 4 enchants to Armadillo, H2 swapped 6 to Lizard —
  so all other stats moved too. Pulled fresh from Hero Data tab.)

To rerun: open sheet -> Quest Sim tab -> recalc -> `python -m sim.validate_vs_sheet`.
"""

from __future__ import annotations
import csv
import io
import urllib.request
from sim.hero import Hero
from sim.data import load_quest_data
from sim.quest import quest_from_data
from sim.combat import run_mc

SHEET_ID = "1-SJ6j4U9NtI0aNPxqG830PA5XEbI2GAPhoxYhdLIjH8"
SHEET_TAB = "Quest Sim"
N_TRIALS = 100_000
SEED = 42
TOL = 1.0  # percentage-point tolerance for comparisons

PARTY = [
    Hero("Hero 1", 1351, 149846, 5795, 10,  0.0, 2.0, 25.0, "Fire", armadillo=60.0),
    Hero("Hero 2", 1351, 113092, 5548, 10, 40.0, 6.5,  0.0, "Fire", lizard=21.0),
]
QUEST_NAME = "Lost City of Gold Diff 11"
QUEST_DIFF = "Hard"


def fetch_sheet_csv() -> list[list[str]]:
    url = (
        f"https://docs.google.com/spreadsheets/d/{SHEET_ID}"
        f"/gviz/tq?tqx=out:csv&sheet={SHEET_TAB.replace(' ', '+')}"
    )
    with urllib.request.urlopen(url, timeout=15) as resp:
        text = resp.read().decode("utf-8")
    return list(csv.reader(io.StringIO(text)))


def parse_sheet_mc(rows: list[list[str]]) -> dict:
    """
    Extract MC values from the Quest Sim tab.
    Looks for the 'Quest Success Rate [%]' row and reads from there.
    Returns dict with keys: success_rate, survival_rates (list), avg_hp (list).
    """
    mc: dict = {}
    for i, row in enumerate(rows):
        if not row:
            continue
        label = row[0].strip()
        if label == "Quest Success Rate [%]" and i + 1 < len(rows):
            # Header row; values are on the next row: [success%, min_rnd, avg_rnd, max_rnd, ...]
            vals = rows[i + 1]
            mc["success_rate"] = float(vals[0]) if vals and vals[0] else None
            mc["min_rounds"] = float(vals[1]) if len(vals) > 1 and vals[1] else None
            mc["avg_rounds"] = float(vals[2]) if len(vals) > 2 and vals[2] else None
            mc["max_rounds"] = float(vals[3]) if len(vals) > 3 and vals[3] else None
        elif label == "Survival Rate [%]":
            mc["survival_rates"] = [float(v) for v in row[1:6] if v.strip()]
        elif label.startswith("Average HP Remaining"):
            mc["avg_hp"] = [float(v) for v in row[1:6] if v.strip()]
    return mc


def compare(label: str, py_val: float, sheet_val: float | None, tol: float = TOL) -> bool:
    if sheet_val is None:
        print(f"  {label}: Python={py_val:.2f}%  Sheet=N/A (not found)")
        return True
    diff = abs(py_val - sheet_val)
    ok = diff <= tol
    status = "OK" if ok else "FAIL"
    print(f"  {label}: Python={py_val:.2f}%  Sheet={sheet_val:.2f}%  diff={diff:.2f}pp  [{status}]")
    return ok


def main() -> None:
    quests_db = load_quest_data()
    q = quest_from_data(quests_db[QUEST_NAME], QUEST_DIFF)

    print(f"Running Python MC: {q.name} [{q.difficulty}], {N_TRIALS:,} trials, seed={SEED}")
    mc, _ = run_mc(PARTY, q, n_trials=N_TRIALS, seed=SEED)
    print(f"  Success rate: {mc.success_rate:.2f}%  avg rounds: {mc.avg_rounds:.2f}")
    for h, r in zip(PARTY, mc.heroes):
        print(f"  {h.name}: survival={r.survival_rate:.1f}%  avg_hp={r.avg_hp_remaining:.1f}")

    print(f"\nFetching sheet: {SHEET_TAB!r} ...")
    try:
        rows = fetch_sheet_csv()
    except Exception as e:
        print(f"  Failed to fetch sheet: {e}")
        return

    sheet = parse_sheet_mc(rows)
    if not sheet:
        print("  Could not parse MC section from sheet — check sheet is configured correctly.")
        return

    print(f"\nComparison (tolerance ±{TOL}pp):")
    all_ok = True
    all_ok &= compare("Success rate", mc.success_rate, sheet.get("success_rate"))
    if "survival_rates" in sheet:
        for i, (h, r) in enumerate(zip(PARTY, mc.heroes)):
            sv = sheet["survival_rates"][i] if i < len(sheet["survival_rates"]) else None
            all_ok &= compare(f"{h.name} survival", r.survival_rate, sv)

    print(f"\nResult: {'PASS' if all_ok else 'FAIL'}")


if __name__ == "__main__":
    main()

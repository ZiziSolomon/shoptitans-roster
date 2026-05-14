"""
Validate Python MC results against the Google Sheet Quest Sim.

Setup:
  1. Open the sheet and configure:
       Quest Zone = Mushgoon Graverobber, Difficulty = Medium
       Hero 1: Olga    HP=194  ATK=7691  DEF=1679 Threat=40  Crit=5%  CritDmg=x2.0  Eva=0%
       Hero 2: Vena    HP=248  ATK=474   DEF=370  Threat=90  Crit=5%  CritDmg=x3.0  Eva=25%
       Hero 3: Corae   HP=254  ATK=2295  DEF=1898 Threat=40  Crit=60% CritDmg=x3.0  Eva=30%
       Hero 4: Sabrina HP=188  ATK=3277  DEF=1506 Threat=60  Crit=20% CritDmg=x2.0  Eva=60%
  2. Force a recalculation so the MC rows refresh.
  3. Run: python -m sim.validate_vs_sheet

Expected Python MC results (100k trials, seed=42):
  Success rate ~64.3%, avg rounds ~9.4
  Survival: Olga ~41%, Vena ~19%, Corae ~55%, Sabrina ~50%
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
TOL = 3.0  # percentage-point tolerance for comparisons

PARTY = [
    Hero("Olga",    194, 7691, 1679,  40,  5.0, 2.0,  0.0, "Fire"),
    Hero("Vena",    248,  474,  370,  90,  5.0, 3.0, 25.0, "Water"),
    Hero("Corae",   254, 2295, 1898,  40, 60.0, 3.0, 30.0, "Fire"),
    Hero("Sabrina", 188, 3277, 1506,  60, 20.0, 2.0, 60.0, "Wind"),
]


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
        if label == "Quest Success Rate [%]":
            mc["success_rate"] = float(row[1]) if row[1] else None
        elif label == "Survival Rate [%]":
            mc["survival_rates"] = [float(v) for v in row[1:5] if v.strip()]
        elif label == "Average HP Remaining ":
            mc["avg_hp"] = [float(v) for v in row[1:5] if v.strip()]
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
    q = quest_from_data(quests_db["Mushgoon Graverobber"], "Medium")

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

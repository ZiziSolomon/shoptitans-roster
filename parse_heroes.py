"""
Parse hero data from a TitansDB heroes page HTML file.

The page embeds all hero data in data-hero-string attributes on article.hero-card
elements. Each value is pipe-separated in this order:

  0   promoted (Yes/No)
  1   archetype colour ("Red Type" / "Green Type" / "Blue Type")
  2   class name
  3-8 gear slot types (weapon, armour, slot3..6) — empty string if not equipped
  9-14  equipped item names with tier, e.g. "Dragonwood Bow (ATK/DEF) - T10"
  15-20 item qualities (Normal / Superior / Flawless / Epic / Legendary)
  21-26 enchant levels, e.g. "15 / Tier 9" — empty if unenchanted
  27-32 spirits on each gear slot
  33-36 skills (up to 4 slots; empty string if unused)
  37    hero level
  38-40 unknown counters (always 0 in observed data)
  41-46 elements of each gear slot
"""

import json
import sys
from pathlib import Path

from bs4 import BeautifulSoup

SLOT_NAMES = ["weapon", "armour", "slot3", "slot4", "slot5", "slot6"]
SKILL_SLOTS = 4

ARCHETYPE_MAP = {
    "Red Type": "fighter",
    "Green Type": "rogue",
    "Blue Type": "spellcaster",
}


def parse_hero_string(name: str, data_type: str, data_element: str, raw: str) -> dict:
    fields = raw.split("|")

    def get(i):
        return fields[i].strip() if i < len(fields) else ""

    gear = []
    for i in range(6):
        slot_type = get(3 + i)
        item = get(9 + i)
        quality = get(15 + i)
        enchant = get(21 + i)
        spirit = get(27 + i)
        element = get(41 + i)
        gear.append({
            "slot": SLOT_NAMES[i],
            "slot_type": slot_type or None,
            "item": item or None,
            "quality": quality or None,
            "enchant": enchant or None,
            "spirit": spirit or None,
            "element": element or None,
        })

    skills = [get(33 + i) for i in range(SKILL_SLOTS)]
    skills = [s for s in skills if s]

    return {
        "name": name,
        "class": get(2),
        "archetype": ARCHETYPE_MAP.get(get(1), get(1)),
        "element": data_element,
        "level": int(get(37)) if get(37).isdigit() else None,
        "promoted": get(0) == "Yes",
        "skills": skills,
        "gear": gear,
    }


def parse_heroes_txt(txt_path: Path) -> list[dict]:
    heroes = []
    for line in txt_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        fields = line.split("|")
        archetype_raw = fields[1].strip() if len(fields) > 1 else ""
        # derive element from first non-empty gear element field (indices 41-46)
        element = next((fields[i].strip().lower() for i in range(41, 47) if i < len(fields) and fields[i].strip()), "")
        hero = parse_hero_string(
            name="",
            data_type=ARCHETYPE_MAP.get(archetype_raw, archetype_raw).lower(),
            data_element=element,
            raw=line,
        )
        heroes.append(hero)
    return heroes


def print_heroes(heroes: list[dict]) -> None:
    for h in heroes:
        skills_str = ", ".join(h["skills"]) if h["skills"] else "(none)"
        print(f"  {h['class']:14} lv{h['level']:>3}  {h['element']:6}  {skills_str}")


def main():
    data_dir = Path(__file__).parent / "data"

    for txt_file in sorted(data_dir.glob("*_HeroString_*.txt")):
        player = txt_file.name.split("_")[0]
        out_file = data_dir / f"{player}_heroes.json"
        heroes = parse_heroes_txt(txt_file)
        out_file.write_text(json.dumps(heroes, indent=2), encoding="utf-8")
        print(f"Parsed {len(heroes)} heroes from {txt_file.name} -> {out_file.name}")
        print_heroes(heroes)


if __name__ == "__main__":
    main()

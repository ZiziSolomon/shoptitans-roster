"""Quest dataclass used by the combat sim."""

from __future__ import annotations
from dataclasses import dataclass, field
from sim.data import QuestData, DIFFICULTIES


@dataclass
class Quest:
    name: str
    difficulty: str
    hp: float
    defense_cap: float
    attack: float           # quest attack (damage it deals)
    aoe_damage: float
    aoe_chance: float       # percent
    barrier_hp: float
    barrier: list[str]
    is_boss: bool


def quest_from_data(qd: QuestData, difficulty: str) -> Quest:
    if difficulty not in DIFFICULTIES:
        raise ValueError(f"difficulty must be one of {DIFFICULTIES}, got {difficulty!r}")
    return Quest(
        name=qd.name,
        difficulty=difficulty,
        hp=qd.hp[difficulty],
        defense_cap=qd.defense_cap[difficulty],
        attack=qd.attack[difficulty],
        aoe_damage=qd.aoe_damage[difficulty],
        aoe_chance=qd.aoe_chance,
        barrier_hp=qd.barrier_hp[difficulty],
        barrier=[b for b in qd.barrier if b],
        is_boss=qd.is_boss.strip().lower() == "yes",
    )

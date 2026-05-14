"""Hero dataclass used by the combat sim."""

from __future__ import annotations
from dataclasses import dataclass, field
from sim.data import HeroData


@dataclass
class Hero:
    name: str
    hp: float
    atk: float
    defense: float
    threat: float
    crit_chance: float      # percent, e.g. 20.0
    crit_multiplier: float  # e.g. 3.0
    evasion: float          # percent
    element_type: str
    armadillo: float = 0.0  # dodge chance percent
    lizard: float = 0.0     # HP regen per round
    shark: float = 0.0      # ATK bonus percent
    dinosaur: float = 0.0   # ATK bonus percent
    mundra: float = 0.0
    dmg_bonus_pct: float = 0.0
    def_bonus_pct: float = 0.0


def hero_from_data(hd: HeroData) -> Hero:
    return Hero(
        name=hd.name,
        hp=hd.hp,
        atk=hd.atk,
        defense=hd.defense,
        threat=hd.threat,
        crit_chance=hd.crit_chance,
        crit_multiplier=hd.crit_multiplier,
        evasion=hd.evasion,
        element_type=hd.element_type,
        armadillo=hd.armadillo,
        lizard=hd.lizard,
        shark=hd.shark,
        dinosaur=hd.dinosaur,
        mundra=hd.mundra,
        dmg_bonus_pct=hd.dmg_bonus_pct,
        def_bonus_pct=hd.def_bonus_pct,
    )

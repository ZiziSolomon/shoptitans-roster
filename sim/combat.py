"""Combat simulation — simple deterministic model and Monte Carlo."""

from __future__ import annotations
import math
import random
from dataclasses import dataclass, field
from sim.hero import Hero
from sim.quest import Quest


@dataclass
class HeroSimResult:
    name: str
    threat_share: float
    hits_taken: int
    damage_per_hit: float
    total_damage_taken: float
    survives: bool
    hp_remaining: float


@dataclass
class SimpleResult:
    quest: str
    difficulty: str
    total_atk: int
    rounds: int
    heroes: list[HeroSimResult]

    @property
    def all_survive(self) -> bool:
        return all(h.survives for h in self.heroes)


def _damage_per_hit(hero_def: float, defense_cap: float, quest_atk: float) -> float:
    """
    Piecewise linear interpolation of incoming damage based on hero DEF vs quest defense cap.
    Matches the Quest Sim sheet formula (G16 etc.).
    """
    cap = defense_cap
    atk = quest_atk
    d = hero_def
    if cap == 0:
        return atk
    if d <= cap / 6:
        t = d / (cap / 6)
        return 1.5 * atk + t * (0.5 * atk - 1.5 * atk)
    elif d <= cap / 3:
        t = (d - cap / 6) / (cap / 3 - cap / 6)
        return 0.5 * atk + t * (0.3 * atk - 0.5 * atk)
    else:
        t = min((d - cap / 3) / (cap - cap / 3), 1.0)
        return 0.3 * atk + t * (0.25 * atk - 0.3 * atk)


def run_simple(party: list[Hero], quest: Quest) -> SimpleResult:
    """
    Deterministic model matching the Quest Sim 'Simple Analysis' section.
    No crits, no evasion, no AoE.
    """
    total_atk = sum(h.atk for h in party)
    rounds = math.ceil(quest.hp / total_atk) if total_atk > 0 else 999
    total_threat = sum(h.threat for h in party)

    results = []
    for h in party:
        threat_share = (h.threat / total_threat) if total_threat > 0 else 1 / len(party)
        hits = math.ceil(threat_share * rounds)
        dph = round(_damage_per_hit(h.defense, quest.defense_cap, quest.attack))
        total_dmg = hits * dph
        survives = total_dmg < h.hp
        results.append(HeroSimResult(
            name=h.name,
            threat_share=threat_share,
            hits_taken=hits,
            damage_per_hit=dph,
            total_damage_taken=total_dmg,
            survives=survives,
            hp_remaining=h.hp - total_dmg,
        ))

    return SimpleResult(
        quest=quest.name,
        difficulty=quest.difficulty,
        total_atk=int(total_atk),
        rounds=rounds,
        heroes=results,
    )


# ---------------------------------------------------------------------------
# Monte Carlo
# ---------------------------------------------------------------------------

@dataclass
class MCHeroResult:
    name: str
    survival_rate: float
    avg_hp_remaining: float
    max_hp_remaining: float
    avg_dmg_to_quest: float
    max_dmg_to_quest: float
    min_dmg_to_quest: float


@dataclass
class MCResult:
    quest: str
    difficulty: str
    n_trials: int
    success_rate: float
    min_rounds: int
    avg_rounds: float
    max_rounds: int
    round_limit_hit_rate: float
    round_counts: dict[int, int]  # round_number -> count of trials ending in that round
    heroes: list[MCHeroResult]

    @property
    def round_limit_hit(self) -> bool:
        return self.round_limit_hit_rate > 0


ROUND_LIMIT = 40


def _pick_target(alive: list[tuple[int, Hero]], rng: random.Random) -> int:
    """Pick one hero index via threat-weighted random selection."""
    total = sum(h.threat for _, h in alive)
    r = rng.random() * total
    cumulative = 0.0
    for i, h in alive:
        cumulative += h.threat
        if r < cumulative:
            return i
    return alive[-1][0]


def run_mc(
    party: list[Hero],
    quest: Quest,
    n_trials: int = 10_000,
    seed: int | None = None,
    debug: bool = False,
) -> tuple[MCResult, list[str]]:
    """
    Monte Carlo sim with crits, evasion, threat-weighted targeting, AoE, spirit bonuses.
    Returns (MCResult, trace_lines) where trace_lines is non-empty only when debug=True
    (covers the first trial only).
    """
    rng = random.Random(seed)

    successes = 0
    round_limit_hits = 0
    all_rounds: list[int] = []

    hero_survived: list[int] = [0] * len(party)
    hero_hp_remaining: list[list[float]] = [[] for _ in party]
    hero_dmg_to_quest: list[list[float]] = [[] for _ in party]

    trace: list[str] = []

    for trial in range(n_trials):
        is_debug_trial = debug and trial == 0
        t: list[str] = []

        hp_remaining = [h.hp for h in party]
        quest_hp_left = quest.hp

        effective_atk = [
            h.atk * (1 + (h.shark + h.dinosaur) / 100.0)
            for h in party
        ]
        trial_dmg_to_quest = [0.0] * len(party)

        rounds_taken = 0

        for rnd in range(1, ROUND_LIMIT + 1):
            if quest_hp_left <= 0:
                break

            if is_debug_trial:
                t.append(f"\n--- Round {rnd} --- (Quest HP: {quest_hp_left:,.0f})")

            # Heroes attack
            for i, h in enumerate(party):
                if hp_remaining[i] <= 0:
                    continue
                base_atk = effective_atk[i]
                critted = rng.random() * 100 < h.crit_chance
                actual_atk = base_atk * h.crit_multiplier if critted else base_atk
                quest_hp_left -= actual_atk
                trial_dmg_to_quest[i] += actual_atk
                if is_debug_trial:
                    crit_tag = f" CRIT x{h.crit_multiplier}" if critted else ""
                    t.append(f"  {h.name} attacks for {actual_atk:,.0f}{crit_tag}")

            rounds_taken = rnd
            if is_debug_trial:
                t.append(f"  Quest HP after attacks: {max(0, quest_hp_left):,.0f}")

            if quest_hp_left <= 0:
                if is_debug_trial:
                    t.append("  Quest defeated — no counter-attack this round.")
                break

            # Quest attacks one hero (threat-weighted)
            alive = [(i, party[i]) for i in range(len(party)) if hp_remaining[i] > 0]
            if not alive:
                break
            target_i = _pick_target(alive, rng)
            h = party[target_i]

            dodged = (h.armadillo > 0 and rng.random() * 100 < h.armadillo)
            evaded = (not dodged and h.evasion > 0 and rng.random() * 100 < h.evasion)

            if dodged or evaded:
                dodge_tag = "DODGE (armadillo)" if dodged else "EVADE"
                if is_debug_trial:
                    t.append(f"  Quest targets {h.name} — {dodge_tag}")
            else:
                dph = _damage_per_hit(h.defense, quest.defense_cap, quest.attack)
                hp_remaining[target_i] -= dph
                if is_debug_trial:
                    t.append(
                        f"  Quest targets {h.name} for {dph:.0f} dmg "
                        f"-> HP: {hp_remaining[target_i] + dph:.0f} -> {hp_remaining[target_i]:.0f}"
                    )

            # Lizard regen for targeted hero (happens after being hit)
            if h.lizard > 0:
                hp_remaining[target_i] = min(h.hp, hp_remaining[target_i] + h.lizard)

            # AoE hits all alive heroes
            if quest.aoe_chance > 0 and rng.random() * 100 < quest.aoe_chance:
                if is_debug_trial:
                    t.append(f"  AoE triggered! ({quest.aoe_damage:.0f} dmg to all)")
                for i, h in enumerate(party):
                    if hp_remaining[i] > 0:
                        hp_remaining[i] -= quest.aoe_damage
                        if is_debug_trial:
                            t.append(f"    {h.name}: {hp_remaining[i] + quest.aoe_damage:.0f} -> {hp_remaining[i]:.0f}")
            elif is_debug_trial:
                t.append(f"  AoE: not triggered (chance {quest.aoe_chance}%)")

        else:
            round_limit_hits += 1
            if is_debug_trial:
                t.append(f"\n  *** Round limit ({ROUND_LIMIT}) hit ***")

        quest_survived = quest_hp_left <= 0
        if quest_survived:
            successes += 1
        all_rounds.append(rounds_taken)

        if is_debug_trial:
            t.append(f"\nTrial result: {'SUCCESS' if quest_survived else 'FAIL'} in {rounds_taken} round(s)")
            for i, h in enumerate(party):
                status = f"HP {hp_remaining[i]:.0f}/{h.hp:.0f}" if hp_remaining[i] > 0 else "DEAD"
                t.append(f"  {h.name}: {status}")
            trace = t

        for i in range(len(party)):
            if hp_remaining[i] > 0:
                hero_survived[i] += 1
            hero_hp_remaining[i].append(max(0.0, hp_remaining[i]))
            hero_dmg_to_quest[i].append(trial_dmg_to_quest[i])

    hero_results = []
    for i, h in enumerate(party):
        rems = hero_hp_remaining[i]
        dmgs = hero_dmg_to_quest[i]
        hero_results.append(MCHeroResult(
            name=h.name,
            survival_rate=hero_survived[i] / n_trials * 100,
            avg_hp_remaining=sum(rems) / n_trials,
            max_hp_remaining=max(rems),
            avg_dmg_to_quest=sum(dmgs) / n_trials,
            max_dmg_to_quest=max(dmgs),
            min_dmg_to_quest=min(dmgs),
        ))

    round_counts: dict[int, int] = {}
    for r in all_rounds:
        round_counts[r] = round_counts.get(r, 0) + 1

    result = MCResult(
        quest=quest.name,
        difficulty=quest.difficulty,
        n_trials=n_trials,
        success_rate=successes / n_trials * 100,
        min_rounds=min(all_rounds) if all_rounds else 0,
        avg_rounds=sum(all_rounds) / n_trials if all_rounds else 0,
        max_rounds=max(all_rounds) if all_rounds else 0,
        round_limit_hit_rate=round_limit_hits / n_trials * 100,
        round_counts=round_counts,
        heroes=hero_results,
    )
    return result, trace

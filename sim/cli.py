"""CLI entry point for the quest sim."""

from __future__ import annotations
import argparse
import sys
from sim.data import load_hero_data, load_quest_data
from sim.hero import hero_from_data
from sim.quest import quest_from_data, DIFFICULTIES
from sim.combat import run_simple, run_mc


def print_simple(result) -> None:
    print(f"\n=== {result.quest} [{result.difficulty}] — Simple Analysis ===")
    print(f"Total ATK: {result.total_atk:,}  |  Rounds: {result.rounds}")
    print(f"{'Hero':<20} {'Threat%':>8} {'DpH':>8} {'Hits':>6} {'TotalDmg':>10} {'HP':>8} {'Survives':>9}")
    for h in result.heroes:
        print(
            f"{h.name:<20} {h.threat_share*100:>7.1f}% {h.damage_per_hit:>8.0f} "
            f"{h.hits_taken:>6} {h.total_damage_taken:>10.0f} {h.hp_remaining:>8.0f} "
            f"{'YES' if h.survives else 'NO':>9}"
        )
    print(f"\nAll survive: {'YES' if result.all_survive else 'NO'}")


def print_mc(result) -> None:
    print(f"\n=== {result.quest} [{result.difficulty}] — Monte Carlo ({result.n_trials:,} trials) ===")
    print(f"Success rate: {result.success_rate:.1f}%  |  Rounds: min={result.min_rounds} avg={result.avg_rounds:.2f} max={result.max_rounds}")
    if result.round_limit_hit_rate > 0:
        print(f"Round limit hit: {result.round_limit_hit_rate:.1f}%")
    print(f"\n{'Hero':<20} {'Survival':>9} {'AvgHP':>9} {'MaxHP':>9} {'AvgDmg':>12} {'MinDmg':>12}")
    for h in result.heroes:
        print(
            f"{h.name:<20} {h.survival_rate:>8.1f}% {h.avg_hp_remaining:>9.1f} {h.max_hp_remaining:>9.1f}"
            f" {h.avg_dmg_to_quest:>12,.0f} {h.min_dmg_to_quest:>12,.0f}"
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="Shop Titans quest simulator")
    parser.add_argument("--quest", "-q", default="Sun God Tomb", help="Quest zone name (partial match ok)")
    parser.add_argument("--difficulty", "-d", default="Easy", choices=DIFFICULTIES)
    parser.add_argument("--heroes", "-H", nargs="+", default=None, help="Hero names (first is champion)")
    parser.add_argument("--mode", "-m", default="simple", choices=["simple", "mc", "both"])
    parser.add_argument("--trials", "-t", type=int, default=10_000)
    parser.add_argument("--debug", action="store_true", help="Print round-by-round trace for first trial")
    parser.add_argument("--list-quests", action="store_true")
    parser.add_argument("--list-heroes", action="store_true")
    args = parser.parse_args()

    heroes_db = load_hero_data()
    quests_db = load_quest_data()

    if args.list_quests:
        for q in quests_db:
            print(q)
        return

    if args.list_heroes:
        for h in heroes_db:
            print(h)
        return

    # Resolve quest — exact match first, then case-insensitive substring
    quest_name = args.quest.strip()
    if quest_name in quests_db:
        matches = [quest_name]
    else:
        matches = [q for q in quests_db if quest_name.lower() in q.lower()]
    if not matches:
        print(f"No quest matching {quest_name!r}. Use --list-quests to see available quests.")
        sys.exit(1)
    if len(matches) > 1:
        print(f"Ambiguous quest name {quest_name!r}. Matches: {matches}")
        sys.exit(1)
    quest = quest_from_data(quests_db[matches[0]], args.difficulty)

    # Resolve heroes
    if args.heroes is None:
        # Default: pick first hero as champion, then fill with more from the DB
        hero_list = list(heroes_db.values())[:4]
        print(f"No heroes specified; using first {len(hero_list)} from Hero Data.")
    else:
        hero_list = []
        for name in args.heroes:
            # exact match first, then substring
            if name in heroes_db:
                name_matches = [name]
            else:
                name_matches = [h for h in heroes_db if name.lower() in h.lower()]
            if not name_matches:
                print(f"Hero not found: {name!r}. Use --list-heroes.")
                sys.exit(1)
            if len(name_matches) > 1:
                print(f"Ambiguous hero name {name!r}: {name_matches}")
                sys.exit(1)
            hero_list.append(heroes_db[name_matches[0]])

    party = [hero_from_data(h) for h in hero_list]

    if args.mode in ("simple", "both"):
        result = run_simple(party, quest)
        print_simple(result)

    if args.mode in ("mc", "both"):
        mc, trace = run_mc(party, quest, n_trials=args.trials, debug=args.debug)
        if trace:
            print("\n=== Debug trace (trial 1) ===")
            print("\n".join(trace))
        print_mc(mc)


if __name__ == "__main__":
    main()

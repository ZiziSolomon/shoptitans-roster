# Python MC sim vs sheet/scripts/simV2.txt — Diff

Comparison of `sim/combat.py` (Python `run_mc`) against the Google Apps Script
`myFunction_V2()` in `sheet/scripts/simV2.txt`. Ordered by likely impact on MC
accuracy. Line refs are to simV2.txt unless noted.

## Critical structural bugs

1. **Round order reversed.** Sheet: mob attacks first (815–1006), then heroes.
   Python (combat.py:186–244): heroes first, then mob. Python winning trials
   lose one full mob attack round → inflates survival.
2. **AoE vs single-target is exclusive in sheet, additive in Python.**
   Sheet 821 `if` / 872 `else` — one or the other. Python (combat.py:207–244)
   does both each round.
3. **Round limit:** sheet=499, Python=40 (combat.py:124).
4. **Hero attack order shuffled each trial** (sheet 735–740, Fisher-Yates over
   indices 1..4 — slot 0 fixed). Python iterates fixed 0..N. Order matters
   for Shark threshold (<50% mob HP), Dark Knight execute (<10%), etc.

## Missing combat mechanics

5. **Mob crits** — 10% base (line 91), crit dmg `max(dmg_taken, Mob_Damage)*1.5` (896).
6. **Mob evasion** — default -1; Agile=0.4, Legendary=0.1 minibosses (1012).
7. **Hero evasion cap** — 75% (Pathfinder 78%) (line 241–243).
8. **Surviving Fatal Blow (armadillo)** — sheet: one-shot save at 1 HP
   (678, 833, 901). Python misinterprets as per-hit dodge chance.
9. **Lord save** — Lord absorbs first fatal blow on any teammate (834+).
10. **Cleric/Bishop end-of-round heal** (1124–1131); Lizard EoR regen for
    ALL alive heroes (sheet 1122). Python applies lizard only to targeted hero.
11. **Class innates** — none in Python:
    - Berserker/Jarl HP-threshold stages (962–975)
    - Conquistador consecutive-crit bonus (1022)
    - Samurai/Daimyo R1 guaranteed crit (995); Daimyo guaranteed evade
    - Ninja/Sensei evasion + crit bonus, lost on first hit
    - Dancer/Acrobat guaranteed crit after evade
    - Dark Knight/Death Knight execute <10% mob HP (1038–1041)
    - Pathfinder evasion cap +3%
    - Mercenary 1.25× all champion bonuses
12. **Champions** — all 12 (Argon, Ashley, Bjorn, Donovan, Hemma, Lilu, Malady,
    Polonia, Reinhold, Rudo, Sia, Yami). None implemented.
13. **Aurasong** — 14 aurasongs modify stats pre-fight. None implemented.
14. **Boosters** — Normal/Super/Mega add 20–80% ATK+DEF and crit (583–599).
15. **Mundra** — sheet zeros on non-boss (line 132). Python's Hero has the field
    but combat.py never reads it.
16. **Shark/Dinosaur activation** — Shark only when mob HP <50% (1043);
    Dinosaur only round 1 (1049). Python applies both as flat ATK bonus.
17. **Mob barrier** — element-typed HP shield; if unbroken, dmg × 0.2 (652–661, 1019).
18. **Extreme mode** — −20% hero evasion, crit bonus from negative evasion (180–182, 806).
19. **Hemma drain** — drains teammate HP for Hemma ATK (935–953).
20. **Fateweaver retry** — `success = 1 − (1−p)²` post-process (1181).

## Numerical / hygiene differences

21. **Damage rounding** — sheet rounds DPH/crit DPH to int (642–649); Python floats.
22. **Crit chance** — both `rng*100 < pct` equivalent. ✅
23. **Defense de/re-normalization** — sheet strips atk_mod/def_mod from raw stats
    then re-applies with Mundra mixed in (187–191).
24. **Trial count** — sheet 50k (cuts to 5k if slow); Python default 10k.

## Recommended fix order

1. Swap mob/hero order
2. Make AoE/single-target exclusive
3. Bump round limit to 499
4. Add Booster (Mega is the common one)

Validate after each cluster before tackling champions/innates/aurasongs.

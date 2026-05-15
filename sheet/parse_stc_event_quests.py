"""
Parse `data/STC Hub _ Event Quests.htm` into structured JSON.

Output schema (list of areas):
[
  {
    "area": "Lost City of Gold",
    "type": "lcog",           # or "tot"
    "boss": "Golem",
    "party_size": 5,
    "rewards": ["Pure Gold Bar", "Luxurious Key", ...],
    "difficulties": [
      {
        "tier": 1,
        "name": "Golem",
        "hp": 500, "atk": 8, "aoe": 5, "min_power": 0,
        "defense_caps": {"50": 100, "70": 200, "75": 600},
        "extras": {"Pure Gold Bar": "12 - 18", ...}
      }, ...
    ]
  }, ...
]

Usage:
    python sheet/parse_stc_event_quests.py              # → stdout
    python sheet/parse_stc_event_quests.py -o out.json  # → file
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

DEFAULT_INPUT = Path(__file__).parent.parent / "data" / "STC Hub _ Event Quests.htm"

# Recognised numeric stat titles. Anything else lands in "extras".
KNOWN_STATS = {
    "HP": "hp",
    "ATK": "atk",
    "AoE": "aoe",
    "Minimum Power": "min_power",
}


def _to_number(s: str):
    """'1,000' → 1000; '12 - 18' → '12 - 18' (left as string); '30%' → '30%'."""
    s = s.strip()
    bare = s.replace(",", "")
    if re.fullmatch(r"-?\d+", bare):
        return int(bare)
    if re.fullmatch(r"-?\d+\.\d+", bare):
        return float(bare)
    return s


def _split_top_level(html: str, marker: str) -> list[str]:
    """Split a string at each occurrence of `marker`. The first chunk (before any
    marker) is discarded; each remaining chunk begins right at `marker`."""
    parts = html.split(marker)
    return [marker + p for p in parts[1:]]


def parse_difficulty(block: str) -> dict:
    """Parse one `quest-difficulty` block."""
    diff: dict = {"extras": {}}

    # Tier number: <div class="quest-difficulty-banner-image-wrapper..."> ... <p>N</p>
    m = re.search(
        r'quest-difficulty-banner-image-wrapper[^>]*>.*?<p>(\d+)</p>',
        block, re.DOTALL,
    )
    if m:
        diff["tier"] = int(m.group(1))

    # Difficulty/boss name: prefer the <h3> right after the banner image wrapper.
    m = re.search(
        r'quest-difficulty-banner"\s+title="([^"]*)"',
        block,
    )
    if m:
        diff["name"] = m.group(1)
    m = re.search(
        r'quest-difficulty-banner.*?<h3[^>]*>([^<]+)</h3>',
        block, re.DOTALL,
    )
    if m:
        # h3 overrides banner title when present (more specific for LCoG)
        diff["name"] = m.group(1).strip()

    # Iterate each stat block. The closing-quote in `meta-stat"` is important —
    # it prevents the lookahead from matching the nested
    # `quest-difficulty-meta-stat-def-wrapper-stat-50` sub-wrappers inside Defense Caps.
    stat_re = re.compile(
        r'<div class="quest-difficulty-meta-stat"\s*(?:title="([^"]*)")?\s*>(.*?)'
        r'(?=<div class="quest-difficulty-meta-stat"|</div></div></div>|</div></div><div class="quest-difficulty")',
        re.DOTALL,
    )
    for m in stat_re.finditer(block):
        title = (m.group(1) or "").strip()
        body = m.group(2)
        if title == "Defense Caps":
            caps = {}
            for sm in re.finditer(
                r'quest-difficulty-meta-stat-def-wrapper-stat-(\d+)"\s*>'
                r'\s*<p[^>]*>\s*\d+%\s*</p>'
                r'\s*<p[^>]*>\s*([\d,]+)\s*</p>',
                body,
            ):
                caps[sm.group(1)] = int(sm.group(2).replace(",", ""))
            if caps:
                diff["defense_caps"] = caps
            continue

        # Generic value: the value <p> always has class `st-text-outline-shadow-p`.
        # (AoE has an extra label <p class="st-text-outline no-margin">AoE</p> first;
        # matching shadow-p specifically skips past it to the numeric value.)
        vm = re.search(
            r'<p class="st-text-outline-shadow-p[^"]*"[^>]*>\s*([^<]+?)\s*</p>',
            body,
        )
        if not vm:
            continue
        value = _to_number(vm.group(1))

        key = KNOWN_STATS.get(title)
        if key:
            diff[key] = value
        else:
            # title may be empty (e.g. LCoG key drop). Fall back to icon filename
            # to disambiguate, but keep value either way.
            label = title or _icon_label(body) or "unnamed"
            diff["extras"][label] = value

    if not diff["extras"]:
        diff.pop("extras")
    return diff


def _icon_label(body: str) -> str | None:
    """Look at the first <img src=...> in a stat block; derive a label from the filename."""
    m = re.search(r'<img\s+src="[^"]*?/([^/"]+)\.(?:png|svg|jpg)"', body)
    if m:
        return m.group(1)
    return None


def parse_area(chunk: str) -> dict:
    """Parse one quest area (from `quest-area-banner` up to the next one)."""
    area: dict = {}

    m = re.search(r'quest-area-banner"\s+title="([^"]+)"', chunk)
    if m:
        area["area"] = m.group(1)

    m = re.search(r'quest-banner-wrapper\s+quest-banner-(\w+)"', chunk)
    if m:
        area["type"] = m.group(1)

    m = re.search(r'quest-banner-mob[^"]*".*?<h2[^>]*>([^<]+)</h2>', chunk, re.DOTALL)
    if m:
        area["boss"] = m.group(1).strip()

    m = re.search(
        r'Party Size\s*</p>\s*<h3[^>]*>\s*(\d+)\s*</h3>',
        chunk, re.DOTALL,
    )
    if m:
        area["party_size"] = int(m.group(1))

    # Rewards: collect alt/title text from reward component imgs in the banner.
    banner_end = chunk.find("quest-license-wrapper")
    banner = chunk[: banner_end if banner_end != -1 else len(chunk)]
    rewards: list[str] = []
    for rm in re.finditer(
        r'quest-banner-meta-(?:lcog-rewards-component|tot-component)"\s+'
        r'src="[^"]*"\s+alt="([^"]*)"(?:\s+title="([^"]*)")?',
        banner,
    ):
        label = rm.group(2) or rm.group(1)
        if label and label not in rewards:
            rewards.append(label)
    if rewards:
        area["rewards"] = rewards

    # Difficulties: every <div class="quest-difficulty"> inside the wrapper.
    wrap_match = re.search(
        r'quest-difficulty-wrapper[^"]*".*',
        chunk, re.DOTALL,
    )
    if wrap_match:
        diff_blocks = _split_top_level(
            wrap_match.group(0),
            '<div class="quest-difficulty">',
        )
        area["difficulties"] = [parse_difficulty(b) for b in diff_blocks]

    return area


def parse(html: str) -> list[dict]:
    chunks = _split_top_level(html, 'class="quest-area-banner"')
    return [parse_area(c) for c in chunks]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("-i", "--input", type=Path, default=DEFAULT_INPUT)
    ap.add_argument("-o", "--output", type=Path, default=None,
                    help="Write JSON here; default stdout.")
    args = ap.parse_args(argv)

    html = args.input.read_text(encoding="utf-8", errors="replace")
    data = parse(html)

    out = json.dumps(data, indent=2, ensure_ascii=False)
    if args.output:
        args.output.write_text(out + "\n", encoding="utf-8")
        print(f"Wrote {len(data)} areas to {args.output}", file=sys.stderr)
    else:
        print(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())

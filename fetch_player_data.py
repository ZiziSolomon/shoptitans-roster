import requests
import json
import sys
from pathlib import Path

API_BASE = "https://www.titansdb.com/api"
KEYS_FILE = Path(__file__).parent / "API_keys.txt"
OUT_DIR = Path(__file__).parent / "data"


def load_keys(path):
    players = {}
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        username, api_key = line.split(":", 1)
        players[username.strip()] = api_key.strip()
    return players


def fetch(api_key, endpoint):
    url = f"{API_BASE}/{endpoint}"
    response = requests.get(url, headers={"X-API-Key": api_key}, timeout=30)
    response.raise_for_status()
    return response.json()


def main():
    OUT_DIR.mkdir(exist_ok=True)
    players = load_keys(KEYS_FILE)

    endpoints = ["my_player", "my_player_ticks"]

    for username, api_key in players.items():
        slug = username.replace('#', '_')
        for endpoint in endpoints:
            print(f"Fetching {endpoint} for {username}...")
            try:
                data = fetch(api_key, endpoint)
                out_file = OUT_DIR / f"{slug}_{endpoint}.json"
                out_file.write_text(json.dumps(data, indent=2))
                print(f"  Saved to {out_file}")
            except requests.HTTPError as e:
                print(f"  HTTP error {e.response.status_code}: {e.response.text}", file=sys.stderr)
            except Exception as e:
                print(f"  Error: {e}", file=sys.stderr)


if __name__ == "__main__":
    main()

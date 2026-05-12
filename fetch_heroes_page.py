import requests
from pathlib import Path

SESSION_ID = "e16e9afc521dd003a8e5ab26705b234c"
OUT_DIR = Path(__file__).parent / "data"


def main():
    OUT_DIR.mkdir(exist_ok=True)
    url = "https://www.titansdb.com/user/heroes"
    response = requests.get(
        url,
        cookies={"PHPSESSID": SESSION_ID},
        headers={"User-Agent": "Mozilla/5.0"},
        timeout=30,
    )
    response.raise_for_status()
    out_file = OUT_DIR / "heroes_page.html"
    out_file.write_text(response.text, encoding="utf-8")
    print(f"Saved {len(response.text):,} chars to {out_file}")


if __name__ == "__main__":
    main()

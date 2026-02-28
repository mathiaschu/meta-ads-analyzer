#!/usr/bin/env python3
"""
Sync data from Google Sheets.
Downloads two tabs:
  - 'Ventas x mes 2026' (gid=992221371) -> ventas_2026.csv
  - 'Resumen general'   (gid=0)         -> resumen_gsheet.csv
"""

import os
import sys
import time
import urllib.request
import urllib.error

SHEET_ID = "19uNOkJ39tTLP6jYQADAN8CFrr2g8ViIaylMOat51Ghk"
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CACHE_MAX_AGE = 3600

SHEETS = [
    {"gid": "992221371", "name": "Ventas x mes 2026",
     "output": os.path.join(SCRIPT_DIR, "ventas_2026.csv")},
    {"gid": "0", "name": "Resumen general",
     "output": os.path.join(SCRIPT_DIR, "resumen_gsheet.csv")},
]


def download_sheet(gid, name, output_file):
    url = (f"https://docs.google.com/spreadsheets/d/"
           f"{SHEET_ID}/export?format=csv&gid={gid}")
    print(f"  Descargando '{name}' (gid={gid})...")
    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (Dashboard Sync)"
        })
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = resp.read()
        with open(output_file, "wb") as f:
            f.write(data)
        lines = data.decode("utf-8").strip().split("\n")
        print(f"   OK {len(lines)} filas -> {os.path.basename(output_file)}")
        return True
    except Exception as e:
        print(f"   Error: {e}")
        return False


def is_cache_fresh(path):
    if not os.path.exists(path):
        return False
    return (time.time() - os.path.getmtime(path)) < CACHE_MAX_AGE


def main():
    force = "--force" in sys.argv
    ok = True
    for s in SHEETS:
        if not force and is_cache_fresh(s["output"]):
            age = (time.time() - os.path.getmtime(s["output"])) / 60
            print(f"  Cache fresco '{s['name']}' ({age:.0f} min)")
        else:
            if not download_sheet(s["gid"], s["name"], s["output"]):
                ok = False
    return ok


if __name__ == "__main__":
    sys.exit(0 if main() else 1)

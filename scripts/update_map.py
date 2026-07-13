#!/usr/bin/env python3
"""
Henter kundens Google My Maps som KML og genererer klesbokser_clean_stripped.geojson
med opprydda navn (fjerner kode-prefiks som "Punkt B127 ").

Bruk:
  python3 scripts/update_map.py            # laster ned fra Google My Maps
  python3 scripts/update_map.py fil.kml    # bruker lokal KML-fil i stedet
"""
import json
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

MID = "1sOpB5_jr1qcPFPvR6gBL418m0Fo"
KML_URL = f"https://www.google.com/maps/d/kml?mid={MID}&forcekml=1"
OUT = Path(__file__).resolve().parent.parent / "klesbokser_clean_stripped.geojson"
NS = "{http://www.opengis.net/kml/2.2}"

# Sikkerhetsnett: ikke overskriv fila hvis nedlastingen ser ødelagt/avkortet ut
MIN_FEATURES = 500

# Matcher kode-prefiks: "Punkt B127 ", "B15 ", "O01Linderud", "Punkt М159 " (kyrillisk М), "M143\t..."
PREFIX = re.compile(r"^\s*(?:punkt\s*)?[BSMOМ]\s?-?\d+\s*[.:\-–—\t ]*", re.IGNORECASE)


def clean_name(raw: str) -> str:
    name = " ".join((raw or "").split())  # normaliser whitespace/linjeskift
    cleaned = PREFIX.sub("", name).strip()
    return cleaned or name


def load_kml() -> bytes:
    if len(sys.argv) > 1:
        return Path(sys.argv[1]).read_bytes()
    req = urllib.request.Request(KML_URL, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()


def main() -> None:
    root = ET.fromstring(load_kml())
    features = []
    for pm in root.iter(f"{NS}Placemark"):
        coords = pm.find(f".//{NS}Point/{NS}coordinates")
        if coords is None or not (coords.text or "").strip():
            continue  # hopp over linjer/polygoner
        lng, lat = (float(v) for v in coords.text.strip().split(",")[:2])
        name_el = pm.find(f"{NS}name")
        features.append({
            "type": "Feature",
            "properties": {"name": clean_name(name_el.text if name_el is not None else "")},
            "geometry": {"type": "Point", "coordinates": [round(lng, 7), round(lat, 7)]},
        })

    if len(features) < MIN_FEATURES:
        sys.exit(f"AVBRUTT: bare {len(features)} punkt i KML (forventet minst {MIN_FEATURES}). "
                 "Sjekk at kartet fortsatt er delt med 'alle med lenken'.")

    OUT.write_text(
        json.dumps({"type": "FeatureCollection", "features": features},
                   ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Skrev {len(features)} punkt til {OUT.name}")


if __name__ == "__main__":
    main()

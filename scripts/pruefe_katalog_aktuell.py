#!/usr/bin/env python3
"""Meldet Katalogtexte, die nicht mehr zu ihrer deutschen Quelle passen.

Der Katalog (data/i18n/katalog-de.json) wird aus data/behandlungen.json und
data/beschreibungen.json erzeugt. Ändert jemand dort einen Text, veralten die
drei Übersetzungen still — sie behalten die alte Aussage. Bei medizinischen
Texten ist das heikel: eine entschärfte deutsche Fassung, die in den anderen
Sprachen noch stark formuliert steht, verspricht dort mehr als gewollt.

Aufruf: python3 scripts/pruefe_katalog_aktuell.py [--schreiben]
  ohne Schalter   nur melden
  --schreiben     katalog-de.json auf den Stand der Quellen bringen und
                  auflisten, welche Schlüssel in en/tr/ar nachgezogen werden müssen
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
I18N = DATA / "i18n"

UM = str.maketrans({"ä": "ae", "ö": "oe", "ü": "ue", "ß": "ss"})


def slugify(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower().translate(UM)).strip("-")


def aus_quellen(bestand):
    """Baut die Katalogschlüssel so, wie build_site.py sie erwartet.

    Namen und Beschreibungen stammen aus behandlungen.json und
    beschreibungen.json. Teaser und Einleitung der Kategorien haben keine
    solche Quelle mehr — sie werden in katalog-de.json selbst gepflegt und
    hier unverändert aus dem Bestand übernommen, damit ein Abgleich sie
    nicht löscht.
    """
    katalog = json.loads((DATA / "behandlungen.json").read_text())
    beschr = json.loads((DATA / "beschreibungen.json").read_text())

    out = {}
    for k in katalog["kategorien"]:
        kid = k["id"]
        out[f"kat.{kid}.name"] = k["name_de"]
        for feld in ("teaser", "intro"):
            schluessel = f"kat.{kid}.{feld}"
            if schluessel in bestand:
                out[schluessel] = bestand[schluessel]
        for g in k["gruppen"]:
            out[f"gruppe.{kid}.{slugify(g['name_de'])}.name"] = g["name_de"]
            for b in g["behandlungen"]:
                out[f"beh.{b['slug']}.name"] = b["name_de"]
                if b["slug"] in beschr:
                    out[f"beh.{b['slug']}.desc"] = beschr[b["slug"]]
    return out


def main():
    schreiben = "--schreiben" in sys.argv
    ist_pfad = I18N / "katalog-de.json"
    ist = json.loads(ist_pfad.read_text())
    soll = aus_quellen(ist)

    geaendert = [k for k in soll if k in ist and soll[k] != ist[k]]
    neu = [k for k in soll if k not in ist]
    entfallen = [k for k in ist if k not in soll]

    print(f"Quellen: {len(soll)} Schlüssel, katalog-de.json: {len(ist)}")
    if not (geaendert or neu or entfallen):
        print("Der Katalog ist auf dem Stand der Quellen.")
        return 0

    if geaendert:
        print(f"\nGEÄNDERT ({len(geaendert)}) — in en/tr/ar steht noch die alte Aussage:")
        for k in geaendert[:15]:
            print(f"  {k}")
            print(f"    alt: {ist[k][:95]}")
            print(f"    neu: {soll[k][:95]}")
        if len(geaendert) > 15:
            print(f"  … und {len(geaendert) - 15} weitere")
    if neu:
        print(f"\nNEU ({len(neu)}): {neu[:10]}")
    if entfallen:
        print(f"\nENTFALLEN ({len(entfallen)}): {entfallen[:10]}")

    if schreiben:
        ist_pfad.write_text(json.dumps(soll, ensure_ascii=False, indent=2) + "\n")
        print(f"\nkatalog-de.json auf den Stand der Quellen gebracht.")
        nachzuziehen = sorted(set(geaendert) | set(neu))
        (I18N / "nachzuziehen.txt").write_text("\n".join(nachzuziehen) + "\n")
        print(f"{len(nachzuziehen)} Schlüssel müssen in en/tr/ar neu übersetzt werden.")
        print("Die Liste steht in data/i18n/nachzuziehen.txt")
    else:
        print("\nMit --schreiben wird katalog-de.json angeglichen und die")
        print("Nachzieh-Liste für die Übersetzungen geschrieben.")
    return 1


if __name__ == "__main__":
    sys.exit(main())

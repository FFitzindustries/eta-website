#!/usr/bin/env python3
"""Zieht alle übersetzungsbedürftigen Texte aus den Redaktionsdaten.

Die Inhalte der Website stehen seit dem Ausbau in sieben JSON-Dateien unter
data/. Damit die Sprachauswahl sie erfasst, braucht jeder Text einen stabilen
Schlüssel. Dieses Skript erzeugt daraus data/i18n/daten-de.json.

Schlüsselschema:  daten.<datei>.<pfad>
  daten.behandlungsdaten.stirn-botox.dauer_eingriff
  daten.risiken-gruppen.haut-beauty/botox.risiken.0
  daten.recht.agb.abschnitte.2.text

Aufruf: python3 scripts/i18n_daten_extrahieren.py [--schreiben]
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
I18N = DATA / "i18n"

# Zwei Töpfe, damit zwei Übersetzer je Sprache parallel arbeiten können, ohne
# sich in dieselbe Datei zu schreiben. Der Generator führt sie wieder zusammen.
TOEPFE = {
    "behdaten": ["behandlungsdaten"],
    "inhalte": ["risiken-gruppen", "recht", "beratung", "glossar", "seiteninhalte", "klinik"],
}

# Feldnamen, die nie übersetzt werden: Verweise, Kennungen, Zahlen, Redaktionsspuren.
NIE = {
    "slug", "kategorie", "gruppe", "freigabe", "tiefe", "waehrung", "quelle",
    "risiken_gruppe", "verwandt", "stand", "schema", "name_de", "id", "typ",
    "preis_ab", "preis_bis", "bild", "icon", "url", "href", "datum", "version",
    "sortierung", "kuerzel", "code", "lang", "freigabe_hinweis",
}

# Werte, die keine Übersetzung brauchen: reine Zahlen, Daten, Slugs, Kürzel.
NUR_TECHNISCH = re.compile(
    r"^(\d{4}-\d{2}-\d{2}|[\d.,:/+()\s-]*|[a-z0-9][a-z0-9/_-]*|[A-Z]{2,5})$"
)


def uebersetzbar(wert):
    if not isinstance(wert, str):
        return False
    t = wert.strip()
    if len(t) < 3:
        return False
    if NUR_TECHNISCH.fullmatch(t):
        return False
    return True


def sammle(knoten, pfad, raus):
    if isinstance(knoten, dict):
        for schluessel, wert in knoten.items():
            if schluessel.startswith("_") or schluessel in NIE:
                continue
            sammle(wert, pfad + [str(schluessel)], raus)
    elif isinstance(knoten, list):
        for i, wert in enumerate(knoten):
            sammle(wert, pfad + [str(i)], raus)
    elif uebersetzbar(knoten):
        raus[".".join(pfad)] = knoten.strip()


def main():
    gesamt = 0
    nachzuziehen = set()
    for topf, dateien in TOEPFE.items():
        raus = {}
        teile = []
        for name in dateien:
            pfad = DATA / f"{name}.json"
            if not pfad.exists():
                teile.append(f"{name}: fehlt")
                continue
            vorher = len(raus)
            sammle(json.loads(pfad.read_text()), ["daten", name], raus)
            teile.append(f"{name} {len(raus) - vorher}")
        gesamt += len(raus)
        print(f"{topf}: {len(raus)} Texte  ({', '.join(teile)})")

        if "--schreiben" in sys.argv:
            ziel = I18N / f"{topf}-de.json"
            alt = json.loads(ziel.read_text()) if ziel.exists() else {}
            ziel.write_text(json.dumps(raus, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
            neu = [k for k in raus if k not in alt]
            weg = [k for k in alt if k not in raus]
            geaendert = [k for k in raus if k in alt and raus[k] != alt[k]]
            print(f"  → {ziel.name}: neu {len(neu)}, geändert {len(geaendert)}, entfallen {len(weg)}")
            nachzuziehen |= set(neu) | set(geaendert)

    print(f"\nGesamt: {gesamt} Texte")
    if "--schreiben" in sys.argv:
        if nachzuziehen:
            (I18N / "daten-nachzuziehen.txt").write_text("\n".join(sorted(nachzuziehen)) + "\n")
            print(f"Nachzieh-Liste: data/i18n/daten-nachzuziehen.txt ({len(nachzuziehen)})")
    else:
        print("Mit --schreiben werden data/i18n/behdaten-de.json und inhalte-de.json erzeugt.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

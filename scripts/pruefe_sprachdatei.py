#!/usr/bin/env python3
"""Prüft eine Sprachdatei gegen die deutsche Vorlage.

Aufruf: python3 scripts/pruefe_sprachdatei.py <sprachcode>   z. B. en, tr, ar
Prüft data/i18n/seiten-<code>.json und data/i18n/katalog-<code>.json, soweit vorhanden.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
I18N = ROOT / "data" / "i18n"

# Werte, die absichtlich unübersetzt bleiben dürfen
EIGENNAMEN = {
    "ETA", "European Turkey Asia", "EUROPEAN TURKEY ASIA", "WhatsApp", "Instagram",
    "Facebook", "Messenger", "Istanbul", "Riverside Beauty", "St. Margrethen",
    "Botox", "FUE", "DHI", "PRP", "HIFU", "BBL", "Q-Switch",
    "Hollywood Smile", "HydraFacial", "info@eta-agency.ch", "+41 76 412 21 22",
}


def pruefe(art, code):
    de_pfad = I18N / f"{art}-de.json"
    zi_pfad = I18N / f"{art}-{code}.json"
    if not de_pfad.exists():
        print(f"[{art}] Vorlage {de_pfad.name} fehlt noch — übersprungen.")
        return 0
    if not zi_pfad.exists():
        print(f"[{art}] FEHLT: {zi_pfad.name} ist noch nicht angelegt.")
        return 1

    de = json.loads(de_pfad.read_text())
    zi = json.loads(zi_pfad.read_text())
    fehler = 0

    fehlend = [k for k in de if k not in zi]
    zuviel = [k for k in zi if k not in de]
    print(f"[{art}] {len(zi)} Schlüssel, erwartet {len(de)}")
    if fehlend:
        fehler += 1
        print(f"  FEHLEND ({len(fehlend)}):")
        for k in fehlend[:30]:
            print(f"    {k}  =  {de[k][:70]}")
        if len(fehlend) > 30:
            print(f"    … und {len(fehlend) - 30} weitere")
    if zuviel:
        fehler += 1
        print(f"  ÜBERZÄHLIG ({len(zuviel)}): {zuviel[:20]}")

    if list(de) != list(zi):
        print("  HINWEIS: Reihenfolge weicht von der Vorlage ab.")

    # Leer ist nur dann ein Fehler, wenn die deutsche Vorlage etwas enthält.
    # banner.other_lang ist bewusst überall leer, seit die Seiten vollständig
    # übersetzt sind — ein Hinweis "nur auf Deutsch verfügbar" wäre falsch.
    leer = [k for k, v in zi.items() if not str(v).strip() and str(de.get(k, "")).strip()]
    if leer:
        fehler += 1
        print(f"  LEER ({len(leer)}): {leer[:20]}")

    gleich = [k for k in de if k in zi and zi[k] == de[k] and de[k] not in EIGENNAMEN]
    if gleich:
        print(f"  UNÜBERSETZT ({len(gleich)}) — prüf jeden Eintrag, nur Eigennamen sind in Ordnung:")
        for k in gleich[:40]:
            print(f"    {k}  =  {zi[k][:70]}")
        if len(gleich) > 40:
            print(f"    … und {len(gleich) - 40} weitere")

    # Längenkontrolle für Suchmaschinen-Felder
    for k, v in zi.items():
        if k.endswith(".title") and len(v) > 70:
            print(f"  ZU LANG (Titel, {len(v)} Zeichen): {k}")
        if k.endswith(".desc") and k.startswith("meta.") and len(v) > 180:
            print(f"  ZU LANG (Meta, {len(v)} Zeichen): {k}")

    if not fehler and not gleich:
        print(f"  [{art}] sauber.")
    return fehler


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    code = sys.argv[1]
    fehler = pruefe("katalog", code) + pruefe("seiten", code)
    print()
    print("Ergebnis:", "sauber" if fehler == 0 else f"{fehler} Beanstandungen")
    return 1 if fehler else 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Prüft die Sprachauszeichnung der gebauten Website.

Aufruf: python3 scripts/pruefe_i18n.py [--ohne-bauen]

Ablauf:
  1. baut die Website (docs/)
  2. sammelt jedes data-i18n und data-i18n-attr aus docs/
  3. meldet Schlüssel, die im HTML stehen, aber in de.json fehlen
  4. meldet Schlüssel, die in de.json stehen, aber nirgends im HTML vorkommen
  5. meldet sichtbare Textstellen ohne data-i18n (Heuristik: Umlaute oder
     typisch deutsche Wörter)
  6. zusätzlich: meldet Schlüssel, deren Text im HTML vom Text in de.json abweicht

Rückgabewert 0, wenn Punkt 3 und Punkt 6 leer sind.
"""
import json
import re
import subprocess
import sys
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "docs"
DE_JSON = SITE / "assets" / "i18n" / "de.json"

# Leere Elemente haben kein schliessendes Tag.
LEER_TAGS = {
    "area", "base", "br", "col", "embed", "hr", "img", "input",
    "link", "meta", "param", "source", "track", "wbr",
}
# In diesen Elementen steht kein sichtbarer Fliesstext.
STUMME_TAGS = {"script", "style", "svg", "head"}

# Schlüssel, die nur das JavaScript setzt und die deshalb in keinem HTML stehen.
NUR_JAVASCRIPT = {
    "banner.other_lang",
    "nav.ablauf",
    "nav.behandlungen",
    "seite.allgemein.formular.status.gespeichert",
    "seite.allgemein.formular.status.wa_bereit",
    "seite.allgemein.wa.nachricht",
    "seite.allgemein.wa.nicht_verfuegbar",
}

# Typisch deutsche Wörter für die Heuristik in Punkt 5.
DEUTSCHE_WOERTER = {
    "aber", "alle", "allen", "als", "am", "an", "auch", "auf", "aus", "bei", "beim",
    "bis", "dabei", "das", "dass", "dem", "den", "der", "des", "die", "diese",
    "diesem", "diesen", "dieser", "dieses", "doch", "durch", "ein", "eine", "einem",
    "einen", "einer", "eines", "er", "es", "für", "gegen", "haben", "hat", "ihr",
    "ihre", "ihrem", "ihren", "ihrer", "im", "in", "ist", "kann", "keine", "können",
    "mehr", "mit", "nach", "nicht", "noch", "nur", "ob", "oder", "ohne", "sich",
    "sie", "sind", "so", "über", "um", "und", "uns", "unser", "unsere", "unserem",
    "unserer", "von", "vor", "was", "wenn", "werden", "wie", "wir", "wird", "zu",
    "zum", "zur", "anfrage", "behandlung", "behandlungen", "beratung", "klinik",
    "termin", "termine", "preis", "fragen", "seite", "jetzt", "bitte", "schweiz",
    "deutsch", "hotel", "kosten", "daten",
}
WORT_RE = re.compile(r"[A-Za-zÄÖÜäöüß]+")


def wirkt_deutsch(text):
    if any(z in text for z in "äöüÄÖÜß"):
        return True
    woerter = [w.lower() for w in WORT_RE.findall(text)]
    if not woerter:
        return False
    return any(w in DEUTSCHE_WOERTER for w in woerter)


def normal(text):
    return " ".join(text.split())


def erwartete_kuerzung(schluessel, soll, ist):
    """Auf den Kategorie-Kacheln steht nur der erste Satz der Behandlungsbeschreibung.
    Beim Umschalten erscheint dort die vollständige Beschreibung, das ist gewollt."""
    return schluessel.startswith("beh.") and schluessel.endswith(".desc") and soll.startswith(ist)


class Sammler(HTMLParser):
    """Liest eine HTML-Datei und sammelt Schlüssel, Texte und unmarkierte Stellen."""

    def __init__(self, datei):
        super().__init__(convert_charrefs=True)
        self.datei = datei
        self.stapel = []
        self.text_schluessel = {}   # Schlüssel -> Menge der Texte im HTML
        self.attr_schluessel = {}   # Schlüssel -> Menge der Attributwerte
        self.unmarkiert = []        # (Zeile, Text)

    # -------------------------------------------------------------- Hilfen
    def _oben(self, feld):
        return self.stapel[-1][feld] if self.stapel else False

    def _attr_schluessel_lesen(self, d):
        spec = d.get("data-i18n-attr")
        if not spec:
            return
        for teil in spec.split(";"):
            attribut, _, schluessel = teil.partition(":")
            if not schluessel:
                continue
            wert = d.get(attribut.strip(), "")
            self.attr_schluessel.setdefault(schluessel.strip(), set()).add(normal(wert))

    # -------------------------------------------------------------- Parser
    def handle_startendtag(self, tag, attrs):
        d = dict(attrs)
        self._attr_schluessel_lesen(d)

    def handle_starttag(self, tag, attrs):
        d = dict(attrs)
        self._attr_schluessel_lesen(d)
        if tag in LEER_TAGS:
            return
        schluessel = d.get("data-i18n")
        markiert = bool(schluessel) or ("data-i18n-region" in d) or self._oben("markiert")
        if "data-i18n-region" in d:
            self.text_schluessel.setdefault("contact.region", set())
        stumm = tag in STUMME_TAGS or self._oben("stumm")
        if tag == "title":
            stumm = False
        self.stapel.append({
            "tag": tag, "schluessel": schluessel,
            "markiert": markiert, "stumm": stumm, "text": "",
        })
        if schluessel:
            self.text_schluessel.setdefault(schluessel, set())

    def handle_data(self, data):
        if not self.stapel:
            return
        for rahmen in self.stapel:
            if rahmen["schluessel"]:
                rahmen["text"] += data
        oben = self.stapel[-1]
        if oben["stumm"] or oben["markiert"]:
            return
        text = normal(data)
        if text and wirkt_deutsch(text):
            self.unmarkiert.append((self.getpos()[0], text))

    def handle_endtag(self, tag):
        for i in range(len(self.stapel) - 1, -1, -1):
            if self.stapel[i]["tag"] == tag:
                for rahmen in self.stapel[i:]:
                    if rahmen["schluessel"]:
                        self.text_schluessel.setdefault(rahmen["schluessel"], set()).add(normal(rahmen["text"]))
                del self.stapel[i:]
                return

    def abschluss(self):
        for rahmen in self.stapel:
            if rahmen["schluessel"]:
                self.text_schluessel.setdefault(rahmen["schluessel"], set()).add(normal(rahmen["text"]))
        self.stapel = []


def sammle(dateien):
    texte = {}
    attribute = {}
    unmarkiert = []
    for f in dateien:
        s = Sammler(f)
        s.feed(f.read_text())
        s.close()
        s.abschluss()
        for k, v in s.text_schluessel.items():
            texte.setdefault(k, set()).update(x for x in v if x)
        for k, v in s.attr_schluessel.items():
            attribute.setdefault(k, set()).update(x for x in v if x)
        for zeile, text in s.unmarkiert:
            unmarkiert.append((f.relative_to(SITE).as_posix(), zeile, text))
    return texte, attribute, unmarkiert


def main():
    if "--ohne-bauen" not in sys.argv:
        print("→ baue die Website …")
        subprocess.run([sys.executable, str(ROOT / "scripts" / "build_site.py")], check=True)

    if not DE_JSON.exists():
        print("Fehler: docs/assets/i18n/de.json fehlt.")
        return 2
    de = json.loads(DE_JSON.read_text())

    dateien = sorted(SITE.rglob("*.html"))
    texte, attribute, unmarkiert = sammle(dateien)
    print(f"→ {len(dateien)} HTML-Dateien gelesen")

    im_html = set(texte) | set(attribute)

    # ---------------------------------------------------------------- 3
    fehlend = sorted(im_html - set(de))
    print(f"\n[3] Schlüssel im HTML, aber nicht in de.json: {len(fehlend)}")
    for k in fehlend:
        print("    " + k)

    # ---------------------------------------------------------------- 4
    ungenutzt = sorted(
        k for k in de
        if k not in im_html and k not in NUR_JAVASCRIPT and ".tpl." not in k
    )
    print(f"\n[4] Schlüssel in de.json, die im HTML nicht vorkommen: {len(ungenutzt)}")
    for k in ungenutzt:
        print("    " + k)

    # ---------------------------------------------------------------- 5
    gezaehlt = {}
    for datei, zeile, text in unmarkiert:
        gezaehlt.setdefault(text, []).append(f"{datei}:{zeile}")
    print(f"\n[5] sichtbare Textstellen ohne data-i18n: {len(gezaehlt)} verschiedene")
    for text in sorted(gezaehlt):
        stellen = gezaehlt[text]
        beispiel = stellen[0] + (f" (+{len(stellen) - 1} weitere)" if len(stellen) > 1 else "")
        print(f"    {beispiel}: {text[:110]}")

    # ---------------------------------------------------------------- 6
    abweichend = []
    gekuerzt = 0
    for k, werte in sorted(list(texte.items()) + list(attribute.items())):
        if k not in de:
            continue
        soll = normal(de[k])
        for ist in sorted(werte):
            if ist == soll:
                continue
            if erwartete_kuerzung(k, soll, ist):
                gekuerzt += 1
                continue
            abweichend.append((k, soll, ist))
    print(f"\n[6] Schlüssel mit abweichendem Text im HTML: {len(abweichend)}"
          f"  (zusätzlich {gekuerzt} bewusste Kürzungen auf den Kategorie-Kacheln)")
    for k, soll, ist in abweichend:
        print(f"    {k}\n        de.json: {soll[:100]}\n        HTML:    {ist[:100]}")

    print("\nZusammenfassung: "
          f"{len(im_html)} Schlüssel im HTML, {len(de)} in de.json, "
          f"{len(fehlend)} fehlend, {len(ungenutzt)} ungenutzt, "
          f"{len(gezaehlt)} unmarkierte Textstellen, {len(abweichend)} Abweichungen")
    return 0 if not fehlend and not abweichend else 1


if __name__ == "__main__":
    sys.exit(main())

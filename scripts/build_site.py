#!/usr/bin/env python3
"""Generiert die statische ETA-Website aus data/behandlungen.json + data/beschreibungen.json.

Aufruf: python3 scripts/build_site.py
Output: docs/ (kompletter Webroot, deploybar auf GitHub Pages und Vercel)

Sprachen: das HTML wird weiterhin auf Deutsch ausgegeben. Jeder sichtbare Text
traegt zusaetzlich data-i18n (Textinhalt) bzw. data-i18n-attr (Attribute).
Die Uebersetzungen liegen in data/i18n/ und werden beim Bauen zu
docs/assets/i18n/<lang>.json zusammengefuehrt.
"""
import hashlib
import json
import os
import re
import shutil
from datetime import date
from html import escape
from urllib.parse import quote
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "docs"
DATA = ROOT / "data"
STATIC = ROOT / "static"
I18N_QUELLE = DATA / "i18n"

# Eine einzige kanonische Adresse. Bis eine eigene Domain da ist, ist das die
# Vercel-Adresse; danach genuegt ETA_BASE_URL in den Projekteinstellungen.
# (Befund technik B1: canonical, og:image, robots.txt und alle Sitemap-Eintraege
# zeigten auf die GitHub-Pages-Adresse, die byte-identisch parallel live ist.)
BASE_URL = os.environ.get(
    "ETA_BASE_URL",
    "https://" + os.environ.get("VERCEL_PROJECT_PRODUCTION_URL", "eta-website-livid.vercel.app"),
).rstrip("/")
SPRACHEN = ["de", "en", "tr", "ar"]

KATALOG = json.loads((DATA / "behandlungen.json").read_text())
BESCHREIBUNGEN = json.loads((DATA / "beschreibungen.json").read_text())
# Kategorien, Gruppen, Behandlungsnamen und -beschreibungen auf Deutsch.
# Hier stehen auch die frueheren Konstanten KAT_TEASER und KAT_INTRO.
KATALOG_TEXTE = json.loads((I18N_QUELLE / "katalog-de.json").read_text())


def lies_optional(pfad, standard):
    """Liest eine Datendatei, die es geben darf, aber nicht geben muss.

    Die Redaktionsdaten (behandlungsdaten, klinik, recht) werden von einer
    anderen Bahn gepflegt. Fehlt eine Datei, soll der Build weiterlaufen und
    die betroffenen Zeilen einfach weglassen — nicht abbrechen.
    """
    if not pfad.exists():
        print(f"Hinweis: {pfad.name} fehlt, betroffene Angaben bleiben weg.")
        return standard
    return json.loads(pfad.read_text())


# Sachangaben je Behandlung (Aufenthalt, Dauer, Betaeubung, Preis ...).
BEHANDLUNGSDATEN = lies_optional(DATA / "behandlungsdaten.json", {}).get("behandlungen", {})
# Angaben zur Partnerklinik, streng getrennt nach belegt und offen.
KLINIK = lies_optional(DATA / "klinik.json", {})
# Impressum, Datenschutz und AGB als Datenstruktur.
RECHT = lies_optional(DATA / "recht.json", {})
# Inhalte fuer Seiten und Kontaktwege.
SEITENINHALTE = lies_optional(DATA / "seiteninhalte.json", {})
# Risikotexte je Behandlungsgruppe, Schluessel "<kategorie-id>/<gruppen-slug>".
RISIKEN = lies_optional(DATA / "risiken-gruppen.json", {})
RISIKEN_GRUPPEN = RISIKEN.get("gruppen", {})
# Fachbegriffe mit Kurz- und Langfassung. Lagen bis zur letzten Bahn ungenutzt
# da: «Graft» — die Groesse, nach der Haartransplantationen abgerechnet werden —
# stand auf sieben Seiten und wurde nirgends erklaert (Befund inhalt B13).
GLOSSAR = lies_optional(DATA / "glossar.json", {})
# Zweiter Zugang zum Katalog: nach Anliegen statt nach Verfahren, dazu fuenf
# Gegenueberstellungen (Befund inhalt B12).
BERATUNG = lies_optional(DATA / "beratung.json", {})
# Bauplan der Bildvarianten, erzeugt von scripts/bilder_aufbereiten.mjs.
BILD_VARIANTEN = lies_optional(STATIC / "assets" / "img" / "abgeleitet.json", {})


def load_bild_manifest():
    """Sammelt slug -> Bildpfad aus allen behandlung-bilder-manifest-*.json (von Higgsfield-Agenten geschrieben).
    Bilder muessen unter static/assets/ liegen (die Quelle, die build_site.py nach site/assets/ kopiert),
    nicht direkt unter site/assets/, da site/ bei jedem Build komplett neu aufgebaut wird."""
    bilder = {}
    static_assets = ROOT / "static" / "assets"
    for f in DATA.glob("behandlung-bilder-manifest-*.json"):
        for eintrag in json.loads(f.read_text()):
            if eintrag.get("status") == "ok" and eintrag.get("path") and (static_assets / Path(eintrag["path"]).relative_to("assets")).exists():
                bilder[eintrag["slug"]] = eintrag["path"]
    return bilder


BEHANDLUNG_BILDER = load_bild_manifest()

KAT_ICONS = {
    "plastische-chirurgie": '<path d="M12 3l2 6 6 2-6 2-2 6-2-6-6-2 6-2 2-6z"/>',
    "haartransplantation": '<path d="M6 3c3 3-3 6 0 10s-3 5 0 8"/><path d="M12 3c3 3-3 6 0 10s-3 5 0 8"/><path d="M18 3c3 3-3 6 0 10s-3 5 0 8"/>',
    "zaehne": '<path d="M12 3c-2 0-3 1.2-4.8 1.2S4 5 4 8c0 2.8 1.4 3.8 1.9 5.6.5 1.7.6 6.4 2.4 6.4 1.5 0 1-3.8 3.7-3.8s2.2 3.8 3.7 3.8c1.8 0 1.9-4.7 2.4-6.4.5-1.8 1.9-2.8 1.9-5.6 0-3-1.4-3.8-3.2-3.8S14 3 12 3z"/>',
    "haut-beauty": '<path d="M12 3s6 7 6 11a6 6 0 0 1-12 0c0-4 6-11 6-11z"/>',
    "medizinische-fachbereiche": '<path d="M4 20V6h16v14"/><path d="M9 20v-5h6v5"/><path d="M12 8v4"/><path d="M10 10h4"/>',
}

WA_SVG = '<svg width="{s}" height="{s}" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 005.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 00-3.48-8.413"/></svg>'


# ------------------------------------------------------------------- Formulare
# Version des Einwilligungstextes unter den Formularen. Wird mitgespeichert
# (contacts.einwilligungstext_version), damit später belegbar ist, wozu genau
# eingewilligt wurde. Bei jeder Textänderung hochzählen: v2, v3, ...
EINWILLIGUNG_VERSION = "v1"

# Honigtopf gegen automatische Ausfüller. Das Feld ist per CSS (.hp) unsichtbar
# und für Hilfsmittel wie Screenreader unsichtbar (aria-hidden, tabindex -1).
# Menschen sehen es nie, Bots füllen es aus – und werden in api/lead.mjs still
# verworfen. Bewusst kein display:none per Attribut: manche Bots überspringen
# genau solche Felder. Kein data-i18n, das Feld wird nie übersetzt.
# Pflichtfelder waren bisher weder sichtbar noch maschinenlesbar gekennzeichnet
# (Befund technik B9: 5 Pflichtfelder, 0 mit aria-required, 0 mit sichtbarem
# Hinweis). Der Stern ist fuer Hilfsmittel ausgeblendet, weil dort schon
# aria-required steht — sonst hoert man «Stern» zweimal.
PFLICHT_STERN = '<span class="pflicht" aria-hidden="true">*</span>'

# Die Statuszeile wechselt nach dem Absenden von hidden auf sichtbar. Ohne
# role/aria-live liest ein Vorleseprogramm diesen Wechsel nicht vor — der
# Besucher hoert nach dem Absenden nichts (Befund technik B9).
FORM_STATUS = '<p id="form-status" class="form-status small" role="status" aria-live="polite" hidden></p>'


def pflicht_hinweis():
    return (
        f'<p class="small muted form-pflicht">{PFLICHT_STERN} '
        f'<span{i18n("seite.allgemein.formular.pflichtfeld")}>Pflichtfeld</span></p>'
    )


HONEYPOT = (
    '<div class="hp" aria-hidden="true">'
    '<label>Website (bitte leer lassen)'
    '<input type="text" name="website" tabindex="-1" autocomplete="off">'
    "</label></div>"
)


# ------------------------------------------------------------------ i18n-Hilfen
VERWENDETE_SCHLUESSEL = set()

# Die Texte aus den Redaktionsdaten tragen eigene Schluessel nach dem Schema
#   daten.<dateiname-ohne-json>.<pfad-im-json-mit-punkten>
# Erzeugt von scripts/i18n_daten_extrahieren.py, abgelegt als
# data/i18n/behdaten-de.json (behandlungsdaten.json) und inhalte-de.json (die
# sechs uebrigen Dateien). Der Generator baut denselben Schluessel aus Datei
# und Pfad zusammen — siehe dkey() — und faellt still zurueck, wenn die
# Extraktion den Wert gar nicht erfasst hat.
DATEN_TEXTE = {}
for _topf in ("behdaten", "inhalte"):
    _quelle = I18N_QUELLE / f"{_topf}-de.json"
    if _quelle.exists():
        DATEN_TEXTE.update(json.loads(_quelle.read_text()))
    else:
        print(f"Hinweis: {_quelle.name} fehlt, die Werte daraus bleiben unausgezeichnet.")

# Datenschluessel, die im HTML gebraucht wuerden, die die Extraktion aber nicht
# kennt. Das ist der Normalfall fuer Zahlen, Kennungen und Redaktionsfelder;
# gezaehlt wird trotzdem, damit ein Umbau der Datendateien auffaellt.
UNBEKANNTE_DATENSCHLUESSEL = set()

# Werte, die der Generator vor der Ausgabe umformt. Im HTML steht die
# umgeformte Fassung; in der Sprachdatei stuende ohne Zutun die Rohfassung, und
# der Umschalter schoebe sie beim Wechsel zurueck auf die Seite.
# build_sprachdateien() legt deshalb dieselbe Umformung auf jede Sprache.
DATEN_ABGELEITET = {}


def dkey(datei, *pfad):
    """Baut den Schluessel eines Redaktionswerts: daten.<datei>.<pfad>.

    Listenindizes sind Zahlen ab 0, genau wie in behdaten-de.json und
    inhalte-de.json:
        dkey("behandlungsdaten", "behandlungen", "lidstraffung", "risiken", 7)
        -> daten.behandlungsdaten.behandlungen.lidstraffung.risiken.7
    """
    return "daten." + datei + "." + ".".join(str(teil) for teil in pfad)


def daten_bekannt(key):
    """Wahr, wenn die Extraktion diesen Wert erfasst hat und er ausgeliefert wird."""
    wert_ = DATEN_TEXTE.get(key)
    return wert_ is not None and not KLAMMER.search(wert_)


def dkey_abgeleitet(funktion, datei, *pfad):
    """Wie dkey(), merkt sich aber, dass der Wert vor der Ausgabe umgeformt wird."""
    key = dkey(datei, *pfad)
    if daten_bekannt(key):
        DATEN_ABGELEITET[key] = funktion
    return key


def i18n(key):
    """Gibt das data-i18n-Attribut zurueck (mit fuehrendem Leerzeichen) und merkt sich den Schluessel.

    Ein leerer Schluessel ergibt ein leeres Attribut — so darf jede Aufrufstelle
    einfach durchreichen, was sie hat. Dasselbe gilt fuer Datenschluessel, die
    die Extraktion nicht kennt: eine Zahl, eine Kennung oder ein Feld mit
    Klammer-Platzhalter bekommt kein data-i18n, damit nie ein Schluessel im
    HTML steht, den de.json nicht kennt.
    """
    if not key:
        return ""
    if key.startswith("daten.") and not daten_bekannt(key):
        UNBEKANNTE_DATENSCHLUESSEL.add(key)
        return ""
    VERWENDETE_SCHLUESSEL.add(key)
    return f' data-i18n="{key}"'


def i18n_attr(spec):
    """data-i18n-attr fuer Attribute, z. B. i18n_attr('placeholder:seite.kontakt.formular.name.ph').
    Mehrere Attribute durch Semikolon trennen."""
    for teil in spec.split(";"):
        VERWENDETE_SCHLUESSEL.add(teil.split(":", 1)[1])
    return f' data-i18n-attr="{spec}"'


def kat_name(kid):
    return KATALOG_TEXTE["kat." + kid + ".name"]


def kat_teaser(kid):
    return KATALOG_TEXTE["kat." + kid + ".teaser"]


def kat_intro(kid):
    return KATALOG_TEXTE["kat." + kid + ".intro"]


# Die WhatsApp-Nummer steht in data/seiteninhalte.json; main.js kennt dieselbe.
WA_NUMMER = re.sub(
    r"\D", "",
    ((SEITENINHALTE.get("kontaktwege") or {}).get("whatsapp") or {}).get("nummer") or "+41764122122",
)


def wa_link(kontext):
    if not WA_NUMMER:
        return ""
    return "https://wa.me/" + WA_NUMMER + ("?text=" + quote(kontext) if kontext else "")


def wa_button(label, size=18, cls="btn btn-gold", i18n_key="", kontext="", kontext_key=""):
    """WhatsApp-Knopf. Mit Kontext traegt er die Behandlung in die Nachricht.

    Die Beschriftung nennt den Kanal. data/seiteninhalte.json -> kontaktwege
    verlangt das ausdruecklich: «Muss als WhatsApp erkennbar sein, bevor sich
    die App oeffnet.» Vorher hiess der Knopf auf 112 Seiten «Unverbindlich
    anfragen» — das ist dort der Name des Formularwegs (Rang 1), nicht der
    von WhatsApp (Rang 2). Das Zeichen im Knopf ist aria-hidden; wer vorlesen
    laesst, hoert nur die Beschriftung.

    Ohne Kontext bleibt alles wie bisher: href="#", Klasse js-whatsapp, und
    main.js setzt den allgemeinen Text ein. Mit Kontext steht der fertige
    wa.me-Link schon im HTML — dann muss nichts nachgeladen werden, und der
    Link funktioniert auch ohne JavaScript. data-wa-kontext liegt zusaetzlich
    bereit, damit main.js den Text spaeter uebersetzen kann
    (Befund inhalt B6: eine Nachricht fuer 116 Seiten, jetzt 101 eigene).
    """
    i18n_attribut = i18n(i18n_key) if i18n_key else ""
    text = echt(kontext)
    if text and WA_NUMMER:
        # data-wa-key nennt den Schluessel der vorbereiteten Nachricht. main.js
        # baut den Link beim Sprachwechsel damit neu auf, sonst bliebe die
        # Nachricht auf allen 101 Seiten deutsch, obwohl sie uebersetzt vorliegt.
        key_attr = f' data-wa-key="{h(kontext_key)}"' if kontext_key else ""
        if kontext_key:
            VERWENDETE_SCHLUESSEL.add(kontext_key)
        return (f'<a href="{h(wa_link(text))}" class="{cls} js-whatsapp-kontext" '
                f'target="_blank" rel="noopener" data-wa-kontext="{h(text)}"{key_attr}>'
                f'{WA_SVG.format(s=size)}<span{i18n_attribut}>{label}</span></a>')
    return f'<a href="#" class="{cls} js-whatsapp">{WA_SVG.format(s=size)}<span{i18n_attribut}>{label}</span></a>'


UMLAUT_MAP = str.maketrans({"ä": "ae", "ö": "oe", "ü": "ue", "ß": "ss"})


def slugify(s):
    s = s.lower().translate(UMLAUT_MAP)
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s


NAV_KAT_ORDER = ["haut-beauty", "plastische-chirurgie", "haartransplantation", "zaehne", "medizinische-fachbereiche"]
NAV_KAT_I18N = {
    "haut-beauty": "nav.kat.hautbeauty",
    "plastische-chirurgie": "nav.kat.plastischechirurgie",
    "haartransplantation": "nav.kat.haartransplantation",
    "zaehne": "nav.kat.zaehne",
    "medizinische-fachbereiche": "nav.kat.medizinischefachbereiche",
}

# --------------------------------------------------------------- Navigation
# Welle 2 hat die Hauptnavigation neu gebaut. Vier Dinge waren kaputt:
#
#   1. Die Aufklappfelder trugen alle 116 Behandlungen und waren unterhalb der
#      Umschaltbreite per «display: none !important» abgeschaltet. Der Pfeil ▾
#      blieb sichtbar und versprach, was es dort nicht gab: am Handy fuehrte
#      das Menue zu keiner einzigen Behandlung (Befund responsiv B2).
#   2. Die Felder oeffneten allein per :hover / :focus-within. Wer mit der
#      Tastatur kam, wurde in 116 Verweise hineingezogen und kam mit Escape
#      nicht heraus — 122 Tab-Stationen vor der ersten Ueberschrift, auf jeder
#      Seite (Befund technik B5).
#   3. «Penisvergroesserung» stand im Menue jeder Seite, auch im Impressum
#      (Befund inhalt B14).
#   4. «Vorher / Nachher» stand im Menue, die Seite wird aber nicht mehr
#      erzeugt — ein toter Verweis auf 119 Seiten.
#
# Jetzt: je Kategorie hoechstens die Behandlungen, die data/behandlungen.json
# als «im_menue» fuehrt (32 von 101, redaktionell gesetzt von der Bahn
# «daten»), dazu «Alle Behandlungen ansehen». Der Rest bleibt vollstaendig im
# Katalog, auf der Kategorieseite und in der Suche — nichts wird versteckt,
# nur das Menue wird lesbar. Verweis und Aufklappknopf sind getrennte
# Bedienelemente; der Knopf traegt aria-expanded und aria-controls, und
# main.js schaltet ihn auf jeder Breite gleich.

# Pfeil am Aufklappknopf. Als Grafik, nicht als Schriftzeichen «▾» im
# ::after — das alte Zeichen hing am Verweis und liess sich deshalb nicht
# abschalten, wo es nichts zu oeffnen gab.
NAV_PANEL_ID = "nav-feld-"

NAV_CHEVRON = (
    '<svg class="nav-chevron" width="16" height="16" viewBox="0 0 24 24" fill="none" '
    'stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" '
    'aria-hidden="true"><path d="M6 9l6 6 6-6"/></svg>'
)


def nav_behandlungen(k):
    """Die Behandlungen einer Kategorie, die ins Menue gehoeren."""
    return [b for g in k["gruppen"] for b in g["behandlungen"] if b.get("im_menue")]


def nav_aufklapp(feld_id, kopf_html, name_i18n, name_de, eintraege_html):
    """Ein Menuepunkt aus Verweis, Aufklappknopf und Feld.

    Der Knopf traegt keine sichtbare Beschriftung, nur den Pfeil. Fuer
    Vorleseprogramme steht «Untermenü <Name>» darin — beide Teile mit eigenem
    Schluessel, damit der Sprachumschalter sie mitnimmt.
    """
    return (
        f'<div class="nav-drop">{kopf_html}'
        f'<button type="button" class="nav-drop-knopf" aria-expanded="false" aria-controls="{feld_id}">'
        f'<span class="nur-vorlesen">'
        f'<span{i18n("nav.untermenue")}>Untermenü</span> <span{i18n(name_i18n)}>{h(name_de)}</span>'
        f'</span>{NAV_CHEVRON}</button>'
        f'<div class="nav-drop-panel" id="{feld_id}">{eintraege_html}</div></div>'
    )


def nav_kat_dropdowns(prefix, active):
    kmap = {k["id"]: k for k in kats()}
    out = ""
    for kid in NAV_KAT_ORDER:
        k = kmap[kid]
        cls = ' class="nav-drop-link active"' if active == kid else ' class="nav-drop-link"'
        kopf = (f'<a href="{prefix}behandlungen/{kid}/index.html"{cls}'
                f'{i18n(NAV_KAT_I18N[kid])}>{h(k["name_de"])}</a>')
        eintraege = "".join(
            f'<a href="{prefix}behandlungen/{kid}/{b["slug"]}.html"'
            f'{i18n("beh." + b["slug"] + ".name")}>{h(b["name_de"])}</a>'
            for b in nav_behandlungen(k)
        )
        # Der letzte Eintrag fuehrt immer in den vollstaendigen Katalog. Die
        # Zahl bleibt unuebersetzt, das Wort davor nicht.
        eintraege += (
            f'<a class="nav-drop-alle" href="{prefix}behandlungen/{kid}/index.html">'
            f'<span{i18n("nav.alle_ansehen")}>Alle Behandlungen ansehen</span> '
            f'<span class="nav-drop-zahl">({kat_count(k)})</span></a>'
        )
        out += nav_aufklapp(NAV_PANEL_ID + kid, kopf, NAV_KAT_I18N[kid], k["name_de"], eintraege)
    return out


def nav_wissen_eintraege(prefix):
    """Die Seiten hinter «Gut zu wissen» — nur die, die es wirklich gibt.

    gut-zu-wissen.html hatte im ganzen Erzeugnis genau einen eingehenden
    Verweis, von der Startseite (Befund inhalt B11: «der teuerste einzelne
    Navigationsfehler»). Die drei Seiten aus Welle 2 standen bisher nur im
    Fussbereich; «Wenn etwas nicht wie geplant läuft» gehoert laut Uebergabe
    ausdruecklich in die Hauptnavigation.
    """
    eintraege = []
    if BERATUNG_ANLIEGEN:
        eintraege.append((SEITE_BERATUNG, "Was passt zu mir?", "seite.beratung.kurz"))
    if GLOSSAR_SORTIERT:
        eintraege.append((SEITE_GLOSSAR, "Fachbegriffe", "seite.glossar.kurz"))
    if SEITENINHALTE.get("wenn_etwas_schiefgeht"):
        eintraege.append((SEITE_SCHIEFGEHT, "Wenn etwas nicht wie geplant läuft", "seite.schiefgeht.kurz"))
    if SEITENINHALTE.get("reiseablauf"):
        eintraege.append((SEITE_REISE, "Ihre Reise", "seite.reise.kurz"))
    if SEITENINHALTE.get("gesamtkosten"):
        eintraege.append((SEITE_KOSTEN, "Was es kostet", "seite.kosten.kurz"))
    eintraege.append(("gut-zu-wissen.html", "Häufige Fragen", "footer.link.faq"))
    return "".join(
        f'<a href="{prefix}{ziel}"{i18n(key)}>{h(label)}</a>' for ziel, label, key in eintraege
    )


def nav_wissen(prefix, active=""):
    """«Gut zu wissen» im Menue. Die Seiten dahinter markieren den Punkt.

    Bisher rief keine der sechs Seiten hinter diesem Punkt header_nav mit
    einem aktiven Wert auf — der Menuepunkt blieb auf jeder von ihnen
    unmarkiert (navigation, offener Punkt 7).
    """
    cls = "nav-drop-link active" if active == "wissen" else "nav-drop-link"
    kopf = (f'<a href="{prefix}gut-zu-wissen.html" class="{cls}"'
            f'{i18n("nav.wissen")}>Gut zu wissen</a>')
    return nav_aufklapp(NAV_PANEL_ID + "wissen", kopf, "nav.wissen", "Gut zu wissen",
                        nav_wissen_eintraege(prefix))


SUCHE_LUPE = (
    '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
    'stroke-width="2" stroke-linecap="round" aria-hidden="true">'
    '<circle cx="11" cy="11" r="7"/><path d="M20 20l-3.5-3.5"/></svg>'
)


def kopf_suche(prefix):
    """Das Suchfeld in der Kopfleiste.

    Befund inhalt B11: null Suchfelder bei 101 Behandlungen. Wer
    «Nasenkorrektur» sucht, musste wissen, dass sie unter «Plastische
    Chirurgie» liegt. Der Index entsteht in build_suchindex() und liegt als
    assets/suche.json bereit (101 Behandlungen mit 198 Synonymen, dazu die
    festen Seiten); main.js laedt ihn beim ersten Tastendruck und filtert im
    Browser. Kein Server, kein Fremdpaket.

    Ohne JavaScript fuehrt das Absenden auf den Gesamtkatalog — ein Weg, der
    weiterfuehrt, statt einer Sackgasse.
    """
    return (
        f'<form class="kopf-suche" role="search" action="{prefix}behandlungen/index.html" '
        f'method="get" autocomplete="off">'
        f'<label class="nur-vorlesen" for="suche-feld"{i18n("nav.suche.label")}>Behandlung suchen</label>'
        f'<input id="suche-feld" class="suche-feld" type="search" name="q" '
        f'role="combobox" aria-expanded="false" aria-controls="suche-liste" '
        f'aria-autocomplete="list" aria-describedby="suche-hilfe" '
        f'placeholder="Behandlung suchen …"'
        f'{i18n_attr("placeholder:nav.suche.platzhalter")}>'
        f'<span class="suche-lupe" aria-hidden="true">{SUCHE_LUPE}</span>'
        f'<ul id="suche-liste" class="suche-liste" role="listbox" aria-label="Suchvorschläge"'
        f'{i18n_attr("aria-label:nav.suche.vorschlaege")} hidden></ul>'
        f'<p id="suche-hilfe" class="nur-vorlesen"{i18n("nav.suche.hilfe")}>'
        f'Vorschläge erscheinen beim Tippen. Mit Pfeil nach unten auswählen, mit Eingabe öffnen.</p>'
        f'<p id="suche-status" class="nur-vorlesen" role="status" aria-live="polite"></p>'
        f'</form>'
    )


# --------------------------------------------------------------- Werkzeuge
def h(wert_):
    """Maskiert einen Datenwert fuer HTML — Text wie Attribut.

    Ab hier laeuft jeder Wert aus data/*.json hier durch. Vorher standen 760
    rohe & im Erzeugnis, und ein einziges Anfuehrungszeichen in einer
    Beschreibung haette ein content="..."-Attribut beendet (Befund technik B12).
    """
    return escape(str(wert_), quote=True)


# Eckige Klammern sind in diesen Daten immer Platzhalter, nie Inhalt.
KLAMMER = re.compile(r"\[[^\]]*\]")
# Grossgeschriebene Klammerwerte wie [X TAGE] oder [PLZ ORT] — die tauchen auch
# mitten in einem Satz auf und duerfen nirgends ausgeliefert werden.
KLAMMER_GROSS = re.compile(r"\[[A-ZÄÖÜ][A-ZÄÖÜ0-9 .:/-]*\]")


def echt(wert_):
    """Gibt den Wert zurueck, wenn er echt ist — sonst None.

    Echt heisst: vorhanden, nicht leer und kein Platzhalter in eckigen
    Klammern. Der Auftraggeber hat entschieden: kein Wert -> die Zeile wird
    gar nicht erst ausgegeben, nicht per CSS versteckt und nicht durch
    «k. A.» ersetzt.
    """
    if wert_ is None:
        return None
    text = " ".join(str(wert_).split())
    if not text or KLAMMER.fullmatch(text):
        return None
    return text


def fakt(label, wert_, label_key="", wert_key=""):
    """Eine Zeile im Kasten «Auf einen Blick» — nur wenn es etwas zu sagen gibt."""
    text = echt(wert_)
    if text is None:
        return ""
    return (f'<div class="fact"><span{i18n(label_key)}>{h(label)}</span>'
            f'<strong{i18n(wert_key)}>{h(text)}</strong></div>')


def span(text, key=""):
    """Ein Textstueck mit eigenem Schluessel.

    data-i18n ersetzt den ganzen Textinhalt eines Elements. Steht Text neben
    einer Zahl, einem Symbol, einem Link oder einem zweiten Text, bekommt er
    deshalb ein eigenes <span> — und nur das <span> wird ausgezeichnet.
    """
    return f"<span{i18n(key)}>{h(text)}</span>"


def kurzfassen(text, grenze=155):
    """Kappt eine Meta-Beschreibung an der Wortgrenze (Befund technik B13).

    Google schneidet um 155–160 Zeichen ab; 54 von 116 Beschreibungen lagen
    darueber und verloren genau den Vertrauenssatz am Ende.
    """
    text = " ".join(str(text).split())
    if len(text) <= grenze:
        return text
    schnitt = text[:grenze].rsplit(" ", 1)[0]
    return schnitt.rstrip(" ,;:–-") + " …"


# Saetze, die nur fuer ETA und die Redaktion bestimmt sind. Sie stehen mitten in
# sonst brauchbaren Feldern — «Ueblicherweise nach Zahl der Grafts. Die Spanne ist
# von ETA einzutragen.» Der erste Satz gehoert auf die Seite, der zweite nicht.
REDAKTIONSNOTIZEN = ("einzutragen", "noch festzulegen", "vor der veröffentlichung", "noch zu klären")


def saetze(text):
    """Zerlegt einen Text in Saetze, samt Satzzeichen."""
    return re.findall(r"[^.!?]+[.!?]*", text)


def ohne_redaktionsnotiz(wert_):
    """Entfernt die Saetze, die sich an ETA richten, und gibt den Rest zurueck.

    «Ueblicherweise nach Zahl der Grafts. Die Spanne ist von ETA einzutragen.»
    -> der erste Satz gehoert auf die Seite, der zweite nicht. Bleibt nichts
    uebrig, faellt die Zeile ganz weg.
    """
    text = echt(wert_)
    if text is None:
        return None
    text = re.sub(r"\s+und ist von ETA einzutragen", "", text, flags=re.IGNORECASE)
    return echt("".join(
        x for x in saetze(text) if not any(n in x.lower() for n in REDAKTIONSNOTIZEN)
    ))


def aufenthalt_kurz(wert_):
    """Kuerzt den Aufenthaltswert auf das, was neben dem Etikett Sinn ergibt.

    Das Etikett heisst «Aufenthalt in Istanbul»; im Wert stand bisher noch
    einmal «3 Naechte in Istanbul» und bei den Riverside-Behandlungen ein
    ganzer Nebensatz, der zwei Zeilen darunter der Zeile «Klinik» widersprach
    (gemeldet von der Bahn geruest an die Redaktion).
    """
    text = echt(wert_)
    if text is None:
        return None
    if text.lower().startswith("kein"):
        text = re.split(r"\s+—\s+", text, 1)[0]
        text = re.sub(r"^kein(?:en)? (?:eigener )?Aufenthalt(?: in Istanbul)? nötig",
                      "Nicht nötig", text, flags=re.IGNORECASE)
        return text[0].upper() + text[1:]
    return re.sub(r"\b(Nächte|Nacht) in Istanbul\b", r"\1", text)


def absaetze(werte, klasse="", key=""):
    """Mehrere Absaetze aus einer Liste oder einem einzelnen Text.

    key ist der Schluessel des Datenfelds. Steht dort ein einzelner Text,
    bekommt der Absatz genau diesen Schluessel; steht dort eine Liste, bekommt
    jeder Absatz key.<index> — dieselbe Schreibweise, in der die Schluessel in
    behdaten-de.json und inhalte-de.json stehen. Der Index zaehlt die Rohliste,
    nicht die ausgegebenen Absaetze: leere Eintraege verschieben nichts.
    """
    einzeln = isinstance(werte, str)
    if einzeln:
        werte = [werte]
    c = f' class="{klasse}"' if klasse else ""
    raus = ""
    for i, wert_ in enumerate(werte or []):
        text = echt(wert_)
        if not text:
            continue
        raus += f"<p{c}{i18n(key if einzeln else f'{key}.{i}' if key else '')}>{h(text)}</p>"
    return raus


def punkte(werte, klasse="punkt-liste", key=""):
    """Eine Liste — oder nichts, wenn nichts drinsteht.

    Standard ist die neutrale Aufzaehlung. «check-list» traegt einen goldenen
    Haken und gehoert nur dorthin, wo ein Haken stimmt: Leistungsumfang,
    Packliste, belegte Zertifikate. Neben «Flug ab der Schweiz — nicht
    enthalten» oder neben einem Risiko waere er eine falsche Aussage.

    key ist der Schluessel der Liste; jeder Eintrag bekommt key.<index>.
    """
    eintraege = ""
    for i, wert_ in enumerate(werte or []):
        text = echt(wert_)
        if not text:
            continue
        eintraege += f"<li{i18n(f'{key}.{i}' if key else '')}>{h(text)}</li>"
    return f'<ul class="{klasse}">{eintraege}</ul>' if eintraege else ""


def block(titel, inhalt, i18n_key="", stufe="h2"):
    """Ueberschrift plus Inhalt — oder gar nichts, wenn der Inhalt leer ist.

    Das ist die Regel des Auftraggebers in einer Funktion: kein Wert, keine
    Zeile. Eine leere Ueberschrift ist schlimmer als eine fehlende.
    """
    if not inhalt or not inhalt.strip():
        return ""
    return f"\n    <{stufe}{i18n(i18n_key)}>{h(titel)}</{stufe}>\n    {inhalt}"


def fakt_liste(zeilen):
    """Mehrere .fact-Zeilen aus (Etikett, Wert)-Paaren.

    Wahlweise mit Schluesseln: (Etikett, Wert, Etikett-Schluessel,
    Wert-Schluessel). Die Argumente gehen unveraendert an fakt().
    """
    return "\n      ".join(z for z in (fakt(*zeile) for zeile in zeilen) if z)


# Slug -> (Kategorie-ID, Name) fuer Querverweise zwischen Behandlungen.
def _slug_register():
    reg = {}
    for k in KATALOG["kategorien"]:
        for g in k["gruppen"]:
            for b in g["behandlungen"]:
                reg[b["slug"]] = (k["id"], b["name_de"])
    return reg


SLUG_REGISTER = _slug_register()


# Die drei neuen Inhaltsseiten. Sie entstehen nur, wenn data/seiteninhalte.json
# den Block mitbringt; sonst wird auch nirgends dorthin verwiesen.
def _seitenpfad(schluessel, standard):
    block_ = SEITENINHALTE.get(schluessel) or {}
    return (echt(block_.get("slug")) or standard) + ".html"


SEITE_SCHIEFGEHT = _seitenpfad("wenn_etwas_schiefgeht", "wenn-etwas-nicht-wie-geplant-laeuft")
SEITE_REISE = _seitenpfad("reiseablauf", "ihre-reise")
SEITE_KOSTEN = _seitenpfad("gesamtkosten", "was-es-kostet")
SEITE_GLOSSAR = "fachbegriffe.html"
SEITE_BERATUNG = "was-passt-zu-mir.html"


# ------------------------------------------------------------- Fachbegriffe
def _glossar_register():
    """Begriffe aus data/glossar.json, jeder mit Sprungmarke und Suchmuster.

    Das Suchmuster ist der Begriff selbst plus moegliche deutsche Endungen:
    «Graft» findet «Grafts», «Krone» findet «Kronen», «Masseter» findet
    «Massetermuskel». Bewusst kein Wortstamm — «Vene» wuerde sonst «Venen»
    treffen und dort «Veneer» erklaeren, wo von Blutgefaessen die Rede ist.
    Der erste Buchstabe darf gross oder klein sein, der Rest muss stimmen.
    """
    reg = {}
    for e in GLOSSAR.get("eintraege", []):
        begriff = echt(e.get("begriff"))
        kurz = echt(e.get("kurz"))
        if not begriff or not kurz:
            continue
        erst = begriff[0]
        rest = re.escape(begriff[1:])
        muster = re.compile(
            r"(?<![0-9A-Za-zÄÖÜäöüß])[" + erst.upper() + erst.lower() + r"]" + rest
            + r"[a-zäöüß]*(?![0-9A-Za-zÄÖÜäöüß])"
        )
        reg[begriff] = {
            "eintrag": e,
            "slug": slugify(begriff),
            "kurz": kurz,
            "lang": echt(e.get("lang")),
            "muster": muster,
            "behandlungen": [x for x in e.get("behandlungen", []) if x],
            "siehe_auch": [x for x in e.get("siehe_auch", []) if x],
        }
    return reg


GLOSSAR_REGISTER = _glossar_register()
# Alphabetisch nach deutschem Begriff — die Reihenfolge der Seite.
GLOSSAR_SORTIERT = sorted(GLOSSAR_REGISTER.items(), key=lambda kv: kv[0].lower())


def glossar_schluessel(slug, feld):
    return f"glossar.{slug}.{feld}"


# ---------------------------------------------------------------- Beratung
BERATUNG_ANLIEGEN = [a for a in BERATUNG.get("anliegen", []) if echt(a.get("titel"))]
_VERGLEICHE = BERATUNG.get("vergleiche") or {}
VERGLEICH_GRUPPEN = {k: v for k, v in (_VERGLEICHE.get("gruppen") or {}).items() if v.get("behandlungen")}
VERGLEICH_SPALTEN = _VERGLEICHE.get("spalten_standard") or []
# Behandlung -> Vergleichsgruppe, damit die Gegenueberstellung dort steht, wo
# jemand schwankt: auf der Detailseite jeder beteiligten Behandlung.
VERGLEICH_FUER_SLUG = {}
for _gid, _g in VERGLEICH_GRUPPEN.items():
    for _s in _g["behandlungen"]:
        VERGLEICH_FUER_SLUG.setdefault(_s, _gid)


def vergleich_slug(gid):
    """«haut-beauty/straffung-ohne-op» -> «haut-beauty-straffung-ohne-op»."""
    return slugify(gid)


def prefix_fuer(relpath):
    """Wie viele Ebenen es von dieser Seite bis zur Wurzel sind."""
    return "../" * relpath.count("/")


# ------------------------------------------------------------------- Bilder
def bild(prefix, quelle, alt, sizes, klasse="", eager=False, alt_i18n="", breite_max=None):
    """Gibt ein <picture> mit WebP-Varianten und JPEG-Rueckfall aus.

    quelle ist der Pfad unterhalb von assets/img/, so wie er in
    static/assets/img/abgeleitet.json steht (z. B. "hero-a.jpg" oder
    "behandlungen/gesichts-botox.jpg"). Ohne Bauplan-Eintrag faellt die
    Funktion auf das Originalbild zurueck, damit der Build nie bricht.

    eager=True ist fuer das Bild, das den groessten Bildaufbau ausmacht: kein
    loading="lazy" (das senkt die Prioritaet) und fetchpriority="high".
    """
    v = BILD_VARIANTEN.get(quelle)
    a_attr = i18n_attr("alt:" + alt_i18n) if alt_i18n else ""
    c_attr = f' class="{klasse}"' if klasse else ""
    prio = ' fetchpriority="high" decoding="async"' if eager else ' loading="lazy" decoding="async"'
    if not v:
        return f'<img{c_attr} src="{prefix}assets/img/{quelle}" alt="{h(alt)}"{a_attr}{prio}>'

    stamm = quelle.rsplit(".", 1)[0]
    webp = [x for x in v["webp"] if not breite_max or x["breite"] <= breite_max] or v["webp"]
    jpg = [x for x in v["jpg"] if not breite_max or x["breite"] <= breite_max] or v["jpg"]
    rueckfall = jpg[-1] if jpg else webp[-1]
    endung = "jpg" if jpg else "webp"
    quellen = ", ".join(f'{prefix}assets/img/{stamm}-{x["breite"]}.webp {x["breite"]}w' for x in webp)
    jpg_srcset = ", ".join(f'{prefix}assets/img/{stamm}-{x["breite"]}.jpg {x["breite"]}w' for x in jpg)
    quelle_tag = f'<source type="image/webp" srcset="{quellen}" sizes="{sizes}">' if webp else ""
    srcset_attr = f' srcset="{jpg_srcset}" sizes="{sizes}"' if len(jpg) > 1 else ""
    return (
        f"<picture>{quelle_tag}"
        f'<img{c_attr} src="{prefix}assets/img/{stamm}-{rueckfall["breite"]}.{endung}"{srcset_attr} '
        f'alt="{h(alt)}"{a_attr} width="{rueckfall["breite"]}" height="{rueckfall["hoehe"]}"{prio}>'
        f"</picture>"
    )


def bild_vorladen(prefix, quelle, sizes, breite_max=None):
    """preload fuer das Hero-Bild: es soll starten, bevor das CSS da ist."""
    v = BILD_VARIANTEN.get(quelle)
    if not v or not v["webp"]:
        return ""
    stamm = quelle.rsplit(".", 1)[0]
    webp = [x for x in v["webp"] if not breite_max or x["breite"] <= breite_max] or v["webp"]
    srcset = ", ".join(f'{prefix}assets/img/{stamm}-{x["breite"]}.webp {x["breite"]}w' for x in webp)
    return (
        f'\n  <link rel="preload" as="image" type="image/webp" '
        f'href="{prefix}assets/img/{stamm}-{webp[len(webp) // 2]["breite"]}.webp" '
        f'imagesrcset="{srcset}" imagesizes="{sizes}" fetchpriority="high">'
    )


# ------------------------------------------------------- Strukturierte Daten
def ld(*objekte):
    """JSON-LD-Block. json.dumps maskiert </script> nicht — deshalb der Ersatz."""
    teile = [o for o in objekte if o]
    if not teile:
        return ""
    daten = teile[0] if len(teile) == 1 else teile
    s = json.dumps(daten, ensure_ascii=False, separators=(",", ":"))
    return '\n  <script type="application/ld+json">' + s.replace("</", "<\\/") + "</script>"


def ld_organisation():
    """Nur Angaben, die stimmen. Keine erfundenen Bewertungen, keine Adresse,
    die im Impressum noch fehlt."""
    firma = RECHT.get("firma", {})
    org = {
        "@context": "https://schema.org",
        "@type": "MedicalBusiness",
        "@id": f"{BASE_URL}/#organisation",
        "name": "ETA – European Turkey Asia",
        "url": BASE_URL + "/",
        "logo": f"{BASE_URL}/assets/img/eta-logo.png",
        "image": f"{BASE_URL}/assets/img/og-image-1200.jpg",
        "telephone": "+41764122122",
        "email": "info@eta-agency.ch",
        "availableLanguage": ["de", "en", "tr", "ar"],
        "areaServed": [
            {"@type": "Country", "name": "Schweiz"},
            {"@type": "Country", "name": "Österreich"},
            {"@type": "Country", "name": "Deutschland"},
        ],
        "description": (
            "Vermittlung ästhetischer und medizinischer Behandlungen in einer festen "
            "Partnerklinik in Istanbul, mit deutschsprachiger Betreuung aus der Schweiz."
        ),
    }
    adresse = {"@type": "PostalAddress", "addressCountry": "CH"}
    if echt(firma.get("strasse")):
        adresse["streetAddress"] = echt(firma["strasse"])
    if echt(firma.get("plz")):
        adresse["postalCode"] = echt(firma["plz"])
    if echt(firma.get("ort")):
        adresse["addressLocality"] = echt(firma["ort"])
    org["address"] = adresse
    if echt(firma.get("name")):
        org["legalName"] = echt(firma["name"])
    same = [url for _name, url in sozial_adressen()]
    if same:
        org["sameAs"] = same
    return org


def ld_krumen(paare):
    """BreadcrumbList aus (Name, absolute URL)-Paaren."""
    return {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": i + 1, "name": n, "item": u}
            for i, (n, u) in enumerate(paare)
        ],
    }


def ld_faq(eintraege):
    """FAQPage. Nur mit Fragen, die auf derselben Seite auch sichtbar stehen."""
    return {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": [
            {"@type": "Question", "name": frage, "acceptedAnswer": {"@type": "Answer", "text": antwort}}
            for _nr, frage, antwort in eintraege
        ],
    }


def ld_faq_paare(paare):
    """FAQPage aus (Frage, Antwort)-Paaren, fuer die Behandlungsseiten."""
    return {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": [
            {"@type": "Question", "name": f_, "acceptedAnswer": {"@type": "Answer", "text": a}}
            for f_, a in paare
        ],
    }


# ------------------------------------------------------------------ Schrift
# Vorgeladen wird nur Jost, die Schrift des Fliesstexts. Gemessen am
# gedrosselten Handynetz (1,6 Mbit/s, CPU x4, Startseite, je zweiter Lauf):
#   beide Schriften vorgeladen  FCP 1192 ms  LCP 1272 ms  CLS 0,000
#   nur Jost vorgeladen         FCP 1008 ms  LCP 1068 ms  CLS 0,000   <- gewaehlt
#   keine Schrift vorgeladen    FCP  856 ms  LCP  948 ms  CLS 0,011
# Playfair steht nur in Ueberschriften; dank der Masskorrektur unten
# verschiebt ihr spaeterer Austausch nichts.
# Die Schriften kommen nicht mehr von Google, sondern aus assets/fonts/
# (Befund technik B7: CLS 0,110 allein vom Schriftwechsel, dazu zwei
# Fremdhosts und die Referrer-Weitergabe jeder besuchten URL an Google).
#
# Die zweite Haelfte ist der Teil, der den Versatz tilgt: die Rueckfallschrift
# bekommt die Masse der Webschrift aufgepraegt. Gemessen in Chromium gegen
# Times/Arial-Masse (Playfair 107,6 % Breite, Jost 94,6 %), deshalb steht
# local('Times New Roman') bzw. local('Arial') bewusst an erster Stelle: so
# gilt auf jedem Betriebssystem dieselbe Grundlage.
def schrift_css(prefix):
    f = prefix + "assets/fonts/"
    lat = "U+0000-00FF,U+0131,U+0152-0153,U+02BB-02BC,U+02C6,U+02DA,U+02DC,U+2000-206F,U+20AC,U+2122"
    ext = "U+0100-02BA,U+02BD-02C5,U+02C7-02CC,U+02CE-02D7,U+02DD-02FF,U+1E00-1E9F,U+1EF2-1EFF,U+2020,U+20A0-20AB,U+20AD-20C0,U+2113,U+2C60-2C7F,U+A720-A7FF"
    return (
        "@font-face{font-family:'Playfair Display';font-style:normal;font-weight:400 700;font-display:swap;"
        f"src:url('{f}playfair-latin.woff2') format('woff2');unicode-range:{lat}}}"
        "@font-face{font-family:'Playfair Display';font-style:normal;font-weight:400 700;font-display:swap;"
        f"src:url('{f}playfair-latin-ext.woff2') format('woff2');unicode-range:{ext}}}"
        "@font-face{font-family:'Jost';font-style:normal;font-weight:300 600;font-display:swap;"
        f"src:url('{f}jost-latin.woff2') format('woff2');unicode-range:{lat}}}"
        "@font-face{font-family:'Jost';font-style:normal;font-weight:300 600;font-display:swap;"
        f"src:url('{f}jost-latin-ext.woff2') format('woff2');unicode-range:{ext}}}"
        "@font-face{font-family:'Georgia';src:local('Times New Roman'),local('Liberation Serif'),local('Tinos'),local('Georgia');"
        "size-adjust:107.6%;ascent-override:100.4%;descent-override:23.2%;line-gap-override:0%}"
        "@font-face{font-family:'Playfair-Rueckfall';src:local('Times New Roman'),local('Liberation Serif'),local('Tinos'),local('Georgia');"
        "size-adjust:107.6%;ascent-override:100.4%;descent-override:23.2%;line-gap-override:0%}"
        "@font-face{font-family:'Helvetica Neue';src:local('Arial'),local('Liberation Sans'),local('Arimo'),local('Helvetica Neue');"
        "size-adjust:94.6%;ascent-override:113.1%;descent-override:40.2%;line-gap-override:0%}"
        "@font-face{font-family:'Jost-Rueckfall';src:local('Arial'),local('Liberation Sans'),local('Arimo'),local('Helvetica Neue');"
        "size-adjust:94.6%;ascent-override:113.1%;descent-override:40.2%;line-gap-override:0%}"
    )


# Das Woerterbuch wird bisher erst von main.js geholt, und main.js steht ganz
# unten. Wer einen anderssprachigen Browser hat, sieht deshalb erst die
# deutsche Fassung und dann den Austausch — gemessen 0,048 CLS auf der
# Startseite (geruest, Bitte 6). Diese fuenfzehn Zeilen starten dieselbe
# Anfrage im <head>, also waehrend das Stylesheet noch laedt und lange vor dem
# ersten Bildaufbau. Sie aendern nichts an der Seite: kein lang, kein dir, kein
# Text. Faellt die Anfrage aus, faellt nur der Vorlauf aus, und main.js holt
# die Datei wie bisher selbst.
I18N_VORLAUF = (
    '(function(){try{'
    'var S=["de","en","tr","ar"],w=null;'
    'try{w=localStorage.getItem("eta_lang")}catch(e){}'
    'if(S.indexOf(w)<0){w=null;'
    'var l=(navigator.languages&&navigator.languages.length)?navigator.languages:[navigator.language||"de"];'
    'for(var i=0;i<l.length&&!w;i++){var c=String(l[i]||"").toLowerCase().split("-")[0];'
    'if(S.indexOf(c)>=0)w=c}}'
    'if(!w)w="de";'
    'window.__etaSprache=w;'
    'if(window.fetch)window.__etaWoerter=fetch("__WURZEL__assets/i18n/"+w+".json",'
    '{credentials:"same-origin"}).then(function(a){return a.ok?a.json():null})'
    '["catch"](function(){return null});'
    '}catch(e){}})();'
)


def head(title, desc, prefix, canonical, title_key, desc_key, jsonld="", vorladen="", robots=""):
    t_i18n = i18n(title_key)
    d_attr = i18n_attr("content:" + desc_key)
    t_attr = i18n_attr("content:" + title_key)
    title = h(title)
    desc = h(kurzfassen(desc))
    robots_meta = f'\n  <meta name="robots" content="{robots}">' if robots else ""
    return f"""<!DOCTYPE html>
<html lang="de-CH">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title{t_i18n}>{title}</title>
  <meta name="description"{d_attr} content="{desc}">
  <link rel="canonical" href="{canonical}">{robots_meta}
  <meta name="theme-color" content="#050505">
  <meta property="og:type" content="website">
  <meta property="og:locale" content="de_CH">
  <meta property="og:site_name" content="ETA – European Turkey Asia">
  <meta property="og:title"{t_attr} content="{title}">
  <meta property="og:description"{d_attr} content="{desc}">
  <meta property="og:url" content="{canonical}">
  <meta property="og:image" content="{BASE_URL}/assets/img/og-image-1200.jpg">
  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:title"{t_attr} content="{title}">
  <meta name="twitter:description"{d_attr} content="{desc}">
  <meta name="twitter:image" content="{BASE_URL}/assets/img/og-image-1200.jpg">
  <link rel="icon" href="{prefix}assets/img/favicon.png" type="image/png">
  <link rel="preload" as="font" type="font/woff2" href="{prefix}assets/fonts/jost-latin.woff2" crossorigin>{vorladen}
  <style>{schrift_css(prefix)}</style>
  <script>{I18N_VORLAUF.replace("__WURZEL__", prefix)}</script>
  <link rel="stylesheet" href="{prefix}assets/css/style.css{CSS_VERSION}">{jsonld}
</head>
<body>
<a class="skip-link" href="#inhalt"{i18n('seite.allgemein.sprunglink')}>Zum Inhalt springen</a>"""


def logo_bild(prefix):
    """Das Zeichen in der Kopfleiste, in der Groesse, in der es gezeigt wird.

    Vorher lag hier das 400 x 334 grosse Original: 16 KB fuer eine Flaeche von
    48 x 40 CSS-Pixeln, auf jeder Seite (Bitte 4 von «geruest», offen
    geblieben bei «navigation»). Die Stufen kommen aus
    scripts/bilder_aufbereiten.mjs. Bei Pixelverhaeltnis 2 laedt ein heutiger
    Browser jetzt 1,2 KB statt 16 KB.

    «width» und «height» stehen weiter drin — ohne sie springt die Leiste beim
    Laden. Das Original bleibt ausgeliefert, weil die Organisationsangabe im
    JSON-LD darauf zeigt.
    """
    img = f"{prefix}assets/img/eta-logo"
    return (
        "<picture>"
        f'<source type="image/webp" srcset="{img}-48.webp 1x, {img}-96.webp 2x, {img}-144.webp 3x">'
        f'<img src="{img}-96.png" srcset="{img}-48.png 1x, {img}-96.png 2x, {img}-144.png 3x" '
        f'alt="ETA – European Turkey Asia" class="logo" width="48" height="40" '
        f'fetchpriority="high" decoding="async">'
        "</picture>"
    )


def header_nav(prefix, active=""):
    """Kopfbereich und Hauptnavigation.

    Aufbau seit Welle 2, von oben nach unten:

      .kopf-strip   Sprachumschalter. Steht beim Seitenaufruf sofort im Bild
                    und scrollt dann weg — er wird einmal benutzt, nicht
                    dauernd. Deshalb ist er der Teil des Kopfes, der nicht
                    klebt.
      .header-bar   Zeichen, Suchfeld, WhatsApp-Knopf, Menueknopf. Das ist die
                    Leiste, die klebt.
      nav.main-nav  ab 1360 px das dunkle Band, darunter das Aufklappmenue.

    Warum das so aussieht: «.main-nav» war als «sticky» deklariert und klebte
    genau 63 px weit, weil ein «sticky»-Element nur innerhalb des Kastens
    seines Elternelements klebt — hier das 113 px hohe <header> (Befund
    responsiv B3). Auf einer Katalogseite, die am Handy 19,5 Bildschirme lang
    ist, gab es ab dem zweiten Wisch keinerlei Navigation mehr. Jetzt klebt
    «.site-header» selbst, um die Hoehe des Strips nach oben versetzt
    («top: calc(-1 * var(--strip-hoehe))»). Stehen bleibt genau die schlanke
    Leiste mit Zeichen, Suche und Menueknopf.
    """
    # Das Sprachbanner wird vom JavaScript gefüllt, der Schlüssel gehört trotzdem dazu.
    VERWENDETE_SCHLUESSEL.add("banner.other_lang")

    def a(href, label, key, i18n_key=""):
        cls = ' class="active"' if key == active else ""
        i18n_attribut = i18n(i18n_key) if i18n_key else ""
        return f'<a href="{href}"{cls}{i18n_attribut}>{label}</a>'

    # Die feste WhatsApp-Blase steht nicht mehr auf der Kontaktseite: dort lag
    # sie ueber dem Hinweis unter dem Formular, und daneben gibt es bereits
    # eine WhatsApp-Karte und den Absendeknopf — drei Wege nebeneinander
    # helfen nicht (Befund responsiv B12). Auf allen anderen Seiten tritt sie
    # zurueck, sobald die Fusszeile im Bild ist; das erledigt main.js.
    blase = "" if active == "kontakt" else (
        f'<a href="#" class="wa-float js-whatsapp" aria-label="Per WhatsApp anfragen"'
        f'{i18n_attr("aria-label:seite.allgemein.wa_float.aria")}>{WA_SVG.format(s=28)}</a>'
    )

    return f"""
<header class="site-header">
  <div class="kopf-strip">
    <div class="lang-switch" role="group" aria-label="Sprache wählen"{i18n_attr('aria-label:seite.allgemein.sprachwahl.aria')}>
      <a href="#" data-lang="de">DE</a><a href="#" data-lang="en">EN</a><a href="#" data-lang="tr">TR</a><a href="#" data-lang="ar">AR</a>
    </div>
  </div>
  <div class="header-bar">
    <a href="{prefix}index.html" class="logo-link">{logo_bild(prefix)}</a>
    {kopf_suche(prefix)}
    <div class="header-actions">
      {wa_button('WhatsApp', 17, 'btn btn-gold btn-sm', 'nav.whatsapp')}
      <button class="nav-toggle" id="nav-toggle" type="button" aria-expanded="false" aria-controls="main-nav" aria-label="Menü öffnen"{i18n_attr('aria-label:seite.allgemein.menue.aria')}>
        <svg class="ikon-burger" width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" aria-hidden="true"><path d="M4 7h16"/><path d="M4 12h16"/><path d="M4 17h16"/></svg>
        <svg class="ikon-x" width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" aria-hidden="true"><path d="M6 6l12 12"/><path d="M18 6L6 18"/></svg>
      </button>
    </div>
  </div>
  <nav class="main-nav" id="main-nav" tabindex="-1" aria-label="Hauptnavigation"{i18n_attr('aria-label:nav.aria')}>
    <div class="main-nav-inner">
      {nav_kat_dropdowns(prefix, active)}
      {nav_wissen(prefix, active)}
      {a(prefix + 'partnerklinik.html', 'Partnerklinik', 'partnerklinik', 'nav.partnerklinik')}
      {a(prefix + 'finanzierung.html', 'Finanzierung', 'finanzierung', 'nav.finanzierung')}
      {a(prefix + 'kontakt.html', 'Kontakt', 'kontakt', 'nav.kontakt')}
    </div>
  </nav>
</header>
{blase}
<p id="lang-banner" class="lang-banner" hidden></p>
"""


def sozial_adressen():
    """Die echten Adressen der sozialen Netze — heute noch keine."""
    netze = SEITENINHALTE.get("kontaktwege", {}).get("soziale_netze", {})
    namen = {"instagram": "Instagram", "facebook": "Facebook", "tiktok": "TikTok", "youtube": "YouTube"}
    return [(namen[k], echt(netze.get(k))) for k in namen if echt(netze.get(k))]


def sozial_links():
    """Im Fussbereich standen 116-mal «Instagram», «Facebook» und «Messenger»
    als href="#" — Links, die auf dieselbe Seite fuehren. Ein fehlender Link
    kostet nichts, ein toter kostet Glaubwuerdigkeit (Befund inhalt B2)."""
    eintraege = sozial_adressen()
    if not eintraege:
        return ""
    teile = "<span>·</span>".join(
        f'<a href="{h(url)}" rel="noopener me" target="_blank">{h(name)}</a>' for name, url in eintraege
    )
    return f'<div class="footer-social">{teile}</div>'


def footer(prefix):
    return f"""
<footer class="site-footer">
  <div class="footer-grid">
    <div class="footer-brand">
      <div class="footer-logo">ETA</div>
      <div class="footer-sub">EUROPEAN TURKEY ASIA</div>
      <p{i18n('footer.tagline')}>Ihre Agentur für Schönheitsbehandlungen in Istanbul, mit Betreuung aus der Schweiz, Österreich und Deutschland.</p>
    </div>
    <div>
      <div class="footer-title"{i18n('footer.titel.behandlungen')}>Behandlungen</div>
      <a href="{prefix}behandlungen/plastische-chirurgie/index.html"{i18n('kat.plastische-chirurgie.name')}>Plastische Chirurgie</a>
      <a href="{prefix}behandlungen/haartransplantation/index.html"{i18n('kat.haartransplantation.name')}>Haartransplantation</a>
      <a href="{prefix}behandlungen/zaehne/index.html"{i18n('kat.zaehne.name')}>Zähne</a>
      <a href="{prefix}behandlungen/haut-beauty/index.html"{i18n('kat.haut-beauty.name')}>Haut &amp; Beauty</a>
      <a href="{prefix}behandlungen/medizinische-fachbereiche/index.html"{i18n('kat.medizinische-fachbereiche.name')}>Medizinische Fachbereiche</a>
      <a href="{prefix}behandlungen/index.html"{i18n('seite.behandlungen.titel')}>Alle Behandlungen</a>
      {f'<a href="{prefix}{SEITE_BERATUNG}"{i18n("seite.beratung.kurz")}>Was passt zu mir?</a>' if BERATUNG_ANLIEGEN else ''}
    </div>
    <div>
      <div class="footer-title"{i18n('footer.titel.rechtliches')}>Rechtliches</div>
      <a href="{prefix}impressum.html"{i18n('footer.link.impressum')}>Impressum</a>
      <a href="{prefix}agb.html"{i18n('footer.link.agb')}>AGB</a>
      <a href="{prefix}datenschutz.html"{i18n('footer.link.datenschutz')}>Datenschutz</a>
    </div>
    <div>
      <div class="footer-title"{i18n('footer.titel.wissen')}>Gut zu wissen</div>
      <a href="{prefix}gut-zu-wissen.html"{i18n('footer.link.faq')}>Häufige Fragen</a>
      <a href="{prefix}{SEITE_REISE}"{i18n('seite.reise.kurz')}>Ihre Reise</a>
      <a href="{prefix}{SEITE_KOSTEN}"{i18n('seite.kosten.kurz')}>Was es kostet</a>
      <a href="{prefix}{SEITE_SCHIEFGEHT}"{i18n('seite.schiefgeht.kurz')}>Wenn etwas nicht wie geplant läuft</a>
      {f'<a href="{prefix}{SEITE_GLOSSAR}"{i18n("seite.glossar.kurz")}>Fachbegriffe</a>' if GLOSSAR_SORTIERT else ''}
    </div>
    <div>
      <div class="footer-title"{i18n('footer.titel.kontakt')}>Kontakt</div>
      <a href="{prefix}kontakt.html"{i18n('nav.kontakt')}>Kontakt</a>
      <div class="footer-line">WhatsApp: <a href="tel:+41764122122">+41 76 412 21 22</a></div>
      <div class="footer-line"><span{i18n('footer.kontakt.email')}>E-Mail:</span> <a href="mailto:info@eta-agency.ch">info@eta-agency.ch</a></div>
      <div class="footer-line"><span{i18n('footer.kontakt.nachsorge')}>Nachsorge-Partner:</span> Riverside Beauty, St. Margrethen</div>
      {sozial_links()}
    </div>
  </div>
  <div class="footer-bottom">
    <div>© 2026 ETA. <span{i18n('footer.bottom.rechte')}>Alle Rechte vorbehalten.</span></div>
    <div{i18n('footer.bottom.hinweis')}>ETA ist eine Vermittlungsagentur und erbringt selbst keine medizinischen Leistungen.</div>
  </div>
</footer>
<script src="{prefix}assets/js/main.js{JS_VERSION}"></script>
</body>
</html>"""


def cta_band(title, sub, key, label=None, label_key=None, kontext="", kontext_key=""):
    """CTA-Band. key ist der Schluesselstamm, z. B. seite.index.cta -> .titel / .sub."""
    if label is None:
        label = "Per WhatsApp schreiben"
        label_key = "seite.allgemein.cta.anfragen"
    t_i18n = i18n(key + ".titel")
    s_i18n = i18n(key + ".sub")
    return f"""
<section class="cta-band">
  <div class="cta-inner">
    <div>
      <h2{t_i18n}>{title}</h2>
      <p{s_i18n}>{sub}</p>
    </div>
    {wa_button(label, 18, 'btn btn-gold', label_key, kontext, kontext_key)}
  </div>
</section>"""


def ph_tile_vn(cls="ph-tile"):
    """Platzhalterkachel Vorher/Nachher."""
    return (
        f'<div class="{cls}"><span class="ph-wm">ETA</span>'
        f'<span class="ph-text"><span{i18n("seite.allgemein.ph.vorhernachher")}>[VORHER / NACHHER]</span><br>'
        f'<span{i18n("seite.allgemein.ph.bildmaterial")}>Bildmaterial der Klinik folgt</span></span></div>'
    )


PAGES = []  # (relpath, html) für sitemap


def write_page(relpath, html):
    out = SITE / relpath
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html)
    PAGES.append(relpath)


def kats():
    return KATALOG["kategorien"]


def kat_count(k):
    return sum(len(g["behandlungen"]) for g in k["gruppen"])


def anzahl_badge(n):
    """'12 BEHANDLUNGEN' - Zahl bleibt unuebersetzt, das Wort bekommt einen Schluessel."""
    return f'<span>{n}</span> <span{i18n("seite.allgemein.behandlungen_gross")}>BEHANDLUNGEN</span>'


def datei_version(relativ):
    """Kurzer Inhalts-Fingerabdruck fuer style.css und main.js.

    Damit duerfen die beiden Dateien ein Jahr lang zwischengespeichert werden
    (Befund technik B6): aendert sich der Inhalt, aendert sich die Adresse.
    main.js schneidet Abfrageteile beim Ermitteln des Wurzelpfads ab, der
    Anhang stoert dort also nicht.
    """
    quelle = STATIC / "assets" / relativ
    if not quelle.exists():
        return ""
    return "?v=" + hashlib.sha256(quelle.read_bytes()).hexdigest()[:8]


CSS_VERSION = ""
JS_VERSION = ""


def kanonisch(relpath):
    """Die eine gueltige Adresse dieser Seite — dieselbe in canonical, og:url
    und Sitemap. Vorher standen dort drei verschiedene Schreibweisen."""
    return f"{BASE_URL}/" if relpath == "index.html" else f"{BASE_URL}/{relpath}"


def seite(relpath, kopf, nav, rumpf, prefix):
    """Setzt eine Seite zusammen. Nur hier gibt es <main> — genau einmal.

    Vorher hatte keine der 116 Seiten eine <main>-Landmarke; Vorleseprogramme
    hatten damit keinen Weg, die 122 Kopf-Links zu ueberspringen
    (Befund technik B5).
    """
    erwartet = prefix_fuer(relpath)
    if prefix != erwartet:
        raise SystemExit(f"Abbruch: falscher Pfadanfang für {relpath}: {prefix!r} statt {erwartet!r}")
    write_page(relpath, kopf + nav + '\n<main id="inhalt" tabindex="-1">' + rumpf + "\n</main>" + footer(prefix))


# ------------------------------------------------------------- Haeufige Fragen
# Die Fragen stehen genau einmal hier: die Startseite zeigt vier davon,
# gut-zu-wissen.html alle sieben, und dieselbe Liste speist das FAQPage-JSON-LD.
# Vorher standen sie zweimal woertlich im Generator — fuer FAQPage muessen
# sichtbarer Text und Auszeichnung zwingend uebereinstimmen (Befund technik B3).
FAQ = [
    (
        "1",
        "Darf ich eine Begleitperson mitbringen?",
        "Ja, sehr gerne. Viele unserer Kundinnen und Kunden reisen zu zweit. Ihre Begleitperson "
        "ist beim Beratungsgespräch in der Klinik dabei und im Hotel untergebracht.",
    ),
    (
        "2",
        "Wie lange bleibe ich in Istanbul?",
        "Das hängt von der Behandlung ab, von einem Tagesbesuch bis zu rund einer Woche. "
        "Die genaue Dauer steht in Ihrem persönlichen Angebot.",
    ),
    (
        "3",
        "In welcher Sprache werde ich betreut?",
        "Ihre Betreuung durch ETA läuft auf Deutsch, Englisch, Türkisch oder Arabisch, ganz wie "
        "Sie es bevorzugen. In der Partnerklinik werden Sie ebenfalls fremdsprachig begleitet.",
    ),
    (
        "4",
        "Wer operiert bzw. behandelt mich?",
        "Die Fachärztinnen und Fachärzte unserer Partnerklinik in Istanbul. Vor jeder Behandlung "
        "findet eine persönliche Beratung und Voruntersuchung statt.",
    ),
    (
        "5",
        "Was ist im Preis enthalten?",
        "Ihr Angebot ist ein Fixpreis der Klinik und enthält Behandlung, Flughafen-Transfer und "
        "Hotel. Den Flug buchen Sie selbst, auf Wunsch helfen wir dabei.",
    ),
    (
        "6",
        "Wie läuft die Nachsorge in der Schweiz?",
        "Die Nachkontrolle findet bei unserem Partner Riverside Beauty im Rheintal statt, in "
        "direkter Abstimmung mit der Klinik in Istanbul.",
    ),
    (
        "7",
        "Was passiert, wenn ich meinen Termin verschieben muss?",
        "Termine können bis 72 Stunden vorher kostenlos verschoben werden. "
        "Details regelt Ihre Buchungsbestätigung.",
    ),
]
FAQ_INDEX = [e for e in FAQ if e[0] in ("1", "2", "3", "6")]


def faq_html(eintraege):
    return "\n    ".join(
        f'<details{" open" if i == 0 else ""}>'
        f'<summary{i18n("seite.gutzuwissen.faq." + nr + ".frage")}>{h(frage)}</summary>'
        f'<p{i18n("seite.gutzuwissen.faq." + nr + ".antwort")}>{h(antwort)}</p></details>'
        for i, (nr, frage, antwort) in enumerate(eintraege)
    )


# ---------------------------------------------------------------- Startseite
def build_index():
    prefix = ""
    cards = ""
    order = ["plastische-chirurgie", "haartransplantation", "zaehne", "haut-beauty"]
    for k in sorted([k for k in kats() if k["id"] in order], key=lambda k: order.index(k["id"])):
        kid = k["id"]
        n_i18n = i18n("kat." + kid + ".name")
        t_i18n = i18n("kat." + kid + ".teaser")
        mehr = i18n("seite.allgemein.mehr_erfahren")
        cards += f"""
      <a class="cat-card" href="behandlungen/{kid}/index.html">
        <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#c58a32" stroke-width="1.5">{KAT_ICONS[kid]}</svg>
        <h3{n_i18n}>{h(k['name_de'])}</h3>
        <div class="cat-count">{anzahl_badge(kat_count(k))}</div>
        <p{t_i18n}>{h(kat_teaser(kid))}</p>
        <span class="link"{mehr}>Mehr erfahren</span>
      </a>"""

    hero_alt = "Zwei zufriedene Kundinnen und Kunden vor der Partnerklinik in Istanbul"
    kopf = head(
        "ETA – Schönheitsbehandlungen in Istanbul, betreut aus der Schweiz",
        "Plastische Chirurgie, Haartransplantation, Zähne und Beauty in Istanbul. Deutschsprachige Betreuung, fixe Partnerklinik, Transfer und Hotel inklusive.",
        prefix, f"{BASE_URL}/", "meta.index.title", "meta.index.desc",
        jsonld=ld(
            ld_organisation(),
            {"@context": "https://schema.org", "@type": "WebSite", "name": "ETA – European Turkey Asia",
             "url": BASE_URL + "/", "inLanguage": "de-CH",
             "publisher": {"@id": f"{BASE_URL}/#organisation"}},
            ld_faq(FAQ_INDEX),
        ),
        vorladen=bild_vorladen(prefix, "hero-a.jpg", "100vw"),
    )
    rumpf = f"""
<section class="hero">
  {bild(prefix, "hero-a.jpg", hero_alt, "100vw", klasse="hero-media", eager=True, alt_i18n="seite.index.hero.bild_alt")}
  <div class="hero-overlay"></div>
  <div class="hero-content">
    <div class="eyebrow"{i18n('hero.eyebrow')}>European Turkey Asia</div>
    <h1{i18n('hero.headline')}>Ihre Schönheitsbehandlung in Istanbul. Betreut von A bis Z.</h1>
    <p{i18n('hero.sub')}>Deutschsprachige Beratung, eine fest geprüfte Partnerklinik und ein Rundum-Paket mit Transfer, Hotel und Nachsorge. Sie kümmern sich um nichts ausser sich selbst.</p>
    <div class="hero-ctas">
      {wa_button('Per WhatsApp schreiben', 18, 'btn btn-gold', 'hero.cta1')}
      <a href="behandlungen/index.html" class="btn btn-outline-light"{i18n('hero.cta2')}>Behandlungen entdecken</a>
    </div>
    <div class="hero-trust"><span{i18n('hero.trust1')}>Deutschsprachige Betreuung</span><span class="dot">·</span><span{i18n('hero.trust2')}>Fixe Partnerklinik</span><span class="dot">·</span><span{i18n('hero.trust3')}>Transfer &amp; Hotel inklusive</span></div>
  </div>
</section>

<section class="section">
  <div class="section-head">
    <div>
      <div class="eyebrow gold"{i18n('seite.index.kat.eyebrow')}>Behandlungen</div>
      <h2{i18n('seite.index.kat.titel')}>Vier Bereiche, ein Ansprechpartner</h2>
    </div>
    <a class="link" href="behandlungen/index.html"{i18n('seite.index.kat.link')}>Alle Behandlungen ansehen</a>
  </div>
  <div class="grid-4">{cards}
  </div>
</section>

<section class="usp-band">
  <div class="grid-4">
    <div class="usp"><span class="usp-icon"><svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#c58a32" stroke-width="1.5"><path d="M4 5h16v11H9l-5 4V5z"/></svg></span><h3{i18n('seite.index.usp.1.titel')}>Deutschsprachige Betreuung</h3><p{i18n('seite.index.usp.1.text')}>Von der ersten Anfrage bis zur Nachkontrolle, eine feste Ansprechperson.</p></div>
    <div class="usp"><span class="usp-icon"><svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#c58a32" stroke-width="1.5"><path d="M4 20V6h16v14"/><path d="M9 20v-5h6v5"/><path d="M12 8v4"/><path d="M10 10h4"/></svg></span><h3{i18n('seite.index.usp.2.titel')}>Fixe Partnerklinik</h3><p{i18n('seite.index.usp.2.text')}>Unser Klinikpartner in Istanbul, von uns persönlich besucht und laufend betreut.</p></div>
    <div class="usp"><span class="usp-icon"><svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#c58a32" stroke-width="1.5"><path d="M2 12l19-9-6 19-3.5-7L2 12z"/></svg></span><h3{i18n('seite.index.usp.3.titel')}>Rundum-Paket</h3><p{i18n('seite.index.usp.3.text')}>Flughafen-Transfer, Hotel und Behandlung aus einer Hand organisiert.</p></div>
    <div class="usp"><span class="usp-icon"><svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#c58a32" stroke-width="1.5"><path d="M12 3l7 3v5c0 5-3.5 8-7 9-3.5-1-7-4-7-9V6l7-3z"/></svg></span><h3{i18n('seite.index.usp.4.titel')}>Nachsorge in der Schweiz</h3><p{i18n('seite.index.usp.4.text')}>Nachkontrolle im Rheintal, in Zusammenarbeit mit Riverside Beauty.</p></div>
  </div>
</section>

<section class="section">
  <div class="eyebrow gold"{i18n('seite.index.schritte.eyebrow')}>So funktioniert es</div>
  <h2{i18n('seite.index.schritte.titel')}>In vier Schritten zu Ihrer Behandlung</h2>
  <div class="grid-4 steps">
    <div class="step"><div class="step-nr">01</div><h3{i18n('seite.index.schritte.1.titel')}>Anfrage</h3><p{i18n('seite.index.schritte.1.text')}>Per WhatsApp oder Formular, unverbindlich und diskret.</p></div>
    <div class="step"><div class="step-nr">02</div><h3{i18n('seite.index.schritte.2.titel')}>Beratung &amp; Angebot</h3><p{i18n('seite.index.schritte.2.text')}>Persönliches Gespräch auf Deutsch, danach ein Fixpreis-Angebot der Klinik.</p></div>
    <div class="step"><div class="step-nr">03</div><h3{i18n('seite.index.schritte.3.titel')}>Anzahlung &amp; Reise</h3><p{i18n('seite.index.schritte.3.text')}>Termin sichern und Flug buchen. Transfer und Hotel organisiert die Klinik.</p></div>
    <div class="step"><div class="step-nr">04</div><h3{i18n('seite.index.schritte.4.titel')}>Behandlung &amp; Nachsorge</h3><p{i18n('seite.index.schritte.4.text')}>Eingriff in Istanbul, Nachkontrolle bei uns im Rheintal.</p></div>
  </div>
  <p class="small"><a class="link" href="{SEITE_REISE}"{i18n('seite.index.link.reise')}>Ihre Reise, Tag für Tag</a> · <a class="link" href="{SEITE_KOSTEN}"{i18n('seite.index.link.kosten')}>Was es insgesamt kostet</a> · <a class="link" href="{SEITE_SCHIEFGEHT}"{i18n('seite.index.link.schiefgeht')}>Wenn etwas nicht wie geplant läuft</a></p>
</section>

<section class="section section-rose">
  <div class="eyebrow gold"{i18n('seite.index.fin.eyebrow')}>Finanzierung</div>
  <h2{i18n('seite.index.fin.titel')}>Drei Wege zu Ihrem Wunschtermin</h2>
  <div class="grid-3">
    <div class="card"><h3 class="serif"{i18n('seite.index.fin.1.titel')}>3 Raten, 0 % Zins</h3><p{i18n('seite.index.fin.1.text')}>Der Behandlungspreis in drei Teilzahlungen, zinsfrei mit fixer Bearbeitungsgebühr.</p></div>
    <div class="card"><h3 class="serif"{i18n('seite.index.fin.2.titel')}>Ratenkauf mit Laufzeit</h3><p{i18n('seite.index.fin.2.text.ohne_anbieter')}>Flexible Laufzeiten über unseren Zahlungspartner, Abwicklung direkt online.</p></div>
    <div class="card"><h3 class="serif"{i18n('seite.index.fin.3.titel')}>Ansparmodell</h3><p{i18n('seite.index.fin.3.text')}>Sie sparen in Ihrem Tempo an. Sobald der Betrag erreicht ist, steht Ihr Termin fest.</p></div>
  </div>
  <p class="small muted"><span{i18n('seite.index.fin.hinweis')}>Konditionen und Details erhalten Sie im persönlichen Beratungsgespräch.</span> <a href="finanzierung.html"{i18n('seite.index.fin.hinweis_link')}>Mehr zur Finanzierung</a></p>
</section>

<section class="section faq-section">
  <div class="faq-intro">
    <div class="eyebrow gold"{i18n('seite.index.faq.eyebrow')}>Gut zu wissen</div>
    <h2{i18n('seite.index.faq.titel')}>Häufige Fragen</h2>
    <p{i18n('seite.index.faq.text')}>Ihre Frage ist nicht dabei? Schreiben Sie uns direkt per WhatsApp, wir antworten persönlich.</p>
    <a class="link" href="gut-zu-wissen.html"{i18n('seite.index.faq.link')}>Alle Fragen ansehen</a>
  </div>
  <div class="faq-list">
    {faq_html(FAQ_INDEX)}
  </div>
</section>
""" + cta_band(
        "Erzählen Sie uns, was Sie sich wünschen.",
        "Unverbindlich, diskret und auf Deutsch. Wir melden uns in der Regel noch am selben Tag.",
        "seite.index.cta", "Jetzt per WhatsApp anfragen", "seite.index.cta.knopf",
    )
    seite("index.html", kopf, header_nav(prefix, "start"), rumpf, prefix)


# ------------------------------------------------------- Behandlungs-Übersicht
def beratung_einstieg(prefix):
    """Der zweite Weg in den Katalog, ganz oben auf der Katalogseite.

    Der Katalog ist nach Verfahren sortiert. Wer sein Anliegen kennt, aber
    nicht den Namen des Verfahrens, fand hier bisher 101 Fachbegriffe und
    keinen Einstieg (Befund inhalt B12). Die drei genannten Anliegen sind die
    ersten drei aus data/beratung.json und fuehren mit einer Sprungmarke
    direkt zum jeweiligen Abschnitt.
    """
    if not BERATUNG_ANLIEGEN:
        return ""
    beispiele = "".join(
        f'<a class="anliegen-chip" href="{prefix}{SEITE_BERATUNG}#{h(a["id"])}"'
        f'{i18n("beratung.anliegen." + a["id"] + ".titel")}>{h(a["titel"])}</a>'
        for a in BERATUNG_ANLIEGEN[:3]
    )
    return f"""
<section class="section beratung-einstieg">
  <div class="card">
    <h2{i18n('seite.behandlungen.beratung.titel')}>Sie kennen Ihr Anliegen, nicht das Verfahren?</h2>
    <p{i18n('seite.behandlungen.beratung.text')}>Dann suchen Sie nicht nach dem Namen. Wir haben 13 häufige Anliegen zusammengestellt und sagen zu jedem, welche Verfahren in Frage kommen und worin sie sich unterscheiden.</p>
    <div class="anliegen-chips">{beispiele}</div>
    <a class="btn btn-outline" href="{prefix}{SEITE_BERATUNG}"{i18n('seite.behandlungen.beratung.link')}>Nach Anliegen suchen</a>
  </div>
</section>"""


def build_behandlungen_index():
    prefix = "../"
    blocks = ""
    for k in kats():
        kid = k["id"]
        cards = ""
        for g in k["gruppen"]:
            for b in g["behandlungen"]:
                b_i18n = i18n("beh." + b["slug"] + ".name")
                mehr = i18n("seite.allgemein.mehr_erfahren")
                cards += f'<a class="t-card" href="{kid}/{b["slug"]}.html"><h3{b_i18n}>{h(b["name_de"])}</h3><span class="link"{mehr}>Mehr erfahren</span></a>\n'
        n_i18n = i18n("kat." + kid + ".name")
        blocks += f"""
<section class="section kat-block">
  <div class="section-head">
    <div>
      <h2{n_i18n}>{h(k['name_de'])}</h2>
      <div class="cat-count">{anzahl_badge(kat_count(k))}</div>
    </div>
    <a class="link" href="{kid}/index.html"><span{i18n('seite.behandlungen.zur_uebersicht')}>Zur Übersicht</span> <span{n_i18n}>{h(k['name_de'])}</span></a>
  </div>
  <div class="grid-4">{cards}</div>
</section>"""

    kopf = head(
        "Alle Behandlungen | ETA",
        "Der komplette Behandlungskatalog unserer Partnerklinik in Istanbul: Plastische Chirurgie, Haartransplantation, Zähne, Haut und Beauty.",
        prefix, kanonisch("behandlungen/index.html"), "meta.behandlungen.title", "meta.behandlungen.desc",
        jsonld=ld(
            ld_organisation(),
            ld_krumen([("Start", kanonisch("index.html")), ("Behandlungen", kanonisch("behandlungen/index.html"))]),
        ),
    )
    rumpf = f"""
<section class="page-band">
  <div class="crumbs"><a href="{prefix}index.html"{i18n('seite.allgemein.crumb.start')}>Start</a><span>/</span><span{i18n('seite.allgemein.crumb.behandlungen')}>Behandlungen</span></div>
  <h1{i18n('seite.behandlungen.titel')}>Alle Behandlungen</h1>
  <p{i18n('seite.behandlungen.text')}>Der komplette Katalog unserer Partnerklinik, übersetzt und für Sie aufbereitet. Jede Behandlung beginnt mit einem unverbindlichen Beratungsgespräch auf Deutsch.</p>
</section>
{beratung_einstieg(prefix)}
{blocks}
""" + cta_band(
        "Unsicher, welche Behandlung passt?",
        "Wir beraten Sie unverbindlich und auf Deutsch.",
        "seite.allgemein.cta.unsicher",
    )
    seite("behandlungen/index.html", kopf, header_nav(prefix, ""), rumpf, prefix)


# --------------------------------------------------------------- Kategorien
def build_kategorien():
    for k in kats():
        kid = k["id"]
        prefix = "../../"
        groups = ""
        for g in k["gruppen"]:
            g_slug = slugify(g["name_de"])
            g_i18n = i18n("gruppe." + kid + "." + g_slug + ".name")
            cards = ""
            for b in g["behandlungen"]:
                sub = BESCHREIBUNGEN.get(b["slug"], "")
                sub_short = sub.split(".")[0] + "." if sub else ""
                b_i18n = i18n("beh." + b["slug"] + ".name")
                # Im HTML steht der erste Satz, beim Umschalten kommt die volle
                # Beschreibung aus dem Katalog - dafuer gibt es keinen zweiten Schluessel.
                d_i18n = i18n("beh." + b["slug"] + ".desc") if sub_short else ""
                mehr = i18n("seite.allgemein.mehr_erfahren")
                cards += f'<a class="t-card" href="{b["slug"]}.html"><h3{b_i18n}>{h(b["name_de"])}</h3><p{d_i18n}>{h(sub_short)}</p><span class="link"{mehr}>Mehr erfahren</span></a>\n'
            groups += f"""
  <div class="kat-group" id="{g_slug}">
    <div class="group-head"><h2{g_i18n}>{h(g['name_de'])}</h2><span class="cat-count">{anzahl_badge(len(g['behandlungen']))}</span></div>
    <div class="grid-4">{cards}</div>
  </div>"""

        n_i18n = i18n("kat." + kid + ".name")
        intro_i18n = i18n("kat." + kid + ".intro")
        relpath = f"behandlungen/{kid}/index.html"
        kopf = head(
            f"{k['name_de']} in Istanbul | ETA",
            f"{k['name_de']}: {kat_teaser(kid)} Deutschsprachige Beratung, Behandlung in unserer Partnerklinik in Istanbul.",
            prefix, kanonisch(relpath),
            "meta.kat-" + kid + ".title", "meta.kat-" + kid + ".desc",
            jsonld=ld(
                ld_organisation(),
                ld_krumen([
                    ("Start", kanonisch("index.html")),
                    ("Behandlungen", kanonisch("behandlungen/index.html")),
                    (k["name_de"], kanonisch(relpath)),
                ]),
            ),
        )
        rumpf = f"""
<section class="page-band">
  <div class="crumbs"><a href="{prefix}behandlungen/index.html"{i18n('seite.allgemein.crumb.behandlungen')}>Behandlungen</a><span>/</span><span{n_i18n}>{h(k['name_de'])}</span></div>
  <h1{n_i18n}>{h(k['name_de'])}</h1>
  <p><span>{kat_count(k)}</span> <span{i18n('seite.kategorie.anzahl_behandlungen')}>Behandlungen.</span> <span{intro_i18n}>{h(kat_intro(kid))}</span></p>
  <a class="link" href="{prefix}behandlungen/index.html"{i18n('seite.kategorie.katalog_link')}>Zum gesamten Behandlungskatalog</a>
</section>
<div class="section kat-groups">{groups}
</div>
""" + cta_band(
            "Unsicher, welche Behandlung passt?",
            "Wir beraten Sie unverbindlich und auf Deutsch.",
            "seite.allgemein.cta.unsicher",
        )
        seite(relpath, kopf, header_nav(prefix, kid), rumpf, prefix)


# ------------------------------------------------------------- Detailseiten
def detail_fakten(slug, lokal=False):
    """Kasten «Auf einen Blick». Jede Zeile nur, wenn ein echter Wert da ist.

    Vorher standen hier auf allen 101 Seiten «[X TAGE]», «[X STUNDEN]» und
    «[AUF ANFRAGE]». Die Werte kommen jetzt aus data/behandlungsdaten.json;
    was dort leer ist, erscheint gar nicht (Befund inhalt B1, gestaltung B1).

    Im Kasten stehen nur die kurzen Angaben. Ergebnis, Haltbarkeit und Zahl
    der Sitzungen sind ganze Saetze und stehen deshalb im Fliesstext
    (Abschnitt «Ergebnis»), nicht in einer zweispaltigen Faktenzeile.
    """
    d = BEHANDLUNGSDATEN.get(slug, {})

    def dk(*pfad):
        return dkey("behandlungsdaten", "behandlungen", slug, *pfad)

    # Bei den Behandlungen, die Riverside auch in der Schweiz anbietet, stand
    # im Kasten «kein Aufenthalt in Istanbul noetig» und zwei Zeilen darunter
    # «Klinik: Unsere Partnerklinik, Istanbul». Das widersprach sich.
    klinik_wert, klinik_key = (
        ("Partnerklinik Istanbul oder Riverside Beauty, St. Margrethen",
         "seite.behandlung.fakten.klinik.wert_lokal")
        if lokal else
        ("Unsere Partnerklinik, Istanbul", "seite.behandlung.fakten.klinik.wert")
    )
    zeilen = [
        fakt("Aufenthalt in Istanbul", aufenthalt_kurz(d.get("aufenthalt_tage")),
             "seite.behandlung.fakten.aufenthalt.label",
             dkey_abgeleitet(aufenthalt_kurz, "behandlungsdaten", "behandlungen", slug, "aufenthalt_tage")),
        fakt("Dauer der Behandlung", d.get("dauer_eingriff"), "seite.behandlung.fakten.dauer.label",
             dk("dauer_eingriff")),
        fakt("Betäubung", d.get("betaeubung"), "seite.behandlung.fakten.betaeubung.label",
             dk("betaeubung")),
        fakt("Wieder alltagsfähig", d.get("ausfallzeit_alltag"), "seite.behandlung.fakten.ausfallzeit.label",
             dk("ausfallzeit_alltag")),
        fakt("Wieder Sport", d.get("ausfallzeit_sport"), "seite.behandlung.fakten.sport.label",
             dk("ausfallzeit_sport")),
        fakt("Klinik", klinik_wert, "seite.behandlung.fakten.klinik.label", klinik_key),
        fakt("Nachsorge", "Rheintal, Schweiz",
             "seite.behandlung.fakten.nachsorge.label", "seite.behandlung.fakten.nachsorge.wert"),
    ]
    # Die Preisbox entfaellt vollstaendig, solange kein Preis hinterlegt ist.
    # Eine fehlende Box ist neutral, «[AUF ANFRAGE]» ist ein Schaden.
    preis = echt(d.get("preis_ab"))
    if preis:
        waehrung = echt(d.get("waehrung")) or "CHF"
        bis = echt(d.get("preis_bis"))
        betrag = f"ab {waehrung} {preis}" + (f" bis {waehrung} {bis}" if bis else "")
        zeilen.append(
            f'<div class="price-box"><span{i18n("seite.behandlung.preis.label")}>PREIS</span>'
            f'<strong>{h(betrag)}</strong>'
            f'<em{i18n("seite.behandlung.preis.hinweis")}>Fixpreis inkl. Transfer und Hotel</em></div>'
        )
    else:
        # Kein Preis, aber die Grundlage, nach der er sich richtet. Das ist die
        # Angabe, mit der ein Interessent zwei Angebote vergleichen kann —
        # «je Graft» oder «je Zahn» sagt mehr als eine Zahl ohne Bezug.
        # Der Schluessel wird auch dann als «abgeleitet» gemeldet, wenn von dem
        # Wert nichts uebrig bleibt: so raeumt build_sprachdateien() die
        # Redaktionsnotiz auch aus den Sprachdateien.
        basis_key = dkey_abgeleitet(ohne_redaktionsnotiz, "behandlungsdaten",
                                    "behandlungen", slug, "preis_basis")
        basis = ohne_redaktionsnotiz(d.get("preis_basis"))
        if basis:
            zeilen.append(
                f'<p class="small muted"><span{i18n("seite.behandlung.preis.basis.label")}>'
                f'Wonach sich der Preis richtet:</span> {span(basis, basis_key)}</p>'
            )
    return "\n      ".join(z for z in zeilen if z)


def risiko_block(slug, d, prefix):
    """Risiken, Grenzen und Ausschlussgruende — aus den Daten, nie erfunden.

    Voll ausgearbeitete Behandlungen haben eigene Risiken; die knappen bekommen
    den Text ihrer Behandlungsgruppe aus data/risiken-gruppen.json. Beide
    bekommen «wann zum Arzt» und «Grenzen des Verfahrens» aus der Gruppe, weil
    das in den Einzeleintraegen nicht doppelt steht (Befund inhalt B4).
    """
    gid = d.get("risiken_gruppe") or ""
    gruppe = RISIKEN_GRUPPEN.get(gid, {})

    def dk(*pfad):
        return dkey("behandlungsdaten", "behandlungen", slug, *pfad)

    def gk(*pfad):
        return dkey("risiken-gruppen", "gruppen", gid, *pfad)

    eigene = punkte([x for x in d.get("risiken", [])], key=dk("risiken"))
    teile = []
    if eigene:
        teile.append(eigene)
    elif gruppe:
        teile.append(absaetze(gruppe.get("einleitung"), key=gk("einleitung")))
        teile.append(block("Was häufig vorkommt", punkte(gruppe.get("haeufig"), key=gk("haeufig")),
                           "seite.behandlung.risiken.haeufig", "h3"))
        teile.append(block("Was selten vorkommt", punkte(gruppe.get("selten"), key=gk("selten")),
                           "seite.behandlung.risiken.selten", "h3"))
    teile.append(block("Wann diese Behandlung nicht in Frage kommt",
                       punkte(d.get("nicht_geeignet_fuer"), key=dk("nicht_geeignet_fuer")),
                       "seite.behandlung.risiken.nicht_geeignet", "h3"))
    teile.append(block("Wann Sie ärztliche Hilfe brauchen",
                       absaetze(gruppe.get("wann_zum_arzt"), key=gk("wann_zum_arzt")),
                       "seite.behandlung.risiken.zum_arzt", "h3"))
    teile.append(block("Was dieses Verfahren nicht kann",
                       absaetze(gruppe.get("grenzen"), key=gk("grenzen")),
                       "seite.behandlung.risiken.grenzen", "h3"))
    inhalt = "".join(t for t in teile if t)
    if not inhalt.strip():
        return ""
    hinweis = echt(RISIKEN.get("haftungshinweis"))
    if hinweis:
        inhalt += (f'\n    <div class="note-box"{i18n("seite.behandlung.risiken.haftung")}>'
                   f'{h(hinweis)}</div>')
    inhalt += (f'\n    <p class="small"><a class="link" href="{prefix}{SEITE_SCHIEFGEHT}"'
               f'{i18n("seite.behandlung.risiken.link")}>'
               f'Was gilt, wenn etwas nicht wie geplant läuft</a></p>')
    return block("Risiken und Grenzen", inhalt, "seite.behandlung.risiken.titel")


def faq_block(eintraege, titel, i18n_key, key_basis=""):
    """Behandlungseigene Fragen. Dieselbe Optik wie die allgemeine FAQ.

    key_basis ist der Schluessel der Frageliste in den Redaktionsdaten; jeder
    Eintrag bekommt key_basis.<index>.frage bzw. .antwort. Der Index zaehlt die
    Rohliste, damit eine unbeantwortete Frage die folgenden nicht verschiebt.
    """
    liste = ""
    paare = []
    for i, e in enumerate(eintraege or []):
        frage, antwort = echt(e.get("frage")), echt(e.get("antwort"))
        if not (frage and antwort):
            continue
        f_key = f"{key_basis}.{i}.frage" if key_basis else ""
        a_key = f"{key_basis}.{i}.antwort" if key_basis else ""
        liste += (f'<details{" open" if not paare else ""}>'
                  f'<summary{i18n(f_key)}>{h(frage)}</summary>'
                  f'<p{i18n(a_key)}>{h(antwort)}</p></details>')
        paare.append((frage, antwort))
    if not paare:
        return "", []
    return block(titel, f'<div class="faq-list wide">{liste}</div>', i18n_key), paare


# Welche Felder einer Behandlung in den Volltext einfliessen, in dem nach
# Fachbegriffen gesucht wird. Redaktionsnotizen und Steuerfelder bleiben
# draussen: «risiken_gruppe» ist ein Schluessel, kein Text, und
# «evidenz_hinweis» richtet sich an die Redaktion, nicht an den Besucher.
GLOSSAR_NICHT_DURCHSUCHEN = {
    "freigabe", "quelle", "stand", "evidenz_hinweis", "whatsapp_text",
    "verwandt", "risiken_gruppe", "waehrung",
}


def beh_volltext(slug):
    """Der Text, der auf dieser Behandlungsseite tatsaechlich steht.

    Grundlage fuer die Frage, welche Fachbegriffe die Seite erklaeren muss.
    Der Gruppen-Risikotext zaehlt mit, weil er mit ausgegeben wird — steht
    «Hyaluronidase» dort, muss das Wort auch dort erklaert sein.
    """
    stuecke = []

    def sammle(o):
        if isinstance(o, str):
            stuecke.append(o)
        elif isinstance(o, list):
            for x in o:
                sammle(x)
        elif isinstance(o, dict):
            for k, v in o.items():
                if k not in GLOSSAR_NICHT_DURCHSUCHEN:
                    sammle(v)

    d = BEHANDLUNGSDATEN.get(slug, {})
    sammle(d)
    sammle(RISIKEN_GRUPPEN.get(d.get("risiken_gruppe") or "", {}))
    stuecke.append(BESCHREIBUNGEN.get(slug, ""))
    if slug in SLUG_REGISTER:
        stuecke.append(SLUG_REGISTER[slug][1])
    return " ".join(stuecke)


def glossar_fuer(slug):
    """Die Fachbegriffe, die auf dieser Behandlungsseite vorkommen.

    Zwei Wege fuehren hinein: das Wort steht im Text der Seite, oder
    data/glossar.json ordnet den Begriff dieser Behandlung ausdruecklich zu.
    Der zweite Weg faengt die Faelle, in denen der Text das Wort umschreibt
    («Saphirklingen» statt «Saphir-FUE»).
    """
    text = beh_volltext(slug)
    return [(b, e) for b, e in GLOSSAR_SORTIERT
            if slug in e["behandlungen"] or e["muster"].search(text)]


def glossar_block(slug, prefix):
    """Kurzerklaerungen am Fuss der Behandlungsseite.

    Bewusst ein eigener Abschnitt und keine Einschuebe im Fliesstext: Die
    medizinischen Texte sind noch nicht fachlich freigegeben, und wer in
    fremde Saetze Klammern einbaut, veraendert sie. Ein Block laesst den Text
    unberuehrt, traegt eigene i18n-Schluessel und faellt weg, wenn die Seite
    keinen Fachbegriff enthaelt.
    """
    treffer = glossar_fuer(slug)
    if not treffer:
        return ""
    zeilen = "".join(
        f'<div class="glossar-zeile">'
        f'<dt><a class="link" href="{prefix}{SEITE_GLOSSAR}#{e["slug"]}"'
        f'{i18n(glossar_schluessel(e["slug"], "begriff"))}>{h(b)}</a></dt>'
        f'<dd{i18n(glossar_schluessel(e["slug"], "kurz"))}>{h(e["kurz"])}</dd>'
        f"</div>"
        for b, e in treffer
    )
    inhalt = (f'<dl class="glossar-liste">{zeilen}</dl>'
              f'<p class="small"><a class="link" href="{prefix}{SEITE_GLOSSAR}"'
              f'{i18n("seite.behandlung.glossar.link")}>Alle Fachbegriffe erklärt</a></p>')
    return block("Fachbegriffe auf dieser Seite", inhalt, "seite.behandlung.glossar.titel")


# --------------------------------------------------- Vergleich von Verfahren
# Etikett je Spalte der Gegenueberstellung. Drei davon gibt es im Kasten
# «Auf einen Blick» schon — ein Schluessel, ein Text.
VERGLEICH_ETIKETTEN = {
    "dauer_eingriff": ("Dauer der Behandlung", "seite.behandlung.fakten.dauer.label"),
    "betaeubung": ("Betäubung", "seite.behandlung.fakten.betaeubung.label"),
    "ausfallzeit_alltag": ("Wieder alltagsfähig", "seite.behandlung.fakten.ausfallzeit.label"),
    "haltbarkeit": ("Wie lange es hält", "seite.vergleich.haltbarkeit.label"),
    "sitzungen": ("Zahl der Sitzungen", "seite.vergleich.sitzungen.label"),
}


def vergleich_karte(slug, prefix, hervor=False):
    """Eine Behandlung in der Gegenueberstellung. Leere Felder fallen weg."""
    if slug not in SLUG_REGISTER:
        return ""
    kid, name = SLUG_REGISTER[slug]
    d = BEHANDLUNGSDATEN.get(slug, {})
    zeilen = "\n      ".join(z for z in (
        fakt(label, d.get(feld), key, dkey("behandlungsdaten", "behandlungen", slug, feld))
        for feld, (label, key) in VERGLEICH_ETIKETTEN.items()
    ) if z)
    kopf = (f'<h3{i18n("beh." + slug + ".name")}>{h(name)}</h3>' if hervor else
            f'<h3><a class="link" href="{prefix}behandlungen/{kid}/{slug}.html"'
            f'{i18n("beh." + slug + ".name")}>{h(name)}</a></h3>')
    marke = (f'<p class="small muted"{i18n("seite.vergleich.diese_seite")}>'
             f'Die Behandlung dieser Seite</p>') if hervor else ""
    if not zeilen:
        # Sechs der 19 verglichenen Behandlungen haben noch keine Sachangaben.
        # Statt einer leeren Karte steht dort der Satz, der auf der eigenen
        # Seite als Lead steht — derselbe Schluessel, keine neue Uebersetzung.
        beschr = echt(BESCHREIBUNGEN.get(slug))
        if beschr:
            zeilen = f'<p class="small"{i18n("beh." + slug + ".desc")}>{h(beschr)}</p>'
    return (f'<div class="card vergleich-karte{" vergleich-karte--hier" if hervor else ""}">'
            f"{kopf}{marke}{zeilen}</div>")


def vergleich_block(gid, prefix, hier_slug="", titel_stufe="h2"):
    """Die Gegenueberstellung einer Gruppe: Entscheidungshilfe plus Karten.

    Bewusst keine Tabelle. Von den 19 verglichenen Behandlungen haben 6 noch
    gar keine Sachangaben und «preis_ab» ist ueberall leer — eine Tabelle mit
    vier Spalten waere zur Haelfte leer, und die gefuellten Zellen sind ganze
    Saetze, die bei 320 px Breite in keine Spalte passen. Karten zeigen
    dasselbe, lassen leere Felder weg und brauchen kein Querscrollen.
    """
    g = VERGLEICH_GRUPPEN.get(gid)
    if not g:
        return ""
    titel = echt(g.get("titel"))
    hilfe = echt(g.get("entscheidungshilfe"))
    vslug = vergleich_slug(gid)
    karten = "".join(vergleich_karte(s, prefix, hervor=(s == hier_slug)) for s in g["behandlungen"])
    if not karten:
        return ""
    inhalt = ""
    if hilfe:
        inhalt += f'<p{i18n("beratung.vergleich." + vslug + ".hilfe")}>{h(hilfe)}</p>'
    inhalt += f'<div class="grid-3 vergleich-gitter">{karten}</div>'
    return block(titel or "Im Vergleich", inhalt,
                 "beratung.vergleich." + vslug + ".titel", titel_stufe)


def verwandt_block(d, prefix):
    """Verwandte Behandlungen. Heute gab es von einer Behandlung zur naechsten
    keinen Weg ausser ueber das Menue (Befund inhalt B5)."""
    karten = ""
    for slug in d.get("verwandt", []):
        if slug not in SLUG_REGISTER:
            continue
        kid, name = SLUG_REGISTER[slug]
        karten += (f'<a class="t-card" href="{prefix}behandlungen/{kid}/{slug}.html"'
                   f'><h3{i18n("beh." + slug + ".name")}>{h(name)}</h3>'
                   f'<span class="link"{i18n("seite.allgemein.mehr_erfahren")}>Mehr erfahren</span></a>')
    return block("Verwandte Behandlungen", f'<div class="grid-4">{karten}</div>' if karten else "",
                 "seite.behandlung.verwandt.titel")



# Der generische ETA-Ablauf stand bisher auf allen 101 Seiten wortgleich
# zwischen dem Interessenten und dem, was er wissen will (Befund inhalt B5).
# Er steht jetzt ganz unten, nach allem Behandlungsspezifischen.
def ablauf_generisch():
    return f"""
    <h2{i18n('seite.behandlung.ablauf.titel')}>So läuft Ihre Behandlung ab</h2>
    <ol class="ablauf-list">
      <li><h3{i18n('seite.behandlung.ablauf.1.titel')}>Beratung per WhatsApp oder Video</h3><p{i18n('seite.behandlung.ablauf.1.text')}>Sie schildern Ihren Wunsch, wir klären offene Fragen und holen die Einschätzung der Klinik ein.</p></li>
      <li><h3{i18n('seite.behandlung.ablauf.2.titel')}>Fixpreis-Angebot</h3><p{i18n('seite.behandlung.ablauf.2.text')}>Sie erhalten ein schriftliches Angebot der Klinik, inklusive Transfer und Hotel. Keine versteckten Kosten.</p></li>
      <li><h3{i18n('seite.behandlung.ablauf.3.titel')}>Reise nach Istanbul</h3><p{i18n('seite.behandlung.ablauf.3.text')}>Abholung am Flughafen, Voruntersuchung in der Klinik, Behandlung und Erholung.</p></li>
      <li><h3{i18n('seite.behandlung.ablauf.4.titel')}>Nachsorge zu Hause</h3><p{i18n('seite.behandlung.ablauf.4.text')}>Nachkontrolle im Rheintal bei unserem Partner Riverside Beauty, in Abstimmung mit der Klinik.</p></li>
    </ol>
    <p class="small"><a class="link" href="../../{SEITE_REISE}"{i18n('seite.behandlung.link.reise')}>Die Reise Tag für Tag</a> · <a class="link" href="../../{SEITE_KOSTEN}"{i18n('seite.behandlung.link.kosten')}>Was es insgesamt kostet</a></p>"""


def detail_eigen(slug, b, prefix):
    """Alles, was nur zu dieser einen Behandlung gehoert.

    Reihenfolge nach Befund inhalt B5: fuer wen, was passiert, wie es ablaeuft,
    Ergebnis, Risiken, danach, eigene Fragen, verwandte Behandlungen. 28 der
    101 Behandlungen sind voll ausgearbeitet, 73 knapp — was fehlt, faellt weg,
    und der Gruppen-Risikotext sorgt dafuer, dass auch die knappen nicht leer
    aussehen.
    """
    d = BEHANDLUNGSDATEN.get(slug, {})
    t = d.get("text") or {}

    def dk(*pfad):
        return dkey("behandlungsdaten", "behandlungen", slug, *pfad)

    teile = []
    teile.append(block("Für wen diese Behandlung geeignet ist",
                       absaetze(t.get("fuer_wen"), key=dk("text", "fuer_wen")),
                       "seite.behandlung.fuer_wen.titel"))
    teile.append(block("Was bei der Behandlung passiert",
                       absaetze(t.get("was_passiert"), key=dk("text", "was_passiert")),
                       "seite.behandlung.was_passiert.titel"))
    teile.append(block("Der Eingriff Schritt für Schritt",
                       absaetze(t.get("ablauf"), key=dk("text", "ablauf")),
                       "seite.behandlung.eingriff.titel"))
    ergebnis = "".join([
        absaetze(d.get("ergebnis_sichtbar_nach"), key=dk("ergebnis_sichtbar_nach")),
        absaetze(d.get("haltbarkeit"), key=dk("haltbarkeit")),
        absaetze(d.get("sitzungen"), key=dk("sitzungen")),
    ])
    teile.append(block("Ergebnis: wann sichtbar, wie lange haltbar", ergebnis,
                       "seite.behandlung.ergebnis.titel"))
    teile.append(risiko_block(slug, d, prefix))
    danach = (absaetze(t.get("danach"), key=dk("text", "danach"))
              + absaetze(d.get("nachsorge"), key=dk("nachsorge")))
    teile.append(block("Nach der Behandlung", danach, "seite.behandlung.danach.titel"))
    # Ein Schluessel, ein Text: der Behandlungsname stuende sonst 28-mal
    # verschieden unter demselben i18n-Schluessel.
    fragen_html, paare = faq_block(d.get("faq"), "Häufige Fragen zu dieser Behandlung",
                                   "seite.behandlung.faq.titel", dk("faq"))
    teile.append(fragen_html)
    # Die Gegenueberstellung steht dort, wo jemand schwankt: auf der Seite
    # jeder beteiligten Behandlung, nicht nur auf der Beratungsseite.
    teile.append(vergleich_block(VERGLEICH_FUER_SLUG.get(slug, ""), prefix, hier_slug=slug))
    teile.append(glossar_block(slug, prefix))
    teile.append(verwandt_block(d, prefix))
    return "".join(x for x in teile if x), paare


def build_details():
    for k in kats():
        kid = k["id"]
        for g in k["gruppen"]:
            for b in g["behandlungen"]:
                slug = b["slug"]
                prefix = "../../"
                relpath = f"behandlungen/{kid}/{slug}.html"
                d = BEHANDLUNGSDATEN.get(slug, {})
                desc = BESCHREIBUNGEN.get(slug, "")
                lokal = ""
                if b.get("lokal_riverside"):
                    lokal = f'<div class="note-box"{i18n("seite.behandlung.lokal")}>Diese Behandlung bietet unser Nachsorge-Partner Riverside Beauty auch lokal in St. Margrethen an. Wir beraten Sie, was für Sie sinnvoller ist.</div>'
                # «evidenz_hinweis» ist trotz des Inhalts eine Notiz an die
                # Redaktion («Vor der Veroeffentlichung fachlich pruefen
                # lassen …») und gehoert deshalb nicht ins HTML. Was der
                # Besucher davon wissen muss, steht bereits in der
                # entschaerften Beschreibung und im eigenen FAQ-Eintrag
                # «Ist die Wirkung belegt?» (Befund inhalt B13).
                # Nur eine Kachel, und nur wenn es wirklich ein Bild gibt.
                # Die beiden Kacheln «[VORHER]» / «[NACHHER]» fallen ersatzlos weg.
                bild_pfad = BEHANDLUNG_BILDER.get(slug)
                galerie = ""
                if bild_pfad:
                    quelle = bild_pfad.replace("assets/img/", "", 1)
                    galerie = (
                        '<figure class="detail-gallery">'
                        + bild(prefix, quelle, b["name_de"],
                               "(min-width: 1100px) 480px, (min-width: 700px) 46vw, 92vw",
                               klasse="detail-bild", eager=True, alt_i18n="beh." + slug + ".name")
                        # Alle 101 Behandlungsbilder sind computererzeugt. Der
                        # Hinweis steht bewusst am Bild und nicht nur im
                        # Impressum (data/recht.json -> impressum -> bilder;
                        # irrefuehrende Werbung, UWG Art. 3 Abs. 1 lit. b).
                        + f'<figcaption class="small muted bild-hinweis"'
                          f'{i18n("seite.behandlung.bild.symbolbild")}>Symbolbild</figcaption>'
                        + "</figure>"
                    )
                eigen, faq_paare = detail_eigen(slug, b, prefix)
                wa_kontext = echt(d.get("whatsapp_text")) or ""
                wa_kontext_key = (
                    "daten.behandlungsdaten.behandlungen." + slug + ".whatsapp_text"
                    if wa_kontext else ""
                )
                b_i18n = i18n("beh." + slug + ".name")
                d_i18n = i18n("beh." + slug + ".desc") if desc else ""
                ph_attr = i18n_attr("placeholder:seite.behandlung.formular.nachricht.ph." + slug)
                # Zwei Typen: MedicalProcedure beschreibt den Eingriff,
                # TherapeuticProcedure erlaubt zusaetzlich contraindication.
                # adverseOutcome bleibt draussen: schema.org erwartet dort eine
                # MedicalEntity, keinen Fliesstext (Abweichung, siehe Bericht).
                verfahren = {
                    "@context": "https://schema.org",
                    "@type": ["MedicalProcedure", "TherapeuticProcedure"],
                    "name": b["name_de"],
                    "url": kanonisch(relpath),
                    "category": k["name_de"],
                    "provider": {"@id": f"{BASE_URL}/#organisation"},
                }
                if desc:
                    verfahren["description"] = desc
                t_ = d.get("text") or {}
                # Nur ausgeben, was auf dieser Seite auch sichtbar steht.
                for feld, wert_ in (
                    ("howPerformed", t_.get("was_passiert")),
                    ("preparation", t_.get("ablauf")),
                    ("followup", d.get("nachsorge")),
                ):
                    if echt(wert_):
                        verfahren[feld] = echt(wert_)
                gegenanzeigen = [echt(x) for x in d.get("nicht_geeignet_fuer", []) if echt(x)]
                if gegenanzeigen:
                    verfahren["contraindication"] = gegenanzeigen
                kopf = head(
                    f"{b['name_de']} in Istanbul | ETA",
                    f"{desc} Beratung auf Deutsch, Klinik in Istanbul.",
                    prefix, kanonisch(relpath),
                    "meta.beh-" + slug + ".title", "meta.beh-" + slug + ".desc",
                    jsonld=ld(
                        ld_organisation(),
                        verfahren,
                        ld_faq_paare(faq_paare) if faq_paare else None,
                        ld_krumen([
                            ("Start", kanonisch("index.html")),
                            ("Behandlungen", kanonisch("behandlungen/index.html")),
                            (k["name_de"], kanonisch(f"behandlungen/{kid}/index.html")),
                            (b["name_de"], kanonisch(relpath)),
                        ]),
                    ),
                    vorladen=bild_vorladen(prefix, quelle, "(min-width: 1100px) 480px, 92vw") if bild_pfad else "",
                )
                rumpf = f"""
<section class="page-band slim">
  <div class="crumbs"><a href="{prefix}behandlungen/index.html"{i18n('seite.allgemein.crumb.behandlungen')}>Behandlungen</a><span>/</span><a href="index.html"{i18n('kat.' + kid + '.name')}>{h(k['name_de'])}</a><span>/</span><span{b_i18n}>{h(b['name_de'])}</span></div>
</section>
<section class="section detail-layout">
  <div class="detail-main">
    <h1{b_i18n}>{h(b['name_de'])}</h1>
    {galerie}
    <p class="lead"{d_i18n}>{h(desc)}</p>
    <p{i18n('seite.behandlung.hinweis')}>Ob und wie diese Behandlung für Sie geeignet ist, klären Sie im persönlichen Beratungsgespräch mit der behandelnden Fachärztin oder dem Facharzt unserer Partnerklinik, auf Deutsch und ohne Zeitdruck.</p>
    {lokal}{eigen}
{ablauf_generisch()}
  </div>
  <aside class="detail-aside">
    <div class="card facts">
      <h2 class="serif"{i18n('seite.behandlung.fakten.titel')}>Auf einen Blick</h2>
      {detail_fakten(slug, bool(b.get("lokal_riverside")))}
      {wa_button('Per WhatsApp schreiben', 18, 'btn btn-gold', 'seite.allgemein.cta.anfragen', wa_kontext, wa_kontext_key)}
      <form class="mini-form" id="anfrage-form" method="post">
        <input type="hidden" name="behandlung" value="{h(b['name_de'])}">
        {pflicht_hinweis()}
        <label for="mf-name"><span{i18n('seite.behandlung.formular.name.label')}>Name</span>{PFLICHT_STERN}<input id="mf-name" type="text" name="name" required aria-required="true" autocomplete="name"></label>
        <label for="mf-email"><span{i18n('seite.behandlung.formular.email.label')}>E-Mail</span>{PFLICHT_STERN}<input id="mf-email" type="email" name="email" required aria-required="true" autocomplete="email"></label>
        <label for="mf-telefon"><span{i18n('seite.behandlung.formular.telefon.label')}>Telefon</span>{PFLICHT_STERN}<input id="mf-telefon" type="tel" name="telefon" required aria-required="true" autocomplete="tel"></label>
        <label for="mf-nachricht"><span{i18n('seite.behandlung.formular.nachricht.label')}>Ihre Nachricht (optional)</span><textarea id="mf-nachricht" name="nachricht" rows="3" placeholder="Frage zu {h(b['name_de'])}"{ph_attr}></textarea></label>
        {HONEYPOT}
        <label class="checkbox" for="mf-einwilligung"><input id="mf-einwilligung" type="checkbox" name="einwilligung" value="ja" required aria-required="true"><span><span{i18n('seite.allgemein.dsgvo.teil1')}>Ich habe die</span> <a href="{prefix}datenschutz.html"{i18n('seite.allgemein.dsgvo.link')}>Datenschutzerklärung</a> <span{i18n('seite.behandlung.formular.dsgvo.teil2')}>gelesen und bin mit der Verarbeitung meiner Angaben einverstanden.</span></span></label>
        <input type="hidden" name="einwilligung_version" value="{EINWILLIGUNG_VERSION}">
        <button type="submit" class="btn btn-gold"{i18n('seite.allgemein.formular.senden')}>Anfrage senden</button>
        {FORM_STATUS}
      </form>
    </div>
  </aside>
</section>
""" + cta_band(
                    "Noch Fragen zu dieser Behandlung?",
                    "Wir antworten persönlich, in der Regel noch am selben Tag.",
                    "seite.behandlung.cta", "Per WhatsApp fragen", "seite.behandlung.cta.knopf",
                    kontext=wa_kontext,
                    kontext_key=wa_kontext_key,
                )
                seite(relpath, kopf, header_nav(prefix, kid), rumpf, prefix)


# ---------------------------------------------------------------- Unterseiten
def klinik_punkte():
    """Belegte Klinikangaben als Liste. Ohne Beleg keine Zeile.

    Vorher stand hier «[KLINIK-FAKTEN: Fachbereiche, Kapazität, Zertifizierungen]».
    Aerztenamen und nicht belegte Zertifikate bleiben bewusst draussen — sie
    stehen in data/klinik.json ausdruecklich unter «offen» bzw. «nicht_belegt».
    """
    punkte = [
        f'<li{i18n("seite.partnerklinik.klinik.punkt.1")}>Deutschsprachige Betreuung direkt in der Klinik</li>',
        f'<li{i18n("seite.partnerklinik.klinik.punkt.2")}>Eigene Transfer- und Hotel-Organisation</li>',
    ]
    for i, f_ in enumerate(KLINIK.get("fakten_belegt", [])):
        label, wert_ = echt(f_.get("label")), echt(f_.get("wert"))
        if label and wert_:
            punkte.append(f'<li>{span(label, dkey("klinik", "fakten_belegt", i, "label"))}: '
                          f'{span(wert_, dkey("klinik", "fakten_belegt", i, "wert"))}</li>')
    fach = [f'<span{i18n(dkey("klinik", "fachbereiche", i))}>{h(x)}</span>'
            for i, x in enumerate(KLINIK.get("fachbereiche", [])) if echt(x)]
    if fach:
        punkte.append(f'<li><span{i18n("seite.partnerklinik.klinik.fachbereiche")}>Fachbereiche:</span> '
                      f'{", ".join(fach)}</li>')
    return "\n      ".join(punkte)


def abgrenzung_satz():
    """Wer haftet wofuer. Steht als Datensatz in data/klinik.json -> abgrenzung."""
    text = echt((KLINIK.get("abgrenzung") or {}).get("text"))
    if not text:
        return ""
    return (f'<div class="note-box">{span(text, dkey("klinik", "abgrenzung", "text"))} '
            f'<a class="link" href="{SEITE_SCHIEFGEHT}"{i18n("seite.behandlung.risiken.link")}>'
            f'Was gilt, wenn etwas nicht wie geplant läuft</a></div>')


def klinik_adresse():
    """Anschrift der Partnerklinik. Erst damit ist sie nachpruefbar."""
    a = KLINIK.get("adresse", {})
    ort_zeile = " ".join(x for x in [
        h(echt(a.get("plz"))) if echt(a.get("plz")) else "",
        span(echt(a["ort"]), dkey("klinik", "adresse", "ort")) if echt(a.get("ort")) else "",
    ] if x)
    zeilen = [
        span(echt(KLINIK["name"]), dkey("klinik", "name")) if echt(KLINIK.get("name")) else "",
        span(echt(a["strasse"]), dkey("klinik", "adresse", "strasse")) if echt(a.get("strasse")) else "",
        ort_zeile,
        span(echt(a["land"]), dkey("klinik", "adresse", "land")) if echt(a.get("land")) else "",
    ]
    zeilen = [z for z in zeilen if z]
    if not zeilen:
        return ""
    url = echt(KLINIK.get("url"))
    link = (f'<p class="small"><a class="link" href="{h(url)}" rel="noopener" target="_blank"'
            f'{i18n("seite.partnerklinik.klinik.website")}>'
            f'Website der Klinik</a></p>') if url else ""
    return f'<address class="klinik-adresse">{"<br>".join(zeilen)}</address>{link}'


def klinik_zertifikate():
    """Nur Zertifikate aus «belegt» und nur mit Urkundennummer.

    «nicht_belegt» ist eine Warnliste (darunter eine JCI-Akkreditierung, die
    die Klinik selbst nicht behauptet) und darf nirgends ins HTML. Heute
    erfuellt kein Eintrag die Bedingung — also erscheint der Abschnitt nicht.
    """
    zeilen = []
    for z in KLINIK.get("zertifizierungen", {}).get("belegt", []):
        nummer = echt(z.get("nummer"))
        name = echt(z.get("name_de")) or echt(z.get("name"))
        if not (nummer and name):
            continue
        aussteller = echt(z.get("aussteller"))
        text = name + (f", {aussteller}" if aussteller else "") + f" (Nr. {nummer})"
        zeilen.append(text)
    return punkte(zeilen, "check-list")


def klinik_aerzte():
    """Nur Personen mit schriftlicher Einwilligung zur Namensnennung.

    Die Liste in data/klinik.json ist ein Abzug der oeffentlichen Klinikseite
    und eine Beschaffungshilfe, keine Veroeffentlichungsliste. Heute steht bei
    allen 18 Eintraegen «einwilligung»: false.
    """
    liste = (KLINIK.get("aerzte") or {}).get("liste", [])
    frei = [x for x in liste if x.get("einwilligung") is True and echt(x.get("name"))]
    if not frei:
        return ""
    karten = "".join(
        f'<div class="card"><h3 class="serif">{h(echt(x["name"]))}</h3>'
        + absaetze(x.get("fachgebiet"), "small") + "</div>"
        for x in frei
    )
    return f'<div class="grid-3">{karten}</div>'


def ld_klinik():
    """MedicalClinic — nur echte Werte. Keine erfundene aggregateRating:
    acht Trustpilot-Bewertungen stehen in data/klinik.json ausdruecklich auf
    «verwenden: false»."""
    name = echt(KLINIK.get("name"))
    if not name:
        return None
    a = KLINIK.get("adresse", {})
    klinik = {
        "@context": "https://schema.org",
        "@type": "MedicalClinic",
        "name": name,
        "medicalSpecialty": [x for x in KLINIK.get("fachbereiche", []) if echt(x)] or None,
    }
    if echt(KLINIK.get("url")):
        klinik["url"] = echt(KLINIK["url"])
    if echt(KLINIK.get("kontakt", {}).get("telefon")):
        klinik["telephone"] = echt(KLINIK["kontakt"]["telefon"])
    adresse = {"@type": "PostalAddress"}
    for feld, schluessel in (("streetAddress", "strasse"), ("postalCode", "plz"),
                             ("addressLocality", "ort"), ("addressCountry", "land_code")):
        if echt(a.get(schluessel)):
            adresse[feld] = echt(a[schluessel])
    if len(adresse) > 1:
        klinik["address"] = adresse
    return {k: v for k, v in klinik.items() if v}


def build_partnerklinik():
    prefix = ""
    name = echt(KLINIK.get("name"))
    # Der 360-Grad-Rundgang bekommt nur dann einen Knopf, wenn die Adresse
    # geprueft ist (klinik.json -> rundgang_360.geprueft). Sonst gar keiner:
    # ein Knopf auf href="#" ist schlechter als kein Knopf.
    rundgang = KLINIK.get("rundgang_360", {})
    rundgang_knopf = ""
    if rundgang.get("geprueft") and echt(rundgang.get("url")):
        rundgang_knopf = (
            f'<a href="{h(rundgang["url"])}" class="btn btn-outline" rel="noopener" target="_blank"'
            f'{i18n("seite.partnerklinik.klinik.rundgang")}>360°-Rundgang ansehen</a>'
        )
    klinik_satz = ""
    if name:
        ort = echt(KLINIK.get("adresse", {}).get("ort"))
        # Der Ortsname bleibt als Eigenname unuebersetzt, wenn er nicht aus den
        # Daten kommt — «Istanbul» heisst in allen vier Sprachen so.
        ort_html = span(ort, dkey("klinik", "adresse", "ort")) if ort else "Istanbul"
        klinik_satz = (
            f'<p class="small muted">'
            f'<span{i18n("seite.partnerklinik.klinik.satz.vor")}>Unsere Partnerklinik ist die</span> '
            f'<strong{i18n(dkey("klinik", "name"))}>{h(name)}</strong> '
            f'<span{i18n("seite.partnerklinik.klinik.satz.in")}>in</span> {ort_html}. '
            f'<span{i18n("seite.partnerklinik.klinik.satz.nach")}>ETA vermittelt die Behandlung dort '
            f'und erbringt selbst keine medizinischen Leistungen.</span></p>'
        )
    kopf = head(
        "Ablauf & Partnerklinik | ETA",
        "So begleitet ETA Sie von der Anfrage bis zur Nachkontrolle, in unserer Partnerklinik in Istanbul.",
        prefix, kanonisch("partnerklinik.html"), "meta.partnerklinik.title", "meta.partnerklinik.desc",
        jsonld=ld(
            ld_organisation(),
            ld_klinik(),
            ld_krumen([("Start", kanonisch("index.html")), ("Ablauf & Partnerklinik", kanonisch("partnerklinik.html"))]),
        ),
        vorladen=bild_vorladen(prefix, "hero-b.jpg", "100vw"),
    )
    rumpf = f"""
<section class="hero hero-sub">
  {bild(prefix, "hero-b.jpg", "", "100vw", klasse="hero-media", eager=True)}
  <div class="hero-overlay"></div>
  <div class="hero-content">
    <div class="eyebrow"{i18n('seite.partnerklinik.hero.eyebrow')}>Ihre Reise</div>
    <h1{i18n('seite.partnerklinik.hero.titel')}>Ablauf &amp; Partnerklinik</h1>
    <p{i18n('seite.partnerklinik.hero.text')}>Vom ersten Gespräch bis zur Nachkontrolle: So begleiten wir Sie, und hier werden Sie behandelt.</p>
  </div>
</section>

<section class="section" id="ablauf">
  <h2{i18n('seite.partnerklinik.ablauf.titel')}>So begleiten wir Sie</h2>
  <div class="grid-4 steps">
    <div class="card step"><div class="step-nr">01</div><h3{i18n('seite.partnerklinik.ablauf.1.titel')}>Anfrage &amp; Beratung</h3><p{i18n('seite.partnerklinik.ablauf.1.text')}>Per WhatsApp oder Formular. Wir besprechen Ihren Wunsch auf Deutsch und holen die Einschätzung der Klinik ein.</p></div>
    <div class="card step"><div class="step-nr">02</div><h3{i18n('seite.partnerklinik.ablauf.2.titel')}>Angebot &amp; Termin</h3><p{i18n('seite.partnerklinik.ablauf.2.text')}>Schriftliches Fixpreis-Angebot inkl. Transfer und Hotel. Mit der Anzahlung ist Ihr Termin gesichert.</p></div>
    <div class="card step"><div class="step-nr">03</div><h3{i18n('seite.partnerklinik.ablauf.3.titel')}>Istanbul</h3><p{i18n('seite.partnerklinik.ablauf.3.text')}>Abholung am Flughafen, Voruntersuchung, Behandlung und Erholung, alles durch die Klinik organisiert.</p></div>
    <div class="card step"><div class="step-nr">04</div><h3{i18n('seite.partnerklinik.ablauf.4.titel')}>Zurück zu Hause</h3><p{i18n('seite.partnerklinik.ablauf.4.text')}>Nachkontrolle im Rheintal bei Riverside Beauty, in direkter Abstimmung mit der Klinik.</p></div>
  </div>
  <p class="small"><a class="link" href="{SEITE_REISE}"{i18n('seite.partnerklinik.link.reise')}>Die Reise Tag für Tag</a> · <a class="link" href="{SEITE_KOSTEN}"{i18n('seite.partnerklinik.link.kosten')}>Was es insgesamt kostet</a> · <a class="link" href="{SEITE_SCHIEFGEHT}"{i18n('seite.partnerklinik.link.schiefgeht')}>Wenn etwas nicht wie geplant läuft</a></p>
</section>

<section class="section section-white klinik-layout">
  <div class="klinik-text">
    <div class="eyebrow gold"{i18n('seite.partnerklinik.klinik.eyebrow')}>Unsere Partnerklinik</div>
    <h2{i18n('seite.partnerklinik.klinik.titel')}>Unsere Partnerklinik in Istanbul</h2>
    <p{i18n('seite.partnerklinik.klinik.text')}>Ein medizinisches Zentrum mit eigenen Fachbereichen für plastische Chirurgie, Haartransplantation, Zahnmedizin und medizinische Ästhetik. Wir haben die Klinik persönlich besucht und arbeiten fest mit ihr zusammen, statt Anfragen an wechselnde Anbieter zu vermitteln.</p>
    {klinik_satz}
    <ul class="check-list">
      {klinik_punkte()}
    </ul>
    {klinik_adresse()}
    {block("Zertifikate und Bewilligungen", klinik_zertifikate(), "seite.partnerklinik.zertifikate", "h3")}
    {block("Die Ärztinnen und Ärzte", klinik_aerzte(), "seite.partnerklinik.aerzte", "h3")}
    {abgrenzung_satz()}
    <div class="btn-row">
      {rundgang_knopf}
      {wa_button('Fragen zur Klinik per WhatsApp', 18, 'btn btn-gold', 'seite.partnerklinik.klinik.cta')}
    </div>
  </div>
</section>
""" + cta_band(
        "Bereit für den ersten Schritt?",
        "Unverbindlich, diskret und auf Deutsch.",
        "seite.partnerklinik.cta",
    )
    seite("partnerklinik.html", kopf, header_nav(prefix, "partnerklinik"), rumpf, prefix)


def anzahlung_satz():
    """Die Anzahlung stand dreimal als «[BETRAG]» im Erzeugnis. Solange der
    Betrag nicht feststeht, wird er nicht genannt — der Rest des Satzes bleibt.

    Dieselbe Entschaerfung traf «[ANBIETER]» in den Finanzierungstexten. In
    data/i18n/seiten-*.json steht unter den alten Schluesseln aber weiter die
    Fassung mit Klammer-Platzhalter, und build_sprachdateien() haelt jeden Wert
    mit Klammer zurueck — der Schluessel fehlte damit in de.json. Deshalb
    tragen die vier betroffenen Stellen jetzt eigene Schluessel:
        seite.index.fin.2.text.ohne_anbieter
        seite.finanzierung.2.text.ohne_anbieter
        seite.finanzierung.hinweis.ohne_betrag
        seite.kontakt.formular.hinweis.ohne_betrag
    Die alten vier Schluessel sind damit unbenutzt und koennen aus allen vier
    Sprachdateien verschwinden, sobald en, tr und ar nachgezogen sind.
    """
    return (
        "Termine werden mit einer Anzahlung fixiert und können bis 72 Stunden "
        "vorher kostenlos verschoben werden."
    )


def build_finanzierung():
    prefix = ""
    kopf = head(
        "Finanzierung | ETA",
        "Drei Wege zu Ihrem Wunschtermin: 3 Raten ohne Zins, Ratenkauf mit Laufzeit oder Ansparmodell.",
        prefix, kanonisch("finanzierung.html"), "meta.finanzierung.title", "meta.finanzierung.desc",
        jsonld=ld(
            ld_organisation(),
            ld_krumen([("Start", kanonisch("index.html")), ("Finanzierung", kanonisch("finanzierung.html"))]),
        ),
    )
    rumpf = f"""
<section class="page-band">
  <div class="crumbs"><a href="index.html"{i18n('seite.allgemein.crumb.start')}>Start</a><span>/</span><span{i18n('nav.finanzierung')}>Finanzierung</span></div>
  <h1{i18n('seite.finanzierung.titel')}>Finanzierung</h1>
  <p{i18n('seite.finanzierung.text')}>Ihr Wunschtermin soll nicht am Zeitpunkt scheitern. Drei Modelle stehen zur Auswahl, welches passt, klären wir gemeinsam im Beratungsgespräch.</p>
</section>
<section class="section">
  <h2{i18n('seite.finanzierung.modelle.titel')}>Die drei Modelle</h2>
  <div class="grid-3">
    <div class="card"><h3 class="serif"{i18n('seite.finanzierung.1.titel')}>3 Raten, 0 % Zins</h3><p{i18n('seite.finanzierung.1.text')}>Der Behandlungspreis in drei Teilzahlungen, zinsfrei mit fixer Bearbeitungsgebühr. Die erste Rate sichert Ihren Termin.</p></div>
    <div class="card"><h3 class="serif"{i18n('seite.finanzierung.2.titel')}>Ratenkauf mit Laufzeit</h3><p{i18n('seite.finanzierung.2.text.ohne_anbieter')}>Flexible Laufzeiten über unseren Zahlungspartner. Die Abwicklung läuft direkt online, die Konditionen sehen Sie vor Abschluss transparent.</p></div>
    <div class="card"><h3 class="serif"{i18n('seite.finanzierung.3.titel')}>Ansparmodell</h3><p{i18n('seite.finanzierung.3.text')}>Sie sparen in Ihrem Tempo mit regelmässigen Teilzahlungen an. Sobald der Betrag erreicht ist, steht Ihr Termin fest.</p></div>
  </div>
  <div class="note-box"{i18n('seite.finanzierung.hinweis.ohne_betrag')}>Zahlungsarten: Twint, Banküberweisung, PayPal. {anzahlung_satz()} Alle Konditionen erhalten Sie schriftlich mit Ihrem Angebot.</div>
</section>
""" + cta_band(
        "Fragen zur Finanzierung?",
        "Wir rechnen Ihnen Ihr Modell unverbindlich durch.",
        "seite.finanzierung.cta",
    )
    seite("finanzierung.html", kopf, header_nav(prefix, "finanzierung"), rumpf, prefix)


# Die Seite «Vorher / Nachher» wird bewusst nicht mehr erzeugt: sie bestand aus
# neun leeren Kacheln. Eine leere Beweisseite ist ein negativer Beweis
# (Befund gestaltung B1, Entscheidung des Auftraggebers). vercel.json leitet
# /vorher-nachher.html auf den Katalog um, damit alte Verweise nicht ins Leere
# laufen. Sobald echte Bilder vorliegen, kommt die Seite zurueck.


def build_faq():
    prefix = ""
    # Neun weitere Fragen aus data/seiteninhalte.json -> reise_faq: Visum,
    # Flugtauglichkeit, Medikamente, Terminverschiebung, Begleitperson,
    # Krankenkasse, Komplikationen zu Hause, Sprache, Zahlung. Keine davon war
    # bisher beantwortet (Befund inhalt B15). Fragen ohne Antwort fallen weg.
    reise = SEITENINHALTE.get("reise_faq") or {}
    reise_html, reise_paare = faq_block(
        reise.get("fragen"), echt(reise.get("titel")) or "Fragen zur Reise",
        "seite.gutzuwissen.reise.titel",
        dkey("seiteninhalte", "reise_faq", "fragen"),
    )
    kopf = head(
        "Gut zu wissen | ETA",
        "Häufige Fragen zu Ablauf, Reise, Begleitung, Sprache, Visum, Versicherung und Nachsorge.",
        prefix, kanonisch("gut-zu-wissen.html"), "meta.gutzuwissen.title", "meta.gutzuwissen.desc",
        jsonld=ld(
            ld_organisation(),
            ld_faq(FAQ),
            ld_faq_paare(reise_paare) if reise_paare else None,
            ld_krumen([("Start", kanonisch("index.html")), ("Gut zu wissen", kanonisch("gut-zu-wissen.html"))]),
        ),
    )
    rumpf = f"""
<section class="page-band">
  <div class="crumbs"><a href="index.html"{i18n('seite.allgemein.crumb.start')}>Start</a><span>/</span><span{i18n('seite.gutzuwissen.crumb')}>Gut zu wissen</span></div>
  <h1{i18n('seite.gutzuwissen.titel')}>Gut zu wissen</h1>
  <p{i18n('seite.gutzuwissen.text')}>Die häufigsten Fragen unserer Kundinnen und Kunden. Ihre Frage fehlt? Schreiben Sie uns per WhatsApp.</p>
</section>
<section class="section">
  <div class="faq-list wide">
    {faq_html(FAQ)}
  </div>
{reise_html}
  <p class="small"><a class="link" href="{SEITE_REISE}"{i18n('seite.gutzuwissen.link.reise')}>Ihre Reise, Tag für Tag</a> · <a class="link" href="{SEITE_KOSTEN}"{i18n('seite.gutzuwissen.link.kosten')}>Was es insgesamt kostet</a> · <a class="link" href="{SEITE_SCHIEFGEHT}"{i18n('seite.gutzuwissen.link.schiefgeht')}>Wenn etwas nicht wie geplant läuft</a></p>
</section>
""" + cta_band(
        "Ihre Frage war nicht dabei?",
        "Wir antworten persönlich, in der Regel noch am selben Tag.",
        "seite.gutzuwissen.cta",
    )
    seite("gut-zu-wissen.html", kopf, header_nav(prefix, "wissen"), rumpf, prefix)


def kontaktwege_block(prefix):
    """Die Wege, die es wirklich gibt — mit tel: und mailto:.

    Auf 116 Seiten gab es null tel:- und null mailto:-Links; Telefonnummer und
    E-Mail standen nur als Fliesstext (Befund inhalt B6). Kanaele ohne Ziel
    (Telefonnummer noch nicht bestaetigt, Terminbuchung noch nicht umgesetzt)
    erscheinen gar nicht — ein angekuendigter Weg, den es nicht gibt, ist
    schlechter als keiner.
    """
    kw = SEITENINHALTE.get("kontaktwege") or {}
    karten = ""
    # Die Reihenfolge auf der Seite richtet sich nach «rang», die Schluessel
    # nach der Stelle in data/seiteninhalte.json — deshalb die Nummer vorher.
    for nr, kanal in sorted(enumerate(kw.get("kanaele", [])), key=lambda p: p[1].get("rang", 99)):
        kb = dkey("seiteninhalte", "kontaktwege", "kanaele", nr)
        typ, label = kanal.get("typ"), echt(kanal.get("label"))
        if not label:
            continue
        if typ == "formular":
            ziel = "#anfrage-form"
        elif typ == "whatsapp":
            ziel = wa_link(echt((kw.get("whatsapp") or {}).get("text_allgemein")) or "")
        elif typ == "tel" and echt(kanal.get("nummer")):
            ziel = "tel:" + re.sub(r"[^+0-9]", "", kanal["nummer"])
        elif typ == "mailto" and echt(kanal.get("adresse")):
            ziel = "mailto:" + echt(kanal["adresse"])
        elif typ == "termin" and echt(kanal.get("ziel")):
            ziel = echt(kanal["ziel"])
        else:
            continue
        extern = ' target="_blank" rel="noopener"' if ziel.startswith("http") else ""
        text = absaetze(kanal.get("text"), "small", key=kb + ".text")
        zeiten = echt(kanal.get("zeiten"))
        if zeiten:
            text += f'<p class="small muted"{i18n(kb + ".zeiten")}>{h(zeiten)}</p>'
        l_attr = i18n(kb + ".label")
        karten += (f'<div class="card"><h3 class="serif"{l_attr}>{h(label)}</h3>{text}'
                   f'<a class="link" href="{h(ziel)}"{extern}{l_attr}>{h(label)}</a></div>')
    if not karten:
        return ""
    hinweis = echt(kw.get("hinweis_gesundheitsdaten"))
    kasten = (f'<div class="note-box"'
              f'{i18n(dkey("seiteninhalte", "kontaktwege", "hinweis_gesundheitsdaten"))}>'
              f'{h(hinweis)}</div>') if hinweis else ""
    return (f'\n<section class="section">'
            f'<h2{i18n("seite.kontakt.wege.titel")}>So erreichen Sie uns</h2>'
            f'<div class="grid-3">{karten}</div>{kasten}</section>')


def build_kontakt():
    prefix = ""
    # data-i18n-region wird vom JavaScript über contact.region gefüllt.
    VERWENDETE_SCHLUESSEL.add("contact.region")
    behandlung_options = ""
    for k in kats():
        o_i18n = i18n("kat." + k["id"] + ".name")
        behandlung_options += f'<option{o_i18n}>{h(k["name_de"])}</option>'
    kopf = head(
        "Kontakt | ETA",
        "Der schnellste Weg zu uns: WhatsApp. Oder senden Sie uns Ihre Anfrage per Formular.",
        prefix, kanonisch("kontakt.html"), "meta.kontakt.title", "meta.kontakt.desc",
        jsonld=ld(
            ld_organisation(),
            {"@context": "https://schema.org", "@type": "ContactPage", "url": kanonisch("kontakt.html"),
             "name": "Kontakt", "about": {"@id": f"{BASE_URL}/#organisation"}},
            ld_krumen([("Start", kanonisch("index.html")), ("Kontakt", kanonisch("kontakt.html"))]),
        ),
    )
    rumpf = f"""
<section class="page-band">
  <div class="crumbs"><a href="index.html"{i18n('seite.allgemein.crumb.start')}>Start</a><span>/</span><span{i18n('nav.kontakt')}>Kontakt</span></div>
  <h1{i18n('seite.kontakt.titel')}>Kontakt</h1>
  <p{i18n('seite.kontakt.text')}>Der schnellste Weg zu uns ist WhatsApp. Wenn Sie lieber schreiben, nutzen Sie das Formular, wir melden uns in der Regel noch am selben Tag.</p>
</section>
<section class="section kontakt-layout">
  <div class="kontakt-side">
    <div class="wa-card">
      {WA_SVG.format(s=30)}
      <h2 class="serif"{i18n('seite.kontakt.wa.titel')}>Direkt per WhatsApp</h2>
      <p><span{i18n('seite.kontakt.wa.text1')}>Schreiben Sie uns formlos, was Sie sich wünschen, mit Betreuung aus</span> <span data-i18n-region>Schweiz, Österreich, Deutschland</span><span{i18n('seite.kontakt.wa.text2')}>. Antwort in der Regel innerhalb weniger Stunden.</span></p>
      <div class="wa-number"><a href="tel:+41764122122">+41 76 412 21 22</a></div>
      {wa_button('Chat starten', 18, 'btn btn-gold', 'seite.kontakt.wa.cta')}
    </div>
    <div class="card">
      <div class="fact"><span{i18n('seite.kontakt.fakten.email.label')}>E-Mail</span><strong><a href="mailto:info@eta-agency.ch">info@eta-agency.ch</a></strong></div>
      <div class="fact"><span{i18n('seite.kontakt.fakten.sprachen.label')}>Beratungssprachen</span><strong{i18n('seite.kontakt.fakten.sprachen.wert')}>Deutsch, Englisch, Türkisch, Arabisch</strong></div>
    </div>
  </div>
  <form class="kontakt-form card" id="anfrage-form" method="post">
    <h2 class="serif"{i18n('seite.kontakt.formular.titel')}>Anfrage senden</h2>
    {pflicht_hinweis()}
    <div class="form-grid-2">
      <label for="kf-vorname"><span{i18n('seite.kontakt.formular.vorname.label')}>Vorname</span>{PFLICHT_STERN}<input id="kf-vorname" type="text" name="vorname" required aria-required="true" autocomplete="given-name"></label>
      <label for="kf-nachname"><span{i18n('seite.kontakt.formular.nachname.label')}>Nachname</span>{PFLICHT_STERN}<input id="kf-nachname" type="text" name="nachname" required aria-required="true" autocomplete="family-name"></label>
    </div>
    <label for="kf-strasse"><span{i18n('seite.kontakt.formular.strasse.label')}>Strasse und Nr.</span><input id="kf-strasse" type="text" name="strasse" autocomplete="street-address"></label>
    <div class="form-grid-3">
      <label for="kf-plz"><span{i18n('seite.kontakt.formular.plz.label')}>PLZ</span><input id="kf-plz" type="text" name="plz" inputmode="numeric" autocomplete="postal-code"></label>
      <label for="kf-ort"><span{i18n('seite.kontakt.formular.ort.label')}>Ort</span><input id="kf-ort" type="text" name="ort" autocomplete="address-level2"></label>
      <label for="kf-geburtsdatum"><span{i18n('seite.kontakt.formular.geburtsdatum.label')}>Geburtsdatum</span><input id="kf-geburtsdatum" type="text" name="geburtsdatum" placeholder="TT.MM.JJJJ"{i18n_attr('placeholder:seite.kontakt.formular.geburtsdatum.ph')}></label>
    </div>
    <div class="form-grid-tel">
      <label for="kf-vorwahl"><span{i18n('seite.kontakt.formular.vorwahl.label')}>Vorwahl</span>
        <select id="kf-vorwahl" name="vorwahl"><option>+41</option><option>+43</option><option>+49</option></select>
      </label>
      <label for="kf-telefon"><span{i18n('seite.kontakt.formular.telefon.label')}>Telefon</span>{PFLICHT_STERN}<input id="kf-telefon" type="tel" name="telefon" required aria-required="true" autocomplete="tel-national"></label>
      <label for="kf-email"><span{i18n('seite.kontakt.formular.email.label')}>E-Mail</span>{PFLICHT_STERN}<input id="kf-email" type="email" name="email" required aria-required="true" autocomplete="email"></label>
    </div>
    <label for="kf-behandlung"><span{i18n('seite.kontakt.formular.behandlung.label')}>Gewünschte Behandlung</span>
      <select id="kf-behandlung" name="behandlung"><option value=""{i18n('seite.kontakt.formular.behandlung.wahl')}>Bitte wählen</option>{behandlung_options}</select>
    </label>
    <label for="kf-nachricht"><span{i18n('seite.kontakt.formular.nachricht.label')}>Ihre Nachricht</span><textarea id="kf-nachricht" name="nachricht" rows="5" placeholder="Was dürfen wir für Sie tun?"{i18n_attr('placeholder:seite.kontakt.formular.nachricht.ph')}></textarea></label>
    {HONEYPOT}
    <label class="checkbox" for="kf-einwilligung"><input id="kf-einwilligung" type="checkbox" name="einwilligung" value="ja" required aria-required="true"><span><span{i18n('seite.allgemein.dsgvo.teil1')}>Ich habe die</span> <a href="datenschutz.html"{i18n('seite.allgemein.dsgvo.link')}>Datenschutzerklärung</a> <span{i18n('seite.kontakt.formular.dsgvo.teil2')}>gelesen und bin mit der Verarbeitung meiner Angaben zur Bearbeitung der Anfrage einverstanden.</span></span></label>
    <input type="hidden" name="einwilligung_version" value="{EINWILLIGUNG_VERSION}">
    <div class="form-footer">
      <button type="submit" class="btn btn-gold"{i18n('seite.allgemein.formular.senden')}>Anfrage senden</button>
      <p class="small muted"{i18n('seite.kontakt.formular.hinweis.ohne_betrag')}>{anzahlung_satz()}</p>
    </div>
    {FORM_STATUS}
  </form>
</section>
""" + kontaktwege_block(prefix)
    seite("kontakt.html", kopf, header_nav(prefix, "kontakt"), rumpf, prefix)


def firma_adresse():
    """Anbieterangaben aus data/recht.json. Jede Zeile nur, wenn gefuellt.

    Vorher standen hier «[STRASSE NR.]», «[PLZ ORT]», «[HR-NUMMER]» und
    «[NAME]». Was fehlt, erscheint nicht — die Liste der offenen Angaben
    fuehrt data/AUSFUELLHILFE.md, nicht die Website.
    """
    f_ = RECHT.get("firma", {})
    zeilen = []
    # Der Firmenname ist ein Eigenname und bleibt unuebersetzt.
    name = echt(f_.get("name")) or "ETA – European Turkey Asia"
    rechtsform = echt(f_.get("rechtsform"))
    zeilen.append(h(name) + (f" ({h(rechtsform)})" if rechtsform else ""))
    if echt(f_.get("strasse")):
        zeilen.append(h(echt(f_["strasse"])))
    land = echt(f_.get("land"))
    land_html = span(land, dkey("recht", "firma", "land")) if land else ""
    ort = " ".join(x for x in [echt(f_.get("plz")), echt(f_.get("ort"))] if x)
    if ort:
        zeilen.append(h(ort) + (", " + land_html if land_html else ""))
    elif land_html:
        zeilen.append(land_html)
    return "<p>" + "<br>".join(zeilen) + "</p>"


def firma_kontakt():
    f_ = RECHT.get("firma", {})
    kontakt = []
    if echt(f_.get("email")):
        kontakt.append(f'<span{i18n("seite.impressum.kontakt.email")}>E-Mail:</span> '
                       f'<a href="mailto:{h(f_["email"])}">{h(f_["email"])}</a>')
    if echt(f_.get("telefon")):
        # Bewusst kein tel:-Link: die Nummer ist heute die WhatsApp-Nummer.
        # data/recht.json verlangt eine Bestaetigung, dass sie auch als
        # Telefonanschluss erreichbar ist, bevor daraus ein Anruf-Link wird.
        kontakt.append(f'<span{i18n("seite.impressum.kontakt.telefon")}>Telefon:</span> '
                       f'{h(f_["telefon"])}')
    return "<p>" + "<br>".join(kontakt) + "</p>" if kontakt else ""


def firma_register():
    """Handelsregister, UID, Vertretung — heute alles leer, also kein Abschnitt."""
    f_ = RECHT.get("firma", {})
    register = []
    if echt(f_.get("hr_nummer")):
        eintrag = "Handelsregister: " + h(echt(f_["hr_nummer"]))
        if echt(f_.get("hr_kanton")):
            eintrag += ", Kanton " + h(echt(f_["hr_kanton"]))
        register.append(eintrag)
    if echt(f_.get("uid")):
        register.append("UID: " + h(echt(f_["uid"])))
    if echt(f_.get("mwst_nummer")):
        register.append("MWST-Nummer: " + h(echt(f_["mwst_nummer"])))
    if echt(f_.get("vertretung")):
        funktion = echt(f_.get("vertretung_funktion"))
        register.append(
            "Vertretungsberechtigt: " + h(echt(f_["vertretung"])) + (f" ({h(funktion)})" if funktion else "")
        )
    return "<p>" + "<br>".join(register) + "</p>" if register else ""


ERSETZTE_IMPRESSUM_ABSCHNITTE = {
    "betreiber": lambda: firma_adresse(),
    "handelsregister": firma_register,
    "kontakt": firma_kontakt,
}


def recht_abschnitt(a, extra="", basis=""):
    """Ein Abschnitt aus data/recht.json. basis ist sein Schluessel in den Daten,
    z. B. daten.recht.datenschutz.abschnitte.3 — Titel, Absaetze und Listen
    haengen sich mit .titel, .absaetze.<i> und .liste.<i> daran."""
    teile = [f'<h2{i18n(f"{basis}.titel" if basis else "")}>{h(a["titel"])}</h2>'] \
        if echt(a.get("titel")) else []
    for i, absatz in enumerate(a.get("absaetze", [])):
        if echt(absatz):
            teile.append(f'<p{i18n(f"{basis}.absaetze.{i}" if basis else "")}>{h(absatz)}</p>')
    if a.get("liste"):
        eintraege = "".join(
            f'<li{i18n(f"{basis}.liste.{i}" if basis else "")}>{h(x)}</li>'
            for i, x in enumerate(a["liste"]) if echt(x)
        )
        if eintraege:
            teile.append(f"<ul>{eintraege}</ul>")
    if extra:
        teile.append(extra)
    return "\n".join(teile)


def build_rechtliches():
    """Impressum, Datenschutz und AGB aus data/recht.json.

    Die Texte sind Redaktionsentwuerfe aus planning/ und tragen «freigabe:
    offen» — deshalb bleibt der ENTWURF-Kasten stehen, solange
    recht.json -> entwurf_banner true ist. Die Felder «hinweis» und
    «offene_punkte» sind Notizen fuer den Auftraggeber und gehen bewusst
    nicht ins HTML.
    """
    prefix = ""
    entwurf = ""
    if RECHT.get("entwurf_banner", True):
        text = echt(RECHT.get("entwurf_text")) or (
            "Diese Seite ist eine Arbeitsversion und wird vor dem Go-Live juristisch "
            "geprüft und vervollständigt."
        )
        entwurf = f'<div class="note-box"{i18n("seite.rechtliches.entwurf")}>{h(text)}</div>'

    seiten = [
        ("impressum.html", "impressum", "Impressum", "Impressum",
         "Impressum der ETA – European Turkey Asia: Anbieterin, Kontaktangaben und Hinweis zur Vermittlungstätigkeit."),
        ("datenschutz.html", "datenschutz", "Datenschutz", "Datenschutzerklärung",
         "Wie ETA Ihre Personendaten und besonders Ihre Gesundheitsdaten bearbeitet, nach revDSG und DSGVO."),
        ("agb.html", "agb", "AGB", "Allgemeine Geschäftsbedingungen",
         "Die Bedingungen für die Vermittlung durch ETA: Leistung, Anzahlung, Terminverschiebung, Mitwirkung, Haftung."),
    ]
    for fname, teil, kurz, langtitel, beschreibung in seiten:
        daten = RECHT.get(teil, {})
        abschnitte = daten.get("abschnitte", [])
        koerper = [entwurf]
        if abschnitte:
            for nr, a in enumerate(abschnitte):
                basis = dkey("recht", teil, "abschnitte", nr)
                if teil == "impressum" and a.get("id") in ERSETZTE_IMPRESSUM_ABSCHNITTE:
                    # Diese drei Abschnitte bestehen in den Daten nur aus einer
                    # Anweisung an den Generator («ergeben sich aus dem Block
                    # firma»). Der Besucher will dort Angaben sehen, nicht die
                    # Bauanleitung — also erzeugt der Generator den Inhalt und
                    # laesst den Abschnitt weg, wenn nichts davon gefuellt ist.
                    inhalt = ERSETZTE_IMPRESSUM_ABSCHNITTE[a["id"]]()
                    if inhalt:
                        koerper.append(f'<h2{i18n(basis + ".titel")}>{h(a["titel"])}</h2>' + inhalt)
                    continue
                koerper.append(recht_abschnitt(a, basis=basis))
        else:
            koerper.append(f"<h2>{h(langtitel)}</h2>" + firma_adresse() + firma_kontakt())
        t_i18n = i18n("seite." + teil + ".titel")
        kopf = head(
            f"{kurz} | ETA", beschreibung, prefix, kanonisch(fname),
            "meta." + teil + ".title", "meta." + teil + ".desc",
            jsonld=ld(
                ld_organisation(),
                ld_krumen([("Start", kanonisch("index.html")), (kurz, kanonisch(fname))]),
            ),
        )
        rumpf = f"""
<section class="page-band">
  <div class="crumbs"><a href="index.html"{i18n('seite.allgemein.crumb.start')}>Start</a><span>/</span><span{t_i18n}>{h(kurz)}</span></div>
  <h1{t_i18n}>{h(kurz)}</h1>
</section>
<section class="section legal" lang="de">
{"".join(koerper)}
</section>
"""
        seite(fname, kopf, header_nav(prefix, ""), rumpf, prefix)


# ------------------------------------------------------- Neue Inhaltsseiten
# Alle drei Seiten stammen aus data/seiteninhalte.json. Was dort leer ist,
# erscheint nicht — weder als Ueberschrift noch als leere Kachel. Die Felder
# «offen», «hinweis», «hinweis_generator», «warum» und «quelle» sind Notizen
# fuer die Redaktion und den Auftraggeber und gehen nie ins HTML.
def inhalt_seite(relpath, titel, beschreibung, kurz, rumpf_inhalt, i18n_stamm,
                 cta=("Fragen dazu?", "Wir antworten persönlich, auf Deutsch.")):
    """Rahmen fuer die drei neuen Textseiten: Brotkrumen, H1, Inhalt, CTA."""
    prefix = ""
    kopf = head(
        f"{kurz} | ETA", beschreibung, prefix, kanonisch(relpath),
        "meta." + i18n_stamm + ".title", "meta." + i18n_stamm + ".desc",
        jsonld=ld(
            ld_organisation(),
            ld_krumen([("Start", kanonisch("index.html")), (kurz, kanonisch(relpath))]),
        ),
    )
    t_i18n = i18n("seite." + i18n_stamm + ".titel")
    k_i18n = i18n("seite." + i18n_stamm + ".kurz")
    rumpf = f"""
<section class="page-band">
  <div class="crumbs"><a href="index.html"{i18n('seite.allgemein.crumb.start')}>Start</a><span>/</span><span{k_i18n}>{h(kurz)}</span></div>
  <h1{t_i18n}>{h(titel)}</h1>
</section>
<section class="section legal">
{rumpf_inhalt}
</section>
""" + cta_band(cta[0], cta[1], "seite." + i18n_stamm + ".cta")
    seite(relpath, kopf, header_nav(prefix, "wissen"), rumpf, prefix)


def notfall_abschnitt(a, basis):
    """Der Abschnitt, auf den es im Ernstfall ankommt. Er steht deshalb oben."""
    teile = [absaetze(a.get("absaetze"), key=basis + ".absaetze")]
    warn = punkte(a.get("warnzeichen"), key=basis + ".warnzeichen")
    if warn:
        titel = echt(a.get("warnzeichen_titel")) or "Sofort in eine Notfallaufnahme bei"
        teile.append(f'<h3{i18n(basis + ".warnzeichen_titel")}>{h(titel)}</h3>{warn}')
    hinweis = echt(a.get("warnzeichen_hinweis"))
    if hinweis:
        teile.append(f'<div class="note-box"{i18n(basis + ".warnzeichen_hinweis")}>{h(hinweis)}</div>')
    nummern = fakt_liste([
        (n.get("label"), n.get("wert"),
         f"{basis}.notfallnummern.{i}.label", f"{basis}.notfallnummern.{i}.wert")
        for i, n in enumerate(a.get("notfallnummern", []))
    ])
    if nummern:
        teile.append(f'<div class="card">{nummern}</div>')
    return "".join(teile)


def zustaendig_abschnitt(a, basis):
    teile = [absaetze(a.get("absaetze"), key=basis + ".absaetze")]
    zeilen = fakt_liste([
        (r.get("frage"), r.get("wer"), f"{basis}.tabelle.{i}.frage", f"{basis}.tabelle.{i}.wer")
        for i, r in enumerate(a.get("tabelle", []))
    ])
    if zeilen:
        teile.append(f'<div class="card">{zeilen}</div>')
    return "".join(teile)


# Etikett und i18n-Schluessel je Zeile. Die Werte dazu liegen noch nicht vor
# (data/seiteninhalte.json -> regelung / weg sind leer), die Zeilen erscheinen
# deshalb heute nicht — die Schluessel stehen trotzdem hier, damit die Zeilen
# uebersetzt sind, sobald ETA die Angaben liefert.
REVISION_LABEL = [
    ("gewaehrleistung_klinik", "Gewährleistung der Klinik", "seite.schiefgeht.revision.gewaehrleistung"),
    ("frist", "Frist", "seite.schiefgeht.revision.frist"),
    ("reise_bei_revision", "Reise und Unterkunft bei einer Revision", "seite.schiefgeht.revision.reise"),
    ("wer_entscheidet", "Wer über einen Revisionsfall entscheidet", "seite.schiefgeht.revision.entscheidung"),
]
BESCHWERDE_LABEL = [
    ("kontakt", "Beschwerdestelle", "seite.schiefgeht.beschwerde.stelle"),
    ("frist_rueckmeldung", "Rückmeldung innerhalb von", "seite.schiefgeht.beschwerde.frist"),
    ("eskalation", "Wenn wir uns nicht einigen", "seite.schiefgeht.beschwerde.eskalation"),
]


def schiefgeht_abschnitt(a, nr):
    """Ein Abschnitt der Seite «Wenn etwas nicht wie geplant läuft».

    nr ist die Stelle des Abschnitts in data/seiteninhalte.json, nicht die
    Stelle auf der Seite: «vorrang» zieht einen Abschnitt nach oben, die
    Schluessel folgen aber der Datei.
    """
    basis = dkey("seiteninhalte", "wenn_etwas_schiefgeht", "abschnitte", nr)
    aid = a.get("id")
    if aid == "notfall":
        inhalt = notfall_abschnitt(a, basis)
    elif aid == "zustaendig":
        inhalt = zustaendig_abschnitt(a, basis)
    else:
        inhalt = absaetze(a.get("absaetze"), key=basis + ".absaetze")
        # Die Gewaehrleistungsregelung der Klinik liegt noch nicht vor. Solange
        # alle Felder leer sind, erscheint keine leere Tabelle — nur der Text.
        for schluessel, labels in (("regelung", REVISION_LABEL), ("weg", BESCHWERDE_LABEL)):
            daten = a.get(schluessel) or {}
            zeilen = fakt_liste([
                (label, daten.get(feld), label_key, f"{basis}.{schluessel}.{feld}")
                for feld, label, label_key in labels
            ])
            if zeilen:
                inhalt += f'<div class="card">{zeilen}</div>'
        # Nachsorgepartner: Name und Ort stehen fest, die Adresse noch nicht.
        partner = a.get("partner") or {}
        if echt(partner.get("name")):
            url = echt(partner.get("url"))
            n_attr = i18n(basis + ".partner.name")
            name = f"<span{n_attr}>{h(partner['name'])}</span>"
            ziel = (f'<a href="{h(url)}" rel="noopener" target="_blank"{n_attr}>'
                    f'{h(partner["name"])}</a>') if url else name
            wenn_ort = (f', {span(echt(partner["ort"]), basis + ".partner.ort")}'
                        if echt(partner.get("ort")) else "")
            inhalt += f"<p>{ziel}{wenn_ort}</p>"
        leistungen = a.get("leistungen") or {}
        inhalt += block("Im Preis enthalten",
                        punkte(leistungen.get("im_preis_enthalten"), "check-list",
                               key=basis + ".leistungen.im_preis_enthalten"),
                        "seite.schiefgeht.leistungen.enthalten", "h3")
        inhalt += block("Zusätzlich kostenpflichtig",
                        punkte(leistungen.get("zusaetzlich_kostenpflichtig"),
                               key=basis + ".leistungen.zusaetzlich_kostenpflichtig"),
                        "seite.schiefgeht.leistungen.kostenpflichtig", "h3")
        inhalt += block("Fragen an Ihre Versicherung",
                        punkte(a.get("pruefliste"), key=basis + ".pruefliste"),
                        "seite.schiefgeht.pruefliste.titel", "h3")
    if not inhalt.strip():
        return ""
    titel = echt(a.get("titel"))
    return (f'<h2{i18n(basis + ".titel")}>{h(titel)}</h2>' if titel else "") + inhalt


def build_schiefgeht():
    daten = SEITENINHALTE.get("wenn_etwas_schiefgeht")
    if not daten:
        return
    abschnitte = list(enumerate(daten.get("abschnitte", [])))
    # «vorrang» heisst: dieser Abschnitt gehoert ganz nach oben, vor allem
    # anderen. Es ist der einzige, bei dem eine Formulierung im Ernstfall zaehlt.
    geordnet = ([p for p in abschnitte if p[1].get("vorrang")]
                + [p for p in abschnitte if not p[1].get("vorrang")])
    inhalt = (absaetze(daten.get("intro"), "lead",
                       key=dkey("seiteninhalte", "wenn_etwas_schiefgeht", "intro"))
              + "".join(schiefgeht_abschnitt(a, nr) for nr, a in geordnet))
    inhalt += (f'\n<p class="small"><a class="link" href="{SEITE_REISE}"'
               f'{i18n("seite.schiefgeht.link.reise")}>Ihre Reise, Tag für Tag</a>'
               f' · <a class="link" href="gut-zu-wissen.html"'
               f'{i18n("seite.schiefgeht.link.wissen")}>Gut zu wissen</a></p>')
    inhalt_seite(
        SEITE_SCHIEFGEHT, echt(daten.get("titel")) or "Wenn etwas nicht wie geplant läuft",
        "Zuständigkeiten, Nachbesserung, Nachsorge, Versicherung und Notfallnummern — "
        "was gilt, wenn eine Behandlung nicht wie geplant verläuft.",
        echt(daten.get("titel")) or "Wenn etwas nicht wie geplant läuft",
        inhalt, "schiefgeht",
        cta=("Offene Frage dazu?", "Fragen Sie uns, bevor Sie sich entscheiden."),
    )


def build_reise():
    daten = SEITENINHALTE.get("reiseablauf")
    if not daten:
        return
    basis = dkey("seiteninhalte", "reiseablauf")
    inhalt = absaetze(daten.get("intro"), "lead", key=basis + ".intro")
    vor = daten.get("vor_der_reise") or {}
    schritte = "".join(
        f'<li><h3{i18n(f"{basis}.vor_der_reise.schritte.{i}.titel")}>{h(echt(x.get("titel")))}</h3>'
        f'{absaetze(x.get("text"), key=f"{basis}.vor_der_reise.schritte.{i}.text")}</li>'
        for i, x in enumerate(vor.get("schritte", [])) if echt(x.get("titel"))
    )
    if schritte:
        inhalt += (f'<h2{i18n(basis + ".vor_der_reise.titel")}>'
                   f'{h(echt(vor.get("titel")) or "Vor der Reise")}</h2>'
                   f'<ol class="ablauf-list">{schritte}</ol>')
    inhalt += block("Was Sie mitnehmen",
                    punkte(vor.get("mitnehmen"), "check-list", key=basis + ".vor_der_reise.mitnehmen"),
                    "seite.reise.mitnehmen.titel", "h3")
    for i, tag in enumerate(daten.get("tage", [])):
        # Kopfzeile aus zwei Datenwerten: «Anreisetag» und «Ankunft und
        # Voruntersuchung» sind zwei Schluessel, der Doppelpunkt bleibt dazwischen.
        kopf = [span(echt(tag[feld]), f"{basis}.tage.{i}.{feld}")
                for feld in ("tag", "titel") if echt(tag.get(feld))]
        p_ = punkte(tag.get("punkte"), key=f"{basis}.tage.{i}.punkte")
        if kopf and p_:
            inhalt += f'<h2>{": ".join(kopf)}</h2>{p_}'
    zurueck = daten.get("nach_der_rueckkehr") or {}
    inhalt += block(echt(zurueck.get("titel")) or "Nach der Rückkehr",
                    punkte(zurueck.get("punkte"), key=basis + ".nach_der_rueckkehr.punkte"),
                    basis + ".nach_der_rueckkehr.titel")
    inhalt += (f'\n<p class="small"><a class="link" href="{SEITE_KOSTEN}"'
               f'{i18n("seite.reise.link.kosten")}>Was es insgesamt kostet</a>'
               f' · <a class="link" href="{SEITE_SCHIEFGEHT}"'
               f'{i18n("seite.reise.link.schiefgeht")}>Wenn etwas nicht wie geplant läuft</a></p>')
    inhalt_seite(
        SEITE_REISE, echt(daten.get("titel")) or "Ihre Reise, Tag für Tag",
        "Von der ersten Anfrage bis zur Nachkontrolle: Vorbereitung, Packliste, Ankunft, "
        "Behandlungstag, Kontrolle und Rückflug.",
        "Ihre Reise", inhalt, "reise",
        cta=("Noch etwas unklar am Ablauf?", "Wir gehen ihn mit Ihnen durch."),
    )


# Wer traegt welchen Posten. Die Schluessel stehen so in data/seiteninhalte.json.
KOSTEN_GRUPPEN = [
    ("im Fixpreis", "Im Fixpreis enthalten", "seite.kosten.gruppe.fixpreis"),
    ("teils im Fixpreis", "Teils im Fixpreis", "seite.kosten.gruppe.teils"),
    ("Aufpreis", "Gegen Aufpreis", "seite.kosten.gruppe.aufpreis"),
    ("Eigenleistung", "Nicht enthalten — das zahlen Sie selbst", "seite.kosten.gruppe.eigenleistung"),
]


def build_kosten():
    daten = SEITENINHALTE.get("gesamtkosten")
    if not daten:
        return
    basis = dkey("seiteninhalte", "gesamtkosten")
    inhalt = absaetze(daten.get("intro"), "lead", key=basis + ".intro")
    posten = daten.get("posten", [])
    for traeger, titel, titel_key in KOSTEN_GRUPPEN:
        eintraege = ""
        for i, x in enumerate(posten):
            if x.get("traeger") != traeger or not echt(x.get("label")):
                continue
            betrag = echt(x.get("betrag"))
            h_key = dkey_abgeleitet(ohne_redaktionsnotiz, "seiteninhalte",
                                    "gesamtkosten", "posten", i, "hinweis")
            hinweis = ohne_redaktionsnotiz(x.get("hinweis"))
            zeile = span(echt(x["label"]), f"{basis}.posten.{i}.label")
            if betrag:
                zeile += f" — <strong>{h(betrag)}</strong>"
            if hinweis:
                zeile += f'<br><span class="small muted"{i18n(h_key)}>{h(hinweis)}</span>'
            eintraege += f"<li>{zeile}</li>"
        if eintraege:
            # Der goldene Haken nur dort, wo etwas enthalten ist. Neben
            # «Flug ab der Schweiz» unter «nicht enthalten» behauptet er das
            # Gegenteil dessen, was dasteht.
            cls = "check-list" if traeger == "im Fixpreis" else "punkt-liste"
            inhalt += f'<h2{i18n(titel_key)}>{h(titel)}</h2><ul class="{cls}">{eintraege}</ul>'
    # Das Rechenbeispiel bleibt weg, solange keine Zahlen da sind. Ein leeres
    # Beispiel waere schlimmer als keines.
    beispiel = daten.get("rechenbeispiel") or {}
    zeilen = fakt_liste([
        (z.get("label"), z.get("betrag"), f"{basis}.rechenbeispiel.zeilen.{i}.label",
         f"{basis}.rechenbeispiel.zeilen.{i}.betrag")
        for i, z in enumerate(beispiel.get("zeilen", []))
    ])
    if zeilen:
        inhalt += (f'<h2{i18n("seite.kosten.beispiel.titel")}>Ein Beispiel</h2>'
                   f'<div class="card">{zeilen}</div>')
    inhalt += (f'\n<p class="small"><a class="link" href="finanzierung.html"'
               f'{i18n("seite.kosten.link.finanzierung")}>Finanzierung in Raten</a>'
               f' · <a class="link" href="{SEITE_REISE}"'
               f'{i18n("seite.kosten.link.reise")}>Ihre Reise, Tag für Tag</a></p>')
    inhalt_seite(
        SEITE_KOSTEN, echt(daten.get("titel")) or "Was es wirklich kostet",
        "Was der Fixpreis enthält und was nicht: Flug, Begleitperson, zusätzliche Nächte, "
        "Versicherung und die langfristigen Folgekosten.",
        "Was es kostet", inhalt, "kosten",
        cta=("Was kostet es in Ihrem Fall?", "Sie erhalten ein schriftliches Fixpreis-Angebot."),
    )


def build_glossar():
    """Alle Fachbegriffe an einem Ort, mit Sprungmarke je Begriff.

    Warum eine eigene Seite und nicht nur Kurzerklaerungen auf den
    Behandlungsseiten: Nach «Was ist ein Graft» wird gesucht, und eine
    Erklaerung, die 33-mal verteilt in Kaesten steht, ist nicht auffindbar.
    Die Behandlungsseiten tragen die Kurzfassung und verweisen hierher; hier
    steht die Langfassung samt Querverweisen. Beides kommt aus derselben
    Quelle, data/glossar.json.
    """
    if not GLOSSAR_SORTIERT:
        return
    prefix = ""
    # Sprungliste: bei 33 Begriffen der Unterschied zwischen Nachschlagen und
    # Scrollen.
    sprungliste = "".join(
        f'<a class="glossar-sprung" href="#{e["slug"]}"'
        f'{i18n(glossar_schluessel(e["slug"], "begriff"))}>{h(b)}</a>'
        for b, e in GLOSSAR_SORTIERT
    )
    abschnitte = ""
    for b, e in GLOSSAR_SORTIERT:
        eintrag = e["eintrag"]
        text = e["lang"] or e["kurz"]
        langfassung = f'<p{i18n(glossar_schluessel(e["slug"], "lang" if e["lang"] else "kurz"))}>{h(text)}</p>'
        # Wo der Begriff vorkommt: nur Behandlungen, die es wirklich gibt.
        ziele = "".join(
            f'<a class="link" href="{prefix}behandlungen/{SLUG_REGISTER[x][0]}/{x}.html"'
            f'{i18n("beh." + x + ".name")}>{h(SLUG_REGISTER[x][1])}</a>'
            for x in e["behandlungen"] if x in SLUG_REGISTER
        )
        vorkommen = (f'<p class="small glossar-verweise"><span{i18n("seite.glossar.vorkommen")}>'
                     f'Kommt vor bei:</span> {ziele}</p>') if ziele else ""
        # Siehe auch: nur Begriffe, die das Glossar auch kennt.
        weiter = "".join(
            f'<a class="link" href="#{GLOSSAR_REGISTER[x]["slug"]}"'
            f'{i18n(glossar_schluessel(GLOSSAR_REGISTER[x]["slug"], "begriff"))}>{h(x)}</a>'
            for x in e["siehe_auch"] if x in GLOSSAR_REGISTER
        )
        siehe = (f'<p class="small glossar-verweise"><span{i18n("seite.glossar.siehe_auch")}>'
                 f'Siehe auch:</span> {weiter}</p>') if weiter else ""
        abschnitte += (
            f'<article class="glossar-eintrag" id="{e["slug"]}">'
            f'<h2{i18n(glossar_schluessel(e["slug"], "begriff"))}>{h(b)}</h2>'
            f'{langfassung}{vorkommen}{siehe}</article>'
        )
    rumpf_inhalt = (
        f'<p class="glossar-einleitung"{i18n("seite.glossar.text")}>'
        f'Fachwörter, die in Angeboten und auf Behandlungsseiten vorkommen — hier in '
        f'normalem Deutsch. Wer die Begriffe kennt, kann Angebote vergleichen. '
        f'Die Erklärungen sind allgemein und ersetzen kein ärztliches Gespräch.</p>'
        f'<nav class="glossar-sprungliste" aria-label="Fachbegriffe"'
        f'{i18n_attr("aria-label:seite.glossar.kurz")}>{sprungliste}</nav>'
        f'{abschnitte}'
    )
    inhalt_seite(
        SEITE_GLOSSAR, "Fachbegriffe, verständlich erklärt",
        "Graft, DHI, Saphir, HIFU, Veneer, Masseter: die Fachwörter aus Angeboten und "
        "Behandlungsseiten, in normalem Deutsch erklärt.",
        "Fachbegriffe", rumpf_inhalt, "glossar",
        cta=("Ein Wort fehlt hier?", "Fragen Sie uns — wir erklären es Ihnen."),
    )


def build_beratung():
    """Der zweite Zugang zum Katalog: nach Anliegen statt nach Verfahren.

    Befund inhalt B12: Wer eine Behandlung sucht, kennt meist sein Anliegen
    («meine Haut wirkt müde»), nicht das Verfahren («Skinbooster»). Der
    Katalog war bisher nur nach Verfahren sortiert. Wer sich nicht entscheiden
    kann, fragt nicht an — er vertagt.
    """
    if not BERATUNG_ANLIEGEN:
        return
    prefix = ""
    # Kurzliste oben: bei 13 Anliegen der Weg zum eigenen in einem Blick.
    sprungliste = "".join(
        f'<a class="glossar-sprung" href="#{h(a["id"])}"'
        f'{i18n("beratung.anliegen." + a["id"] + ".titel")}>{h(a["titel"])}</a>'
        for a in BERATUNG_ANLIEGEN
    )
    abschnitte = ""
    for a in BERATUNG_ANLIEGEN:
        aid = a["id"]
        karten = "".join(
            f'<a class="t-card" href="{prefix}behandlungen/{SLUG_REGISTER[x][0]}/{x}.html">'
            f'<h4{i18n("beh." + x + ".name")}>{h(SLUG_REGISTER[x][1])}</h4>'
            f'<span class="link"{i18n("seite.allgemein.mehr_erfahren")}>Mehr erfahren</span></a>'
            for x in a.get("verfahren", []) if x in SLUG_REGISTER
        )
        text = echt(a.get("text"))
        teile = ""
        if text:
            teile += f'<p{i18n("beratung.anliegen." + aid + ".text")}>{h(text)}</p>'
        if karten:
            teile += f'<div class="grid-4">{karten}</div>'
        # Die Gegenueberstellung, falls es fuer dieses Anliegen eine gibt.
        # Sieben der 13 Anliegen verweisen auf eine Gruppe, die es noch nicht
        # gibt — dort bleibt der Block einfach weg.
        teile += vergleich_block(a.get("vergleich") or "", prefix, titel_stufe="h3")
        if not teile:
            continue
        abschnitte += (f'<article class="anliegen" id="{h(aid)}">'
                       f'<h2{i18n("beratung.anliegen." + aid + ".titel")}>{h(a["titel"])}</h2>'
                       f"{teile}</article>")
    rumpf = f"""
<section class="page-band">
  <div class="crumbs"><a href="index.html"{i18n('seite.allgemein.crumb.start')}>Start</a><span>/</span><span{i18n('seite.beratung.kurz')}>Was passt zu mir?</span></div>
  <h1{i18n('seite.beratung.titel')}>Sie kennen Ihr Anliegen, nicht das Verfahren?</h1>
  <p{i18n('seite.beratung.text')}>Suchen Sie sich aus, was Ihnen am nächsten kommt. Wir nennen die Verfahren, die dafür in Frage kommen, und sagen dazu, worin sie sich unterscheiden. Welches davon für Sie passt, klärt das ärztliche Gespräch.</p>
</section>
<section class="section beratung-liste">
  <nav class="glossar-sprungliste" aria-label="Was passt zu mir?"{i18n_attr('aria-label:seite.beratung.kurz')}>{sprungliste}</nav>
  {abschnitte}
</section>
""" + cta_band(
        "Nichts davon trifft es genau?",
        "Schildern Sie uns Ihr Anliegen in eigenen Worten.",
        "seite.beratung.cta",
    )
    kopf = head(
        "Was passt zu mir? | ETA",
        "Nach Anliegen statt nach Verfahren: 13 häufige Anliegen und die Behandlungen, "
        "die dafür in Frage kommen — mit den Unterschieden dazwischen.",
        prefix, kanonisch(SEITE_BERATUNG), "meta.beratung.title", "meta.beratung.desc",
        jsonld=ld(
            ld_organisation(),
            ld_krumen([("Start", kanonisch("index.html")),
                       ("Was passt zu mir?", kanonisch(SEITE_BERATUNG))]),
        ),
    )
    seite(SEITE_BERATUNG, kopf, header_nav(prefix, "wissen"), rumpf, prefix)


def build_team():
    """Die Team-Seite entsteht nur, wenn Personen hinterlegt sind.

    So steht es als hinweis_generator in data/seiteninhalte.json: eine leere
    Team-Seite ist schlechter als keine. Heute ist «personen» leer, die Seite
    wird also nicht erzeugt und nirgends verlinkt.
    """
    daten = SEITENINHALTE.get("team") or {}
    personen = [x for x in daten.get("personen", []) if echt(x.get("name"))]
    if not personen:
        return
    karten = ""
    for x in personen:
        zeilen = fakt_liste([
            ("Rolle", x.get("rolle")),
            ("Sprachen", ", ".join(s for s in x.get("sprachen", []) if echt(s))),
            ("Erreichbar", x.get("erreichbar")),
        ])
        karten += (f'<div class="card"><h2 class="serif">{h(echt(x["name"]))}</h2>'
                   f"{zeilen}{absaetze(x.get('text'))}</div>")
    inhalt = absaetze(daten.get("intro"), "lead") + f'<div class="grid-3">{karten}</div>'
    inhalt_seite(
        (echt(daten.get("slug")) or "team") + ".html",
        echt(daten.get("titel")) or "Wer wir sind",
        "Die Menschen hinter ETA: Ihre feste Ansprechperson von der ersten Frage bis zur Nachkontrolle.",
        echt(daten.get("titel")) or "Wer wir sind", inhalt, "team",
        cta=("Sprechen Sie mit uns.", "Unverbindlich, diskret und auf Deutsch."),
    )


def build_404():
    """Eigene Fehlerseite. Vercel liefert eine vorhandene 404.html automatisch
    aus; bisher endete jeder tote Verweis auf Vercels schwarzer Standardseite
    ohne Marke, ohne Navigation und ohne Weg zurueck (Befund technik B6)."""
    prefix = ""
    karten = "".join(
        f'<a class="t-card" href="behandlungen/{k["id"]}/index.html">'
        f'<h2{i18n("kat." + k["id"] + ".name")}>{h(k["name_de"])}</h2>'
        f'<span class="link"{i18n("seite.allgemein.mehr_erfahren")}>Mehr erfahren</span></a>'
        for k in kats()
    )
    kopf = head(
        "Seite nicht gefunden | ETA",
        "Diese Seite gibt es nicht mehr oder sie wurde verschoben. Hier geht es zurück zum Behandlungskatalog.",
        prefix, kanonisch("404.html"), "meta.404.title", "meta.404.desc",
        jsonld=ld(ld_organisation()),
        robots="noindex, follow",
    )
    rumpf = f"""
<section class="page-band">
  <h1{i18n('seite.404.titel')}>Diese Seite gibt es nicht</h1>
  <p{i18n('seite.404.text')}>Vielleicht wurde sie verschoben, vielleicht stimmt etwas an der Adresse nicht. Hier kommen Sie weiter:</p>
  <a class="link" href="index.html"{i18n('seite.404.link_start')}>Zur Startseite</a>
</section>
<section class="section">
  <h2{i18n('seite.404.bereiche')}>Unsere Bereiche</h2>
  <div class="grid-4">{karten}</div>
</section>
""" + cta_band(
        "Sie suchen etwas Bestimmtes?",
        "Schreiben Sie uns, wir finden es für Sie.",
        "seite.404.cta",
    )
    # Bewusst nicht in PAGES: eine Fehlerseite gehoert nicht in die Sitemap.
    html = kopf + header_nav(prefix, "") + '\n<main id="inhalt" tabindex="-1">' + rumpf + "\n</main>" + footer(prefix)
    (SITE / "404.html").write_text(html)


def suchindex_seiten():
    """Die festen Seiten fuer die Suche — Ergaenzung der Bahn «navigation».

    Der Index der Bahn «anbindung» kannte nur die 101 Behandlungen. Wer
    «Kosten», «Garantie» oder «Impressum» eintippt, sucht aber eine Seite und
    keine Behandlung. Synonyme stehen hier im Generator, weil es zu diesen
    Seiten keine Datendatei gibt; Seiten, die nicht erzeugt werden, kommen
    auch nicht in den Index.
    """
    eintraege = [
        ("Alle Behandlungen", ["Katalog", "Übersicht", "Angebot", "Leistungen"], "behandlungen/index.html"),
        ("Partnerklinik", ["Klinik", "Istanbul", "Ärzte", "Zertifikate", "JCI"], "partnerklinik.html"),
        ("Finanzierung", ["Ratenzahlung", "bezahlen", "Kredit", "Teilzahlung"], "finanzierung.html"),
        ("Kontakt", ["anfragen", "Anfrage", "Beratung", "E-Mail", "Telefon", "WhatsApp"], "kontakt.html"),
        ("Häufige Fragen", ["FAQ", "Fragen", "Gut zu wissen", "Begleitperson", "Nachsorge"], "gut-zu-wissen.html"),
        ("Impressum", ["Anbieter", "Firma", "Adresse"], "impressum.html"),
        ("Datenschutz", ["Datenschutzerklärung", "DSGVO", "Daten"], "datenschutz.html"),
        ("AGB", ["Bedingungen", "Vertrag", "Rücktritt", "Storno"], "agb.html"),
    ]
    if SEITENINHALTE.get("wenn_etwas_schiefgeht"):
        eintraege.append(("Wenn etwas nicht wie geplant läuft",
                          ["Garantie", "Gewährleistung", "Komplikation", "Beschwerde", "Notfall", "Revision"],
                          SEITE_SCHIEFGEHT))
    if SEITENINHALTE.get("reiseablauf"):
        eintraege.append(("Ihre Reise", ["Ablauf", "Reise", "Hotel", "Transfer", "Flug", "Aufenthalt"], SEITE_REISE))
    if SEITENINHALTE.get("gesamtkosten"):
        eintraege.append(("Was es kostet", ["Kosten", "Preis", "Gesamtkosten", "Budget", "Anzahlung"], SEITE_KOSTEN))
    if BERATUNG_ANLIEGEN:
        eintraege.append(("Was passt zu mir?",
                          ["Anliegen", "Beratung", "Vergleich", "Unterschied", "welche Behandlung"],
                          SEITE_BERATUNG))
    if GLOSSAR_SORTIERT:
        # Jeder Fachbegriff ist ein Synonym der Glossarseite. Wer «Graft»
        # eintippt, landet damit bei der Erklaerung und nicht im Nichts.
        eintraege.append(("Fachbegriffe",
                          ["Glossar", "Lexikon", "Begriff", "Abkürzung"]
                          + [b for b, _ in GLOSSAR_SORTIERT],
                          SEITE_GLOSSAR))
    return [{"n": name, "t": "", "k": "Seite", "s": syn, "d": "", "u": url}
            for name, syn, url in eintraege]


def build_suchindex():
    """Kleiner Index fuer eine Suche ueber alle 101 Behandlungen.

    Befund inhalt B11: null Suchfelder bei 101 Behandlungen, und am Handy
    fuehrt kein Weg vom Menue zu einer einzelnen Behandlung. Die Daten liegen
    bereit — data/behandlungen.json traegt seit Welle 1 «synonyme» (198
    Begriffe zu 53 Behandlungen: «HIFU», «Rhinoplastik», «Tummy Tuck»,
    «Grafts»). Das Suchfeld selbst gehoert in die Kopfleiste und damit in die
    Bahn navigation; hier entsteht nur der Index, den sie braucht.
    """
    eintraege = [
        {
            "n": b["name_de"],
            "t": b.get("name_tr", ""),
            "k": k["name_de"],
            "s": [x for x in b.get("synonyme", []) if echt(x)],
            "d": BESCHREIBUNGEN.get(b["slug"], ""),
            "u": f"behandlungen/{k['id']}/{b['slug']}.html",
        }
        for k in kats() for g in k["gruppen"] for b in g["behandlungen"]
    ] + suchindex_seiten()
    ziel = SITE / "assets" / "suche.json"
    ziel.parent.mkdir(parents=True, exist_ok=True)
    ziel.write_text(json.dumps(eintraege, ensure_ascii=False, separators=(",", ":")) + "\n")
    print(f"Suchindex: {len(eintraege)} Behandlungen, "
          f"{sum(len(e['s']) for e in eintraege)} Synonyme, {ziel.stat().st_size // 1024} KB")


def build_meta_files():
    (SITE / "robots.txt").write_text(
        "User-agent: *\nAllow: /\n"
        f"Sitemap: {BASE_URL}/sitemap.xml\n"
    )
    heute = date.today().isoformat()
    urls = ""
    for pfad in sorted(PAGES):
        # Die Startseite wiegt am schwersten, die Detailseiten aendern sich am
        # oeftesten. Mehr sagt eine Sitemap nicht sinnvoll aus.
        prio = "1.0" if pfad == "index.html" else ("0.8" if pfad.endswith("/index.html") else "0.6")
        urls += (
            f"  <url><loc>{kanonisch(pfad)}</loc>"
            f"<lastmod>{heute}</lastmod><changefreq>monthly</changefreq>"
            f"<priority>{prio}</priority></url>\n"
        )
    (SITE / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + urls + "</urlset>\n"
    )
    (SITE / ".nojekyll").write_text("")


# ------------------------------------------------------------ Sprachdateien
def deutsche_datentexte():
    """Die deutschen Texte, die aus glossar.json und beratung.json kommen.

    Dieselbe Funktion nutzt scripts/pruefe_katalog_aktuell.py, um die Kopie in
    data/i18n/seiten-de.json gegen die Quelle zu pruefen.
    """
    out = {}
    for begriff, e in GLOSSAR_SORTIERT:
        out[glossar_schluessel(e["slug"], "begriff")] = begriff
        out[glossar_schluessel(e["slug"], "kurz")] = e["kurz"]
        if e["lang"]:
            out[glossar_schluessel(e["slug"], "lang")] = e["lang"]
    for a in BERATUNG_ANLIEGEN:
        out["beratung.anliegen." + a["id"] + ".titel"] = echt(a["titel"])
        text = echt(a.get("text"))
        if text:
            out["beratung.anliegen." + a["id"] + ".text"] = text
    for gid, g in VERGLEICH_GRUPPEN.items():
        vslug = vergleich_slug(gid)
        titel = echt(g.get("titel"))
        hilfe = echt(g.get("entscheidungshilfe"))
        if titel:
            out["beratung.vergleich." + vslug + ".titel"] = titel
        if hilfe:
            out["beratung.vergleich." + vslug + ".hilfe"] = hilfe
    return out


def zusammengesetzte_schluessel(texte, lang="de"):
    """Baut die Schluessel, die aus einer Vorlage und einem Katalogtext entstehen.

    Die Vorlagen (…tpl…) werden beim Bauen ersetzt, nicht im Browser. Im
    JavaScript gibt es also keine Platzhalter-Syntax.

    Zwei Dinge sind hier bewusst anders als frueher:
    1. Fuer Deutsch ist data/beschreibungen.json die Quelle, nicht
       katalog-de.json. Die Beschreibungen wurden dort entschaerft (Befund
       inhalt B13); im Katalog steht teilweise noch die alte Fassung. Ohne
       diesen Vorrang stuende nach einem Sprachwechsel zurueck auf Deutsch
       wieder «dauerhafte Haarentfernung» auf der Seite.
    2. Jede Meta-Beschreibung laeuft durch kurzfassen(), sonst holt der
       Sprachumschalter die zu langen Fassungen zurueck (Befund technik B13).
    """
    neu = {}
    # Fachbegriffe und Beratungstexte: fuer Deutsch sind data/glossar.json und
    # data/beratung.json die Quelle, genau wie beschreibungen.json weiter
    # unten. In seiten-de.json steht nur eine Kopie fuer den Abgleich der
    # Uebersetzer (scripts/pruefe_sprachdatei.py); aendert jemand die
    # Datendatei, gewinnt hier die Datendatei, und die Kopie kann nie
    # veraltet auf der Seite landen. scripts/pruefe_katalog_aktuell.py meldet
    # die Abweichung.
    if lang == "de":
        neu.update(deutsche_datentexte())
    vorlagen = {
        "beh_title": texte.get("meta.tpl.beh.title", "{name} in Istanbul | ETA"),
        "beh_desc": texte.get("meta.tpl.beh.desc", "{name}: {desc} Beratung auf Deutsch, Behandlung in unserer Partnerklinik in Istanbul."),
        "kat_title": texte.get("meta.tpl.kat.title", "{name} in Istanbul | ETA"),
        "kat_desc": texte.get("meta.tpl.kat.desc", "{name}: {teaser} Deutschsprachige Beratung, Behandlung in unserer Partnerklinik in Istanbul."),
        "beh_ph": texte.get("seite.tpl.behandlung.formular.nachricht.ph", "Frage zu {name}"),
    }
    for k in kats():
        kid = k["id"]
        name = texte.get("kat." + kid + ".name", kat_name(kid))
        teaser = texte.get("kat." + kid + ".teaser", kat_teaser(kid))
        neu["meta.kat-" + kid + ".title"] = vorlagen["kat_title"].replace("{name}", name)
        neu["meta.kat-" + kid + ".desc"] = kurzfassen(
            vorlagen["kat_desc"].replace("{name}", name).replace("{teaser}", teaser)
        )
        for g in k["gruppen"]:
            for b in g["behandlungen"]:
                slug = b["slug"]
                b_name = texte.get("beh." + slug + ".name", b["name_de"])
                if lang == "de":
                    b_desc = BESCHREIBUNGEN.get(slug, "") or texte.get("beh." + slug + ".desc", "")
                    neu["beh." + slug + ".desc"] = b_desc
                else:
                    b_desc = texte.get("beh." + slug + ".desc", BESCHREIBUNGEN.get(slug, ""))
                neu["meta.beh-" + slug + ".title"] = vorlagen["beh_title"].replace("{name}", b_name)
                if lang == "de":
                    # Wie im HTML: ohne den Namen davor, der drei Zeilen hoeher im Titel steht.
                    roh = f"{b_desc} Beratung auf Deutsch, Klinik in Istanbul."
                else:
                    roh = vorlagen["beh_desc"].replace("{name}", b_name).replace("{desc}", b_desc)
                neu["meta.beh-" + slug + ".desc"] = kurzfassen(roh)
                neu["seite.behandlung.formular.nachricht.ph." + slug] = vorlagen["beh_ph"].replace("{name}", b_name)
    return neu


# Die vier Toepfe je Sprache, in der Reihenfolge, in der sie sich ueberschreiben:
#   seiten    Seitentexte, Formulare, feste Texte des Generators
#   katalog   Kategorien, Gruppen, Behandlungsnamen und -beschreibungen
#   behdaten  die Werte aus data/behandlungsdaten.json
#   inhalte   die Werte aus den sechs uebrigen Redaktionsdateien
I18N_TOEPFE = ["seiten", "katalog", "behdaten", "inhalte"]


def abgeleiteter_wert(funktion, roh_de, wert_lang):
    """Legt die Umformung, die der Generator auf den deutschen Wert anwendet,
    auf denselben Wert in einer anderen Sprache.

    Beide Umformungen sind auf Deutsch getrimmt: aufenthalt_kurz() streicht
    «in Istanbul», ohne_redaktionsnotiz() die Saetze, die sich an ETA richten.
    Auf Englisch, Tuerkisch und Arabisch greifen die Muster nicht.

    Bei aufenthalt_kurz() ist das harmlos: dort bleibt hoechstens ein
    «in Istanbul» stehen, das neben dem Etikett «Aufenthalt in Istanbul» nur
    doppelt ist. Bei einer Redaktionsnotiz waere es ein Schaden — «The range is
    to be entered by ETA» hat auf einer Kundenseite nichts verloren. Deshalb
    wird dort, wo das Deutsche ganze Schlusssaetze verloren hat, dieselbe Zahl
    Schlusssaetze auch in der Uebersetzung gestrichen. Steckte die Notiz im
    Deutschen nur als Nebensatz drin, laesst sie sich in der Uebersetzung nicht
    sicher finden: dann kommt None zurueck, der Schluessel wird
    zurueckgehalten, und es bleibt der bereits bereinigte deutsche Text stehen.
    """
    kurz_de = funktion(roh_de)
    if kurz_de is None:
        return None
    neu = funktion(wert_lang)
    if neu is None or kurz_de == echt(roh_de):
        # Auf Deutsch war nichts zu kuerzen, also auch sonst nirgends.
        return neu
    if neu != echt(wert_lang) or funktion is not ohne_redaktionsnotiz:
        # Die Regel hat auch hier gegriffen — oder es geht um «in Istanbul»,
        # das stehen bleiben darf.
        return neu
    weg = len(saetze(echt(roh_de))) - len(saetze(kurz_de))
    if weg <= 0:
        return None
    return echt("".join(saetze(neu)[:-weg]))


def build_sprachdateien():
    """Fuehrt die vier Quelltoepfe je Sprache zu docs/assets/i18n/<lang>.json zusammen.

    Fuer Deutsch muessen alle vier da sein — de.json ist die Rueckfallebene
    jeder anderen Sprache. Bei en, tr und ar entstehen die Uebersetzungen
    parallel: was noch fehlt, wird uebersprungen und auf der Konsole genannt,
    der Build laeuft weiter. Fuer die fehlenden Schluessel bleibt im Browser
    der deutsche Text stehen.
    """
    ziel = SITE / "assets" / "i18n"
    ziel.mkdir(parents=True, exist_ok=True)
    gebaut = []
    entfernt = []
    notiz = []
    for lang in SPRACHEN:
        dateien = [I18N_QUELLE / f"{topf}-{lang}.json" for topf in I18N_TOEPFE]
        fehlend = [d.name for d in dateien if not d.exists()]
        if fehlend and lang == "de":
            raise SystemExit("Abbruch: " + ", ".join(fehlend) + " fehlt, de.json ist Pflicht.")
        if fehlend:
            print(f"i18n: {lang} ohne {', '.join(fehlend)} — dort bleibt der deutsche Text stehen.")
        texte = {}
        for datei in dateien:
            if datei.exists():
                texte.update(json.loads(datei.read_text()))
        if not texte:
            print(f"i18n: {lang} übersprungen, keine einzige Quelldatei vorhanden.")
            continue
        texte.update(zusammengesetzte_schluessel(texte, lang))
        # Werte, die der Generator vor der Ausgabe kuerzt, muessen auch in der
        # Sprachdatei gekuerzt ankommen — sonst schoebe der Umschalter die
        # Rohfassung zurueck auf die Seite.
        for schluessel, funktion in DATEN_ABGELEITET.items():
            if schluessel not in texte:
                continue
            wert_ = abgeleiteter_wert(funktion, DATEN_TEXTE[schluessel], texte[schluessel])
            if wert_ is not None:
                texte[schluessel] = wert_
                continue
            del texte[schluessel]
            if schluessel in VERWENDETE_SCHLUESSEL:
                ZURUECKGEHALTEN.add(schluessel)
                notiz.append(f"{lang}:{schluessel}")
        # Kein Klammer-Platzhalter verlaesst den Generator — auch nicht ueber
        # eine Sprachdatei. Sonst schiebt der Umschalter «[X TAGE]» zurueck in
        # eine Seite, aus der der Generator die Zeile entfernt hat.
        for schluessel in sorted(texte):
            wert_ = texte[schluessel]
            if not isinstance(wert_, str) or not KLAMMER.search(wert_):
                continue
            del texte[schluessel]
            if schluessel in VERWENDETE_SCHLUESSEL:
                entfernt.append(f"{lang}:{schluessel}")
                ZURUECKGEHALTEN.add(schluessel)
        (ziel / f"{lang}.json").write_text(
            json.dumps(texte, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        gebaut.append(f"{lang} ({len(texte)})")
    print("i18n: gebaut " + ", ".join(gebaut))
    if entfernt:
        print(
            f"i18n: {len(entfernt)} Übersetzungen mit Klammer-Platzhalter zurückgehalten, "
            "dort bleibt der deutsche Text stehen:"
        )
        for e in entfernt:
            print("  - " + e)
    if notiz:
        # Diese Uebersetzungen tragen eine Redaktionsnotiz, die sich nicht
        # eindeutig herausschneiden liess. Statt «to be entered by ETA» auf
        # einer Kundenseite bleibt dort der deutsche, bereits bereinigte Text.
        sprachen = sorted({e.split(":", 1)[0] for e in notiz})
        print(f"i18n: {len(notiz)} Übersetzungen mit Redaktionsnotiz zurückgehalten "
              f"({', '.join(sprachen)}), dort bleibt der deutsche Text stehen.")


ZURUECKGEHALTEN = set()


def pruefe_schluessel():
    """Warnt, wenn das HTML einen Schluessel nutzt, den docs/assets/i18n/de.json nicht kennt."""
    de_datei = SITE / "assets" / "i18n" / "de.json"
    if not de_datei.exists():
        return
    vorhanden = set(json.loads(de_datei.read_text()))
    fehlend = sorted(VERWENDETE_SCHLUESSEL - vorhanden - ZURUECKGEHALTEN)
    if fehlend:
        print(f"i18n: WARNUNG, {len(fehlend)} Schlüssel fehlen in de.json:")
        for k in fehlend[:40]:
            print("  - " + k)
        if len(fehlend) > 40:
            print(f"  … und {len(fehlend) - 40} weitere")


# Was nie ausgeliefert wird. Bisher wanderte static/assets vollstaendig nach
# docs/ — darunter ein 12-MB-Video, das keine einzige Seite einbindet, und die
# 30 MB Originalbilder, von denen nur die Varianten gebraucht werden
# (Befund technik B11).
NICHT_AUSLIEFERN_ORDNER = {"video"}
IMMER_AUSLIEFERN = {"eta-logo.png", "favicon.png"}


def ueberspringen(ordner, namen):
    """ignore-Funktion fuer copytree: nennt die Dateien, die drin bleiben."""
    ordner = Path(ordner)
    raus = set()
    for name in namen:
        pfad = ordner / name
        if pfad.is_dir():
            if name in NICHT_AUSLIEFERN_ORDNER:
                raus.add(name)
            continue
        if name.endswith("-old.jpg") or name == "abgeleitet.json":
            raus.add(name)
            continue
        if name in IMMER_AUSLIEFERN:
            continue
        # Originalbild, von dem es Varianten gibt -> wird nicht mehr gebraucht.
        try:
            schluessel = str(pfad.relative_to(STATIC / "assets" / "img"))
        except ValueError:
            continue
        if schluessel in BILD_VARIANTEN:
            raus.add(name)
    return raus


def pruefe_daten():
    """Bricht mit einer lesbaren Meldung ab statt mit einem nackten KeyError.

    Eine neue Kategorie in behandlungen.json ohne Symbol oder Teaser beendete
    den Build bisher wortlos (Befund technik B12).
    """
    fehlend = []
    for k in kats():
        kid = k["id"]
        if kid not in KAT_ICONS:
            fehlend.append(f"{kid}: Symbol in KAT_ICONS")
        for schluessel in ("name", "teaser", "intro"):
            if "kat." + kid + "." + schluessel not in KATALOG_TEXTE:
                fehlend.append(f"{kid}: Text kat.{kid}.{schluessel} in katalog-de.json")
    if fehlend:
        raise SystemExit("Abbruch, Kategorie unvollständig:\n  - " + "\n  - ".join(fehlend))


def build_csp():
    """Traegt die Hashes aller Inline-Skripte in die CSP von vercel.json ein.

    Die CSP erlaubt nur script-src 'self'. Ein Inline-Skript — etwa die Sprachvorwahl,
    die vor dem ersten Bildaufbau laufen muss — wird sonst vom Browser blockiert und
    erzeugt auf jeder Seite einen Konsolenfehler. Das faellt lokal nicht auf, weil die
    CSP erst von Vercel gesetzt wird. Deshalb rechnet der Build die Hashes selbst aus:
    aendert sich ein Skript, aendert sich der Hash automatisch mit.
    """
    import base64
    import hashlib

    hashes = []
    for datei in sorted(SITE.rglob("*.html")):
        html = datei.read_text(encoding="utf-8")
        for treffer in re.finditer(r"<script(?![^>]*\bsrc=)([^>]*)>(.*?)</script>", html, re.S):
            if "ld+json" in treffer.group(1):
                continue  # JSON-LD ist Datei-Inhalt, kein ausgefuehrtes Skript
            roh = hashlib.sha256(treffer.group(2).encode("utf-8")).digest()
            wert = "'sha256-" + base64.b64encode(roh).decode() + "'"
            if wert not in hashes:
                hashes.append(wert)

    pfad = ROOT / "vercel.json"
    inhalt = pfad.read_text(encoding="utf-8")
    neu = "script-src 'self'" + ("" if not hashes else " " + " ".join(sorted(hashes)))
    ersetzt, anzahl = re.subn(r"script-src 'self'[^;\"]*", neu, inhalt)
    if anzahl != 1:
        raise SystemExit(f"Abbruch: script-src in vercel.json {anzahl} mal gefunden, erwartet 1.")
    if ersetzt != inhalt:
        pfad.write_text(ersetzt, encoding="utf-8")
    print(f"csp: {len(hashes)} Inline-Skripte freigegeben")



def main():
    global CSS_VERSION, JS_VERSION
    pruefe_daten()
    CSS_VERSION = datei_version("css/style.css")
    JS_VERSION = datei_version("js/main.js")
    if SITE.exists():
        shutil.rmtree(SITE)
    SITE.mkdir(parents=True)
    shutil.copytree(ROOT / "static" / "assets", SITE / "assets", ignore=ueberspringen)
    build_index()
    build_behandlungen_index()
    build_kategorien()
    build_details()
    build_partnerklinik()
    build_finanzierung()
    build_faq()
    build_kontakt()
    build_rechtliches()
    build_schiefgeht()
    build_reise()
    build_kosten()
    build_team()
    build_glossar()
    build_beratung()
    build_suchindex()
    build_meta_files()
    build_404()
    build_sprachdateien()
    pruefe_schluessel()
    build_csp()
    print(f"ok: {len(PAGES)} Seiten generiert in {SITE}, {len(VERWENDETE_SCHLUESSEL)} i18n-Schlüssel im HTML")


if __name__ == "__main__":
    main()

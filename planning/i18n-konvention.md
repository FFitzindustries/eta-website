# Sprachumschaltung ETA — verbindliche Konvention

Alle Agenten halten sich exakt an dieses Dokument. Es ist die einzige Absprache
zwischen den parallel laufenden Arbeiten.

## Ziel
Die Website hat vier Sprachen: `de` (Original), `en`, `tr`, `ar`.
Heute wird beim Umschalten nur der Header übersetzt, weil nur ~20 Stellen
`data-i18n` tragen. Am Ende muss **jeder sichtbare Text** umschalten — Seitentexte,
Formulare, alle Behandlungsseiten, Titel, Meta-Beschreibungen und die Rechtstexte.

Kein Umbau auf Sprach-URLs. Es bleibt bei einer Seitenfassung, die im Browser
per JavaScript umgeschaltet wird.

## Wo die Texte liegen

Quelldateien (gepflegt, im Git):

    data/i18n/seiten-de.json     Seitentexte, Formulare, Rechtstexte  (Agent fi-eta-generator)
    data/i18n/seiten-en.json     dito, Englisch
    data/i18n/seiten-tr.json     dito, Türkisch
    data/i18n/seiten-ar.json     dito, Arabisch
    data/i18n/katalog-de.json    Kategorien, Gruppen, Behandlungen    (liegt bereits vor, 232 Schlüssel)
    data/i18n/katalog-en.json    dito, Englisch
    data/i18n/katalog-tr.json    dito, Türkisch
    data/i18n/katalog-ar.json    dito, Arabisch

`scripts/build_site.py` führt beim Bauen `seiten-<lang>.json` und
`katalog-<lang>.json` zu je einer Datei zusammen und schreibt sie nach

    docs/assets/i18n/de.json  en.json  tr.json  ar.json

Format überall: **flaches** JSON-Objekt, Schlüssel → Text. Keine Verschachtelung.

## Schlüssel-Schema

    nav.*                     Navigation
    hero.*                    Hero der Startseite
    footer.*                  Fusszeile
    banner.other_lang         Hinweisbanner
    kat.<kat-id>.name         Kategoriename        z. B. kat.zaehne.name
    kat.<kat-id>.teaser       Kurztext auf der Startseite
    kat.<kat-id>.intro        Einleitung der Kategorieseite
    gruppe.<kat-id>.<slug>.name   Gruppenname innerhalb einer Kategorie
    beh.<slug>.name           Behandlungsname      z. B. beh.stirn-botox.name
    beh.<slug>.desc           Behandlungsbeschreibung
    seite.<seite>.<abschnitt>.<element>
                              alles Übrige, z. B. seite.index.usp.1.titel,
                              seite.kontakt.formular.name.label,
                              seite.agb.absatz.3
    meta.<seite>.title        Inhalt von <title>
    meta.<seite>.desc         Inhalt der Meta-Beschreibung

Schlüssel sind kleingeschrieben, mit Punkten getrennt, ohne Umlaute.
Ein Schlüssel existiert in **allen vier** Sprachdateien, mit identischer Schreibweise.

## Markierung im HTML

Der Generator gibt weiterhin **deutsches** HTML aus und setzt zusätzlich:

    Textinhalt:   <h2 data-i18n="seite.index.usp.titel">Deutscher Text</h2>
    Attribute:    <input data-i18n-attr="placeholder:seite.kontakt.formular.name.ph">
                  mehrere durch Semikolon: "placeholder:a.b;aria-label:c.d"
    Titel:        <title data-i18n="meta.index.title">…</title>
    Meta:         <meta name="description" data-i18n-attr="content:meta.index.desc" content="…">

Regeln:
- `data-i18n` ersetzt den **gesamten** Textinhalt des Elements. Deshalb nur auf
  Elemente setzen, die reinen Text enthalten. Steht Text neben einem Symbol oder
  einem Link, kommt der Text in ein eigenes `<span>` und das `<span>` bekommt die
  Markierung.
- Eigennamen bleiben unübersetzt und werden **nicht** markiert: ETA, European Turkey Asia,
  Riverside Beauty, St. Margrethen, Istanbul, WhatsApp, Instagram, Facebook, Messenger,
  Telefonnummern, E-Mail-Adressen.
- Bestehende Schlüssel (nav.*, hero.*, footer.tagline, contact.region, banner.other_lang)
  behalten ihre heutigen Namen. Nichts davon umbenennen.

## Arbeitsteilung — wer fasst was an

Jeder Agent fasst ausschliesslich seine eigenen Dateien an. Andere Dateien werden
gelesen, aber nie geändert.

    fi-eta-motor       static/assets/js/main.js, static/assets/css/style.css
    fi-eta-generator   scripts/build_site.py, data/i18n/seiten-de.json
    fi-eta-en          data/i18n/katalog-en.json  (später seiten-en.json)
    fi-eta-tr          data/i18n/katalog-tr.json  (später seiten-tr.json)
    fi-eta-ar          data/i18n/katalog-ar.json  (später seiten-ar.json)

`docs/` ist reines Bauergebnis und wird **nie** von Hand bearbeitet.
`static/assets/` ist die Quelle, die der Generator nach `docs/assets/` kopiert.

## Sprache der Arbeit
Alle Commit-Nachrichten, Kommentare und Berichte auf Deutsch.

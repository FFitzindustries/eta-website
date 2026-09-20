# Sprachauswahl pflegen

Die Website läuft in vier Sprachen: `de` (Original), `en`, `tr`, `ar`. Jeder
sichtbare Text trägt einen Schlüssel, die Wörterbücher werden beim Umschalten
nachgeladen. **Fehlt ein Schlüssel, bleibt der deutsche Text stehen** — neue
Inhalte brechen also nie etwas, sie erscheinen nur vorerst deutsch.

## Wenn du Inhalte geändert hast

Die Inhalte stehen in den Redaktionsdateien unter `data/`. Nach jeder Änderung:

    python3 scripts/i18n_daten_extrahieren.py --schreiben

Das gleicht `data/i18n/behdaten-de.json` und `inhalte-de.json` an die Quellen
an und schreibt die Liste der neu zu übersetzenden Schlüssel nach
`data/i18n/daten-nachzuziehen.txt`. Diese Schlüssel dann in den `-en`, `-tr`
und `-ar`-Fassungen derselben Töpfe nachziehen.

Für den Behandlungskatalog (Namen, Kurzbeschreibungen) gilt dasselbe mit:

    python3 scripts/pruefe_katalog_aktuell.py --schreiben

## Wenn du neue Texte in den Generator geschrieben hast

    python3 scripts/pruefe_i18n.py

Punkt **[3]** nennt Schlüssel, die im HTML stehen, aber im Wörterbuch fehlen —
die müssen nach `data/i18n/seiten-de.json`.
Punkt **[5]** nennt sichtbare Textstellen ohne Auszeichnung. Sie gehören über
`i18n(key)` beziehungsweise `i18n_attr(spec)` ausgezeichnet.
Punkt **[6]** nennt Schlüssel, deren Wörterbuchtext nicht mehr zum HTML passt.
Das ist heimtückisch: Beim Zurückschalten auf Deutsch erscheint dann die alte
Fassung. Wörterbuch an das HTML angleichen.

Erwartet bleiben darf nur eine Stelle: das Honigtopf-Feld
«Website (bitte leer lassen)». Es ist für Menschen unsichtbar und soll für
Spam-Roboter unauffällig aussehen.

## Sprachdateien prüfen

    python3 scripts/pruefe_sprachdatei.py en|tr|ar

Prüft alle vier Töpfe (`katalog`, `seiten`, `behdaten`, `inhalte`) gegen die
deutsche Vorlage: fehlende, überzählige, leere und unübersetzt gebliebene
Einträge sowie zu lange Titel und Meta-Beschreibungen.

## Im Browser gegenprüfen

    cd docs && python3 -m http.server 8899 --bind 127.0.0.1 &
    node scripts/pruefe_sprachen.mjs
    node scripts/pruefe_sprachen.mjs https://eta-website-livid.vercel.app

Braucht Playwright: ein Projekt mit installiertem Playwright per
`node_modules`-Symlink neben das Skript legen.

Der Test schaltet jede Seite durch alle Sprachen und prüft Textinhalt, Titel,
Meta-Beschreibung, `lang`, `dir` und ob das Zurückschalten auf Deutsch die
Originaltexte wiederherstellt. Gemeldet werden nur Stellen, die deutsch
geblieben sind — Fachbegriffe (Veneer, SMAS, Graft) und Eigennamen (Klinikname,
Adresse) sind dabei normal.

## Worauf bei medizinischen Texten zu achten ist

Die deutschen Beschreibungen sind bewusst zurückhaltend formuliert: kein
«zuverlässig», dafür Hinweise darauf, dass die Wirkung nachlässt, dass mehrere
Sitzungen nötig sind oder dass ein Ergebnis nicht zugesagt werden kann.

**Jede Übersetzung muss diese Einschränkungen mittragen.** Eine
fremdsprachige Fassung, die mehr verspricht als die deutsche, ist ein Schaden —
nicht nur rechtlich. Dasselbe gilt für Risiken und Gegenanzeigen: Was auf
Deutsch als Notfall beschrieben ist, muss in jeder Sprache als Notfall
erkennbar sein.

Ein brauchbarer Schnelltest: Keine Übersetzung darf weniger Sätze haben als
das deutsche Original. Fehlt ein Satz, fehlt meist die Einschränkung.

## Texte, die erst im Browser entstehen

Statusmeldungen des Formulars und die vorbereitete WhatsApp-Nachricht stehen
nicht im HTML. Sie holen ihre Fassung in `static/assets/js/main.js` über

    t("js.status.eingegangen", "Deutscher Rückfalltext")

Der zweite Wert erscheint, solange der Schlüssel fehlt. Die Schlüssel beginnen
mit `js.` und stehen in `data/i18n/seiten-*.json`.

Die behandlungsspezifische WhatsApp-Nachricht läuft über `data-wa-key` am
Knopf; `main.js` baut den Link bei jedem Sprachwechsel neu auf.

## Schlüsselschema

    nav.* hero.* footer.*          Rahmen
    kat.* gruppe.* beh.*           Behandlungskatalog
    seite.<seite>.<abschnitt>      Seitentexte aus dem Generator
    meta.<seite>.title / .desc     Titel und Meta-Beschreibung
    js.*                           Texte, die im Browser entstehen
    daten.<datei>.<pfad>           Werte aus den Redaktionsdateien,
                                   automatisch erzeugt — nicht von Hand ändern

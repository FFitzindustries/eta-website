# Ausfüllhilfe

> Arbeitsblatt für Ferry und den Kunden. Hier steht, welche Angaben der Website noch
> fehlen, warum jede davon zählt und wo sie hingehört. **Erzeugt am 2026-09-20 aus dem
> tatsächlichen Stand der Dateien unter `data/`.** Wer etwas einträgt, kann
> `python3 scripts/build_site.py` laufen lassen und sieht das Ergebnis sofort.

**Grundregel:** Ein leeres Feld ist kein Problem — der Generator gibt die Zeile dann
einfach nicht aus. Ein erfundener Wert ist ein Problem. Lassen Sie lieber etwas leer,
als zu schätzen. Das gilt besonders für Preise, medizinische Zahlen, Arztnamen und
Zertifikate.

---

## Stufe 1 — ohne das geht die Seite nicht online

Diese Angaben fehlen heute und sind rechtlich oder für das Vertrauen zwingend.

### 1.1 Firmendaten (Impressum, Datenschutz, AGB)

Steht in `data/recht.json` → `firma`. Heute zeigt das Impressum an vier Stellen
Platzhalter in eckigen Klammern. Wer auf einer Seite mit Gesundheitsdaten
«[HR-NUMMER]» liest, schliesst daraus: dieses Unternehmen ist nicht greifbar.

| Feld | warum es zählt |
|---|---|
| `name` | Ohne Firmennamen gibt es keinen Vertragspartner. |
| `rechtsform` | Teil der gesetzlichen Impressumspflicht. |
| `strasse / plz / ort` | Eine Schweizer Adresse ist für die Zielgruppe der wichtigste Einzelbeleg dafür, dass es ETA wirklich gibt. |
| `hr_nummer / uid` | Nachschlagbar im Handelsregister. Der Zefix-Link ist der einzige Beleg, den ein Zweifelnder selbst überprüfen kann. |
| `hr_link` | Direkter Link auf den Zefix-Eintrag — kostet nichts und wirkt mehr als jedes Adjektiv. |
| `vertretung` | Wer für das Unternehmen unterschreibt. Gesetzlich gefordert. |
| `datenschutz_email` | Adresse für Auskunfts- und Löschbegehren nach revDSG. |
| `mwst_nummer` | Falls mehrwertsteuerpflichtig. |

### 1.2 Anzahlung und Zahlungsbedingungen

Steht in `data/recht.json` → `agb` → Ziffer 4 und in
`data/seiteninhalte.json` → `gesamtkosten`. Heute steht «[BETRAG]» an drei Stellen im
Erzeugnis — unter anderem **direkt unter dem Absendeknopf des Kontaktformulars**, also
an der Stelle mit dem grössten Zögern.

- Höhe der Anzahlung (Betrag oder Prozentsatz)
- Zahlungsmittel und Währung
- Zeitpunkt und Ort der Restzahlung
- Was bei Storno innerhalb von 72 Stunden mit der Anzahlung geschieht
- Name des Ratenpartners (steht heute als «[ANBIETER]» auf der Finanzierungsseite)

### 1.3 Gewährleistung und Revision der Partnerklinik

Steht in `data/seiteninhalte.json` → `wenn_etwas_schiefgeht` → `revision`.
**Das ist die dringendste Beschaffung in diesem ganzen Auftrag.** Die Wörter
«Komplikation», «Garantie», «Haftung», «Nachbesserung» kommen heute auf 116 Seiten
null-mal vor. Ohne diese Angaben bleibt die neue Seite «Wenn etwas nicht wie geplant
läuft» an ihrer wichtigsten Stelle leer.

- Was bessert die Klinik unter welchen Voraussetzungen nach?
- In welchem Zeitraum?
- Wer bezahlt Flug und Unterkunft bei einer Revision?
- Wer entscheidet, ob ein Revisionsfall vorliegt, und wie kann der Kunde widersprechen?
- Schriftlich einholen, nicht mündlich.

### 1.4 Nachsorge in der Schweiz

Steht in `data/seiteninhalte.json` → `nachsorge`. «Nachkontrolle im Rheintal bei
Riverside Beauty» steht viermal auf der Seite — ohne Umfang, ohne Zahl, ohne Link.

- Welche Leistungen, je Behandlungsart?
- Wie viele Termine, über welchen Zeitraum?
- Was ist im Fixpreis enthalten, was kostet extra?
- Was gilt für Wohnorte ausserhalb des Rheintals?
- **Was gilt für Kundinnen und Kunden aus Österreich und Deutschland?** Die Seite
  spricht sie ausdrücklich an; eine Nachsorge im Rheintal ist für sie keine Antwort.
- Website-Adresse von Riverside Beauty, damit der dreimal genannte Name verlinkt ist.

---

## Stufe 2 — ohne das bleibt die Seite eine Hülle

### 2.1 Preise

Steht in `data/behandlungsdaten.json`, Felder `preis_ab`, `preis_bis`, `preis_basis`.
**Alle 101 Behandlungen haben heute kein Preisfeld gefüllt.**
«CHF» kommt auf 116 Seiten null-mal vor. Wer drei Anbieter vergleicht, streicht den,
der keine Zahl nennt — nicht weil er teuer wäre, sondern weil es keinen Preis gibt.

Ein Preisband genügt («ab CHF x'xxx bis y'yyy»). Wichtig ist, **woran** der Preis hängt:
bei Haartransplantationen die Graft-Zahl, bei Zahnbehandlungen die Zahl der Zähne, bei
Fettabsaugungen die Zahl der Zonen. Das steht bei den ausgearbeiteten Behandlungen
schon in `preis_basis`.

**Reihenfolge:** Beginnen Sie mit diesen Behandlungen — sie sind bereits vollständig
ausgearbeitet und warten nur noch auf die Zahl:

- **haut-beauty:** `gesichts-botox`, `lippen-filler`, `hifu-facelifting`, `fadenlifting`, `prp-vampirlifting`, `stammzellen-therapie`, `lachs-dna-serum`, `laser-haarentfernung`, `fettweg-mesotherapie`
- **plastische-chirurgie:** `nasenkorrektur`, `facelifting`, `lidstraffung`, `ohrenkorrektur`, `brustvergroesserung`, `bruststraffung`, `fettabsaugung`, `bauchdeckenstraffung`
- **haartransplantation:** `fue-haartransplantation`, `dhi-haartransplantation`, `saphir-haartransplantation`, `haartransplantation-frauen`, `barthaartransplantation`, `augenbrauentransplantation`, `haar-prp`
- **zaehne:** `hollywood-smile`, `zahnimplantate`, `kronen-veneers`, `bleaching`

**Wenn die Klinik keine Preisnennung erlaubt:** Das ist vertraglich zu klären. Eine
Seite ganz ohne Zahl ist im Preisvergleichssegment nicht haltbar; ein «ab»-Preis ist das
Mindeste.

### 2.2 Medizinische Freigabe

**28 ausgearbeitete Behandlungstexte** und **15 Gruppen-Risikotexte**
tragen heute `"freigabe": "offen"`. Solange das so steht, sind es Redaktionsentwürfe
nach allgemeinem Fachwissen — nicht geprüfte medizinische Aufklärung.

Was zu tun ist: Die Partnerklinik liest die Texte gegen und bestätigt oder korrigiert
Dauer, Aufenthalt, Ausfallzeit, Betäubung, Risiken und Ausschlussgründe. Danach wird
`"freigabe"` auf `"erteilt"` gesetzt, mit Datum und Namen der freigebenden Person.

Betroffene Dateien:
- `data/behandlungsdaten.json` — je Behandlung
- `data/risiken-gruppen.json` — je Gruppe
- `data/glossar.json` — Fachbegriffe
- `data/seiteninhalte.json` → `wenn_etwas_schiefgeht` — besonders die Warnzeichenliste

### 2.3 Angaben zur Partnerklinik

Steht in `data/klinik.json`. Was belegt ist, steht dort mit Quelle und Abrufdatum. Was
fehlt:

| Feld | warum es zählt |
|---|---|
| Freigabe des Klinknamens | Der Name steht 101-mal in den Daten und auf keiner Seite. Vertraglich klären, ob ETA ihn nennen darf. |
| Adresse bestätigen | Die Klinik nennt selbst zwei verschiedene Postleitzahlen für dieselbe Adresse. |
| Zertifikatsnummer der Gesundheitstourismus-Bewilligung | Ein echtes, nachprüfbares türkisches Zertifikat — aber nur mit Nummer belegbar. |
| Ärzte: Einwilligung, Facharzttitel, Kammernummer, Foto | Vier Angaben je Person. Ohne alle vier wird die Person nicht ausgegeben. |
| Kapazität: OP-Säle, Betten, Gründungsjahr, Fallzahlen | Nicht öffentlich auffindbar. Zahlen schlagen Adjektive. |
| Fotos von Gebäude, Empfang, Behandlungsraum, Hotel | Rechtlich unbedenklich (anders als Vorher/Nachher) und beantworten «wo lande ich da eigentlich». |
| Prüfen, ob der 360°-Rundgang funktioniert | Der Knopf zeigt heute auf `href="#"`. |

**Nicht eintragen, solange kein Beleg vorliegt:** JCI und ISO. Eine Suche im offiziellen
JCI-Verzeichnis ergab am 2026-09-20 keinen Eintrag für diese Klinik; die Zuschreibung
stammt aus einem Drittanbieter-Verzeichnis. Eine unzutreffende Akkreditierungsangabe
wäre irreführende Werbung und im Schadensfall haftungsrelevant.

### 2.4 Team

Steht in `data/seiteninhalte.json` → `team`. ETA verspricht «eine feste Ansprechperson,
deutschsprachig». Diese Person hat heute weder Namen noch Gesicht. Zwei Porträts, zwei
Namen, zwei Sätze — der billigste grosse Vertrauensgewinn auf dieser Liste.

Solange `personen` leer ist, wird die Seite nicht erzeugt. Eine leere Team-Seite ist
schlechter als keine.

### 2.5 Kontaktwege neben WhatsApp

Steht in `data/seiteninhalte.json` → `kontaktwege`. Heute gibt es auf 116 Seiten null
`tel:`-Links und null `mailto:`-Links.

- Bestätigen, dass +41 76 412 21 22 auch telefonisch erreichbar ist — oder eine andere Nummer nennen
- Telefonische Erreichbarkeitszeiten
- Zugesicherte Reaktionszeit auf eine Anfrage
- **Echte Adressen der sozialen Netze oder Entscheid, die Links zu entfernen.** Instagram,
  Facebook und Messenger stehen heute 116-mal als `href="#"` im Fussbereich. Die
  Zielgruppe kommt laut Auftrag über Instagram und landet auf derselben Seite. Ein
  fehlender Link kostet nichts, ein toter kostet Glaubwürdigkeit.

---

## Stufe 3 — macht die Seite konkurrenzfähig

### 3.1 Restliche Behandlungstexte

**28 von 101 Behandlungen** haben eigenen Fliesstext, Risiken und FAQ.
Die übrigen **73** haben nur das Gerüst: Name, verwandte Behandlungen,
Gruppen-Risikotext und eine vorbelegte WhatsApp-Nachricht.

Das war eine bewusste Priorisierung: Die 28 ausgearbeiteten sind die, nach denen
gesucht wird. Für die restlichen 73 gilt: kurz lassen ist in Ordnung, solange sie nicht
beworben werden. Wer eine davon ausbauen will, braucht je Behandlung:

- `text.was_passiert` — was genau gemacht wird, 150–250 Wörter
- `text.fuer_wen` — für wen geeignet, für wen nicht
- `text.ablauf` und `text.danach`
- `risiken`, `nicht_geeignet_fuer`, `nachsorge`
- drei bis fünf behandlungsspezifische FAQ
- danach `"tiefe": "voll"` setzen

Die 15 Einträge unter «Medizinische Fachbereiche» sind Fachabteilungen, keine
Behandlungen. Sie brauchen keinen Ausbau — eher die Entscheidung, ob sie überhaupt
eigene Seiten bekommen.

### 3.2 Rechenbeispiel Gesamtkosten

Steht in `data/seiteninhalte.json` → `gesamtkosten` → `rechenbeispiel`. Sobald die
Preise vorliegen: eine gefragte Behandlung durchrechnen, inklusive Flug, Verpflegung
und Puffer. Nimmt den Verdacht versteckter Kosten weg — der entsteht genau dann, wenn
er nicht angesprochen wird.

### 3.3 Reisedetails

Steht in `data/seiteninhalte.json` → `reiseablauf`:

- Hotel: Name, Kategorie, Entfernung zur Klinik, Fotos mit Nutzungsrecht
- Fahrdienst: wer, erkennbar woran
- **Begleitperson: was kostet sie, was ist inbegriffen?** Steht heute zweimal als
  «[Details zu Hotel und Begleitperson folgen]» im Erzeugnis.
- Ob und wie ETA vor Ort begleitet: bei jedem Termin, nur beim Eingriff, telefonisch?
- Visumsangaben gegen die aktuellen EDA-Hinweise prüfen und mit Datum versehen

### 3.4 Belege statt Vorher/Nachher

Die Seite «Vorher / Nachher» wird bis auf Weiteres nicht mehr erzeugt — sie bestand aus
sechs leeren Kacheln. Was stattdessen trägt und heute schon beschaffbar ist:

- Fotos von Klinikgebäude, Empfang, Behandlungsraum und Hotel (rechtlich unbedenklich)
- Erfahrungsberichte mit Vorname, Alter, Kanton und Behandlungsjahr, schriftlich freigegeben
- Fallzahlen der Klinik
- Ein Reisebericht Tag für Tag mit echten Fotos

**Vor jedem Vorher/Nachher-Bild juristisch klären:** In Deutschland verbietet
§ 11 Abs. 1 Satz 3 Nr. 1 HWG die vergleichende Vorher-Nachher-Darstellung für operative
plastisch-chirurgische Eingriffe ausserhalb der Fachkreise. Der Katalog enthält 19
solcher Eingriffe, und die Seite spricht Deutschland ausdrücklich an. Eine Einwilligung
der Patientin genügt dafür nicht.

---

## Welche Datei wofür

| Datei | Inhalt |
|---|---|
| `data/behandlungen.json` | Katalogbaum: Kategorien, Gruppen, Namen, Menüsteuerung, Suchsynonyme |
| `data/behandlungsdaten.json` | Je Behandlung: Preis, Dauer, Risiken, Fliesstext, FAQ, WhatsApp-Text |
| `data/beschreibungen.json` | Der eine Einleitungssatz je Behandlung |
| `data/risiken-gruppen.json` | Risikotexte je Behandlungsgruppe |
| `data/klinik.json` | Partnerklinik: Adresse, Ärzte, Zertifikate, Belege |
| `data/recht.json` | Impressum, Datenschutz, AGB, Einwilligungstexte |
| `data/seiteninhalte.json` | Neue Seiten: Reiseablauf, Kosten, Team, Reise-FAQ, Nachsorge, Kontaktwege |
| `data/beratung.json` | Einstieg nach Anliegen, Vergleichstabellen |
| `data/glossar.json` | Fachbegriffe |

## Wie man etwas einträgt

1. Datei öffnen, Feld suchen, Wert eintragen.
2. Gültigkeit prüfen: `python3 -c "import json; json.load(open('data/DATEI.json'))"`
3. Neu bauen: `python3 scripts/build_site.py`
4. Ansehen. Das Feld erscheint jetzt auf der Seite — vorher war die Zeile gar nicht da.

**Bei medizinischen Angaben zusätzlich:** `"freigabe"` von `"offen"` auf `"erteilt"`
setzen und daneben festhalten, wer wann freigegeben hat.

# Empfehlung: Intimchirurgie und Aufhellungsbehandlungen im Hauptmenü

> Vorlage zur Entscheidung durch den Auftraggeber. Erstellt von der Bahn `daten`,
> 2026-09-20, zu Befund `inhalt.md` B14. **Diese Entscheidung soll nicht ein Agent
> allein treffen** — sie betrifft die Positionierung, nicht die Technik.

## Worum es geht

Das Aufklappmenü der Kopfleiste rendert heute alle 101 Behandlungen in **jede der 116
Seiten**. Betroffen sind unter anderem elf Einträge, die auf jeder Seite ungefragt im
Blick stehen:

**Intimchirurgie Mann (5):** Penisvergrösserung, Penis-Eigenfett-Behandlung (Stem Shot),
Penis-PRP-Behandlung, Korrektur der Penisverkrümmung, Stosswellentherapie (ESWT)
**Intimchirurgie Frau (2):** Schamlippenkorrektur (Labioplastik), Venushügel-Korrektur
**Aufhellungsbehandlungen (4):** Laser-Hautaufhellung, Achselaufhellung, Aufhellung
Intimbereich, Laser-Haaraufhellung

Nachweis aus dem Befund: `grep -c "Penisvergrösserung" docs/impressum.html` → 1. Der
Eintrag steht also auch im Impressum, auf der Startseite und auf der Seite zum
Zahnbleaching.

## Warum das ein Problem ist

Das ist keine Frage der Prüderie, sondern der Positionierung. Der Befund beschreibt den
Fall präzise: Eine 42-jährige Interessentin aus Zürich, die eine Bauchdeckenstraffung
erwägt — hochpreisig, angstbesetzt —, öffnet das Menü «Plastische Chirurgie» und liest
in derselben Spalte «Penisvergrösserung». Das Segment ist hochpreisige Medizin, und ein
ungefiltertes Gesamtsortiment im Dauer-Sichtfeld zieht die Anmutung Richtung
Katalogversand.

Dazu kommt: **Viele Besucher schauen die Seite nicht allein an.** Am Küchentisch, im
Grossraumbüro, im Zug. Ein Menü, das man nicht öffnen mag, wenn jemand danebensitzt, ist
ein Menü, das seltener geöffnet wird.

Bei den vier Aufhellungsbehandlungen kommt ein zweites Thema dazu: Hautaufhellung ist im
europäischen Markt reputationsbelastet, unabhängig von der medizinischen Bewertung der
einzelnen Behandlung.

## Was ich empfehle

**Variante A — Menü kürzen (empfohlen).**

Das Aufklappmenü zeigt je Kategorie die sechs bis acht gefragtesten Behandlungen plus
einen Eintrag «Alle … ansehen». Alle übrigen Behandlungen — einschliesslich der
Intimchirurgie — bleiben vollständig im Katalog und sind über die Kategorieseite und
über die Suche erreichbar. Nichts wird versteckt, nichts entfernt.

Ich habe das bereits in den Daten vorbereitet: `data/behandlungen.json` trägt jetzt je
Behandlung ein Feld `im_menue`. Gesetzt sind 32 von 101 Behandlungen:

| Kategorie | im Menü | gesamt |
|---|---|---|
| Haut & Beauty | 8 | 49 |
| Plastische Chirurgie | 8 | 19 |
| Haartransplantation | 6 | 10 |
| Zähne | 6 | 8 |
| Medizinische Fachbereiche | 4 | 15 |

Für den Generator ist das eine Filterzeile in `nav_kat_dropdowns()`.

**Warum diese Variante:**

1. Sie löst zugleich ein zweites, grösseres Problem. Laut Befund `inhalt.md` B11 sind
   die 55 Behandlungslinks im Aufklappmenü **am Handy gar nicht erreichbar** — das Panel
   ist `display:none`. Es gibt dort heute keinen Weg vom Menü zu einer einzelnen
   Behandlung. Ein Menü mit sechs bis acht Einträgen je Kategorie passt auf ein
   Handydisplay; eines mit 49 nie.
2. Sie kostet nichts an Auffindbarkeit. Die Seiten bleiben erzeugt, verlinkt und
   indexierbar.
3. Sie ist umkehrbar. Wer anders entscheidet, ändert Zeilen in einer JSON-Datei.
4. Sie ist keine Aussage über die Behandlungen. Auch «Botox gegen Handschweiss» und
   «Lymphdrainage» stehen nicht im Menü — sie werden nur seltener gesucht.

**Variante B — eigene Untergruppe «Intimchirurgie» mit Sammelseite.**

Statt sieben Einzeleinträge ein Eintrag «Intimchirurgie», der auf eine eigene Seite
führt. Wirkt zurückhaltender als sieben Zeilen, ist aber diskutabel: Für die
Auffindbarkeit sind eigene Seiten je Verfahren besser, und wer gezielt sucht, findet
schneller.

Variante B lässt sich mit A kombinieren, ist aber nicht nötig, wenn A umgesetzt wird.

**Variante C — nichts ändern.** Trägt die Positionierungskosten weiter und löst das
Handy-Problem aus B11 nicht.

## Was ich nicht empfehle

**Die Behandlungen aus dem Katalog nehmen.** Es sind reguläre Leistungen der
Partnerklinik, sie werden gesucht, und eigene Seiten dafür sind für die Auffindbarkeit
wertvoll. Aus dem Menü nehmen und aus dem Angebot nehmen sind zwei verschiedene Dinge.

**Sie per CSS verstecken.** Das widerspricht der Vorgabe des Auftraggebers
(Platzhalter und Unerwünschtes werden gar nicht erst ausgegeben, nicht versteckt) und
hilft weder der Vorlesehilfe noch dem Quelltext.

## Zwei Punkte, die separat entschieden werden müssen

**1. «Gesundheitsatteste und Berichte».** Der Katalogeintrag beschrieb bisher die
«Ausstellung medizinischer Berichte und Atteste, etwa für Behörden oder Versicherungen».
Das im Katalog eines Auslandsvermittlers zu bewerben, ist unabhängig von der Rechtslage
reputationsgefährdend (Befund B13). Ich habe die Beschreibung eng auf Berichte im Rahmen
der eigenen Behandlung begrenzt. **Meine Empfehlung geht weiter: die Position ganz aus
dem öffentlichen Katalog nehmen.** Entscheidung beim Auftraggeber.

**2. Die vier Aufhellungsbehandlungen.** Sie bleiben aus meiner Sicht im Katalog — sie
sind Teil des Angebots, und ein Weglassen wäre eine inhaltliche Entscheidung, die mir
nicht zusteht. Ich habe in `data/beschreibungen.json` bei allen vier den Hinweis auf das
erhöhte Risiko bleibender Pigmentverschiebungen bei dunkleren Hauttypen ergänzt — das
ist bei dieser Indikation und dieser Zielgruppe die wichtigste Information. Ob sie ins
Menü gehören, beantwortet Variante A mit nein.

## Vorschlag zum weiteren Vorgehen

1. Der Auftraggeber entscheidet zwischen A, B und C.
2. Bei A: Die Bahn `navigation` liest `im_menue` in `nav_kat_dropdowns()` und ergänzt je
   Kategorie den Eintrag «Alle … ansehen». Die Daten liegen bereit.
3. Unabhängig davon: Die Suche aus Befund B11 bauen. Sie ist die Voraussetzung dafür,
   dass ein gekürztes Menü niemanden ausschliesst. `data/behandlungen.json` enthält dafür
   jetzt 198 Suchsynonyme zu 53 Behandlungen — darunter «HIFU» für «Facelifting ohne OP»,
   das man heute ohne Kenntnis des Katalognamens nicht findet.

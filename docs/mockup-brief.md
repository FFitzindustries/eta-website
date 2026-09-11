# Mockup-Brief: ETA Website (für /design)

Ziel: Klickbares/visuelles Mockup der ETA-Website (European Turkey Asia), Vermittlungsagentur für Beauty-/OP-Behandlungen in Istanbul. Statische Mockups reichen (kein Prototyp mit Logik). Sprache im Mockup: Deutsch (de-CH, ß vermeiden, "ss").

## Marke

- **Logo:** `~/eta-website/assets/logo/eta-logo.svg` (Gold/Rosé-Wortmarke "ETA" mit Bogen, Stern und Subline "EUROPEAN TURKEY ASIA"). Fürs Canvas vorher als PNG unter 70 KB exportieren (z. B. `sips -Z 400`).
- **Farben:** Rosé `#D998A5` · Gold `#c58a32` · Luxury Black `#050505` · Weiss `#ffffff`. Heller, edler Look (Seide/Gold), NICHT düster. Schwarz als Kontrast-Anker (Header/Footer/Overlays), Rosé/Gold als Akzente, viel Weiss/Champagner als Fläche.
- **Fonts:** Tan Garland (Headings) + Stavok Grotesque (Text). Falls nicht verfügbar: elegante Serif/Didone für Headlines (z. B. Playfair Display) + neutrale Grotesk (z. B. Jost) von Google Fonts, mit Fallback-Stack.
- **Bildsprache:** warm, nahbar-luxuriös. Keine OP-Säle, keine Spritzen, kein steriles Klinik-Weiss.

## Assets (liegen bereit)

- Hero Startseite: `~/eta-website/assets-hero/hero-a-seide-gold.png` (16:9, Frau rechts, Negativraum links für Headline). Es gibt auch ein 10s-Video (`hero-a-video.mp4`) - im Mockup reicht das Standbild mit Play-Andeutung.
- Header "Ablauf/Partnerklinik": `~/eta-website/assets-hero/hero-b-istanbul.png` (Frau am Fenster, Bosporus-Skyline).
- Beide Bilder fürs Canvas auf unter 70 KB downsamplen (`sips -Z 1200`, JPEG).
- Behandlungs-Menü mit allen 94 Behandlungen: `~/eta-website/docs/behandlungskatalog.md` (Kategorien, Gruppen, deutsche Namen). Vollständige Daten: `~/eta-website/data/behandlungen.json`.

## Zielgruppe (bestimmt Ton und Bild)

"Gabi von nebenan": Frau (und Mann) aus DACH/Ostschweiz, 25-55, normales Einkommen, will Premium-Behandlung zu türkischen Preisen. Braucht: Vertrauen (Angst vor Billig-Türkei-Image), Luxusgefühl, Nahbarkeit (deutschsprachig, WhatsApp). Ton: warm, souverän, ehrlich - kein Marktschreier, keine Rabatt-Optik.

## Artboards (Desktop 1440×900, dazu 1 Mobile-Check 390×844)

1. **Startseite** (Main)
   - Header: Logo links, Nav (Behandlungen, Partnerklinik, Ablauf, Finanzierung, Vorher/Nachher, Kontakt), Sprachumschalter (DE/EN/IT/FR), WhatsApp-Button prominent (Gold)
   - Hero: hero-a-seide-gold, dunkles Gradient-Overlay links, Headline Richtung "Ihre Schönheitsbehandlung in Istanbul. Betreut von A bis Z." + Subline (deutschsprachige Betreuung, fixe Partnerklinik, Rundum-Paket) + 2 CTAs: "Unverbindlich anfragen" (primär, WhatsApp) / "Behandlungen entdecken" (sekundär)
   - 4 Kategorie-Kacheln (Viererblock, KEINE Horizontal-Scroller): Plastische Chirurgie · Haartransplantation · Zähne · Haut & Beauty
   - USP-Leiste: deutschsprachige Betreuung · fixe Partnerklinik in Istanbul · Transfer + Hotel inklusive · Nachsorge in der Schweiz (Riverside Beauty)
   - Ablauf in 4 Schritten: Anfrage -> Beratung & Angebot -> Anzahlung & Reise -> Behandlung & Nachsorge
   - Vorher/Nachher-Teaser (3 Platzhalter-Bilder mit ETA-Wasserzeichen-Andeutung)
   - Finanzierungs-Teaser (3 Karten: 3 Raten 0 % · Ratenkauf mit Laufzeit · Ansparmodell)
   - FAQ-Teaser (3-4 Fragen), Footer (Impressum, AGB, Datenschutz, Social, Partner: Riverside Beauty)

2. **Behandlungs-Übersicht** (Kategorie-Seite, Beispiel: Plastische Chirurgie)
   - Header-Band in Rosé/Schwarz, Breadcrumb
   - Gruppen als Abschnitte (Gesicht, Brust, Körper, Intimchirurgie Frau/Mann) mit Behandlungs-Kacheln im Viererblock, Namen aus `behandlungskatalog.md`
   - Oben klein: "Alle Behandlungen" (Meeting-Vorgabe: die wichtigsten gross, Rest dahinter)

3. **Behandlungs-Detailseite** (Beispiel: Brustvergrösserung)
   - Hero-Band, Kurzbeschreibung, Fakten-Box (Aufenthalt: X Tage, Dauer, Narkose, [PREIS AUF ANFRAGE])
   - Ablauf, FAQ-Akkordeon, Vorher/Nachher-Platzhalter
   - Sticky CTA: "Unverbindlich anfragen" (WhatsApp + Formular-Link)

4. **Kontakt/Anfrage**
   - WhatsApp gross, daneben Formular: Name, Strasse, PLZ/Ort, Geburtsdatum, Telefon MIT Ländervorwahl-Dropdown (CH/AT/DE), E-Mail, gewünschte Behandlung (Select aus Kategorien), Nachricht
   - Hinweis Anzahlung/72h-Storno dezent

5. Optional, wenn Zeit: **Ablauf/Partnerklinik** mit hero-b-istanbul (Elit Klinik Vadi Istanbul, Zahlen, 360°-Tour-Verweis)

## Regeln

- Kein Text in Bilder einbacken (Mehrsprachigkeit), Headlines immer als Text-Layer
- Viererblock-Grids, keine endlosen Horizontal-Scroller (explizite Meeting-Vorgabe)
- WhatsApp-Button auf jeder Seite sichtbar (sticky)
- Echte Behandlungsnamen aus dem Katalog verwenden, keine Lorem-Ipsum-Menüs
- Preise/Daten als markierte Platzhalter ([PREIS], [DATUM]), nichts erfinden
- Keine medizinischen Erfolgsversprechen im Copy ("Traumkörper garantiert" o. ä.)

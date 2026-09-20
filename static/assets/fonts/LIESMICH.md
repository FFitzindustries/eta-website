# Schriften, selbst ausgeliefert

Playfair Display und Jost kamen bisher bei jedem Seitenaufruf von
`fonts.googleapis.com` / `fonts.gstatic.com`. Das kostete zwei Fremdhosts, ein
render-blockierendes Fremd-Stylesheet und gab jede besuchte URL als `Referer`
an Google weiter (Befund technik B6/B7). Seit dem Umbau liegen die Dateien hier.

| Datei | Zeichenvorrat | Grösse |
|---|---|---|
| `playfair-latin.woff2` | Latin (deutsch, englisch) | 38 KB |
| `playfair-latin-ext.woff2` | Latin erweitert (türkisch: ş ğ İ) | 21 KB |
| `jost-latin.woff2` | Latin | 26 KB |
| `jost-latin-ext.woff2` | Latin erweitert | 17 KB |

Alle vier sind **variable Schriften** und decken damit jedes Gewicht ab, das im
CSS vorkommt — eine Datei je Zeichenvorrat statt einer je Schnitt.
Vorgeladen werden nur die beiden `latin`-Dateien; `latin-ext` holt der Browser
über `unicode-range` nur, wenn türkische Sonderzeichen auf der Seite stehen.

**Arabisch:** Keine der beiden Schriften enthält arabische Zeichen. Für `ar`
greift die Systemschriftkette aus `style.css`. Das ist gewollt, aber es heisst
auch: die arabische Fassung sieht anders aus als die deutsche.

Herkunft: Google Fonts, Abruf 2026-09-20, unverändert übernommen.
Lizenz: SIL Open Font License 1.1 — Volltexte in `OFL-Playfair-Display.txt`
und `OFL-Jost.txt`. Einbetten und Selbst-Ausliefern sind ausdrücklich erlaubt.

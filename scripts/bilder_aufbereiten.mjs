/**
 * Erzeugt aus den Originalbildern unter static/assets/img/ die Varianten,
 * die scripts/build_site.py in <picture> einbindet.
 *
 * Aufruf:  node scripts/bilder_aufbereiten.mjs [--neu]
 *   ohne --neu werden vorhandene Varianten uebersprungen (schneller Wiederlauf).
 *
 * Ergebnis:
 *   static/assets/img/<name>-<breite>.webp   (Hauptformat)
 *   static/assets/img/<name>-<breite>.jpg    (Rueckfall fuer alte Browser)
 *   static/assets/img/abgeleitet.json        (Bauplan fuer den Generator:
 *                                             Breiten, Hoehen, Seitenverhaeltnis)
 *
 * sharp liegt bereits im Werkzeugkasten des Nachbarprojekts; es wird bewusst
 * kein neues Paket installiert. Das Skript laeuft einmalig von Hand, nicht bei
 * jedem Build — die Varianten liegen danach im Repository.
 */
import { readdirSync, existsSync, writeFileSync, statSync } from "node:fs";
import { join, basename, extname } from "node:path";
import { fileURLToPath } from "node:url";
import sharp from "/home/fitzindustries/ri-mobil/werkzeug/node_modules/sharp/lib/index.js";

const WURZEL = join(fileURLToPath(new URL(".", import.meta.url)), "..");
const IMG = join(WURZEL, "static", "assets", "img");
const NEU = process.argv.includes("--neu");

// Qualitaet: WebP 72 laut Messung von befund/technik B2. Fuer Hautaufnahmen
// waere 78 sicherer — das ist eine Sichtentscheidung, hier bewusst notiert.
const WEBP_Q = 74;
const JPG_Q = 78;

/** Was aus welcher Quelle entstehen soll. */
const PLAN = [
  // Startseiten-Hero: volle Breite, deshalb bis 1920.
  { quelle: "hero-a.jpg", webp: [480, 960, 1170, 1440, 1920], jpg: [960, 1440] },
  { quelle: "hero-b.jpg", webp: [480, 960, 1170, 1440, 1920], jpg: [960, 1440] },
  // Vorschaubild fuer geteilte Links. Wird von der Seite selbst nie geladen.
  { quelle: "og-image.jpg", webp: [], jpg: [1200] },
  // Das Zeichen in der Kopfleiste. Es liegt als 400 x 334 grosses PNG vor und
  // wird 48 x 40 dargestellt — 16 KB fuer ein Bild, von dem 94 Prozent der
  // Flaeche weggerechnet werden, auf jeder der 120 Seiten. Drei Stufen decken
  // Pixelverhaeltnis 1 bis 3 ab. PNG bleibt der Ruecklauf, weil ein Zeichen
  // mit harten Kanten in WebP bei dieser Groesse nichts spart, wenn ein alter
  // Browser es nicht versteht.
  { quelle: "eta-logo.png", webp: [48, 96, 144], jpg: [], png: [48, 96, 144] },
];

// Die 101 Behandlungsbilder werden hoechstens 300 CSS-Pixel breit gezeigt,
// bei DPR 3 also rund 900 px. 400 und 800 decken das ab, 1200 waere Ballast.
for (const datei of readdirSync(join(IMG, "behandlungen")).sort()) {
  if (!/\.(jpg|jpeg|png)$/i.test(datei)) continue;
  // Nur Originale, keine bereits erzeugten Varianten (…-800.jpg).
  if (/-\d+\.(jpg|jpeg|png)$/i.test(datei)) continue;
  PLAN.push({ quelle: join("behandlungen", datei), webp: [400, 600, 800], jpg: [800] });
}

const manifest = {};
let erzeugt = 0;
let uebersprungen = 0;
let quellBytes = 0;
let zielBytes = 0;

for (const eintrag of PLAN) {
  const quellPfad = join(IMG, eintrag.quelle);
  if (!existsSync(quellPfad)) {
    console.error("fehlt, uebersprungen: " + eintrag.quelle);
    continue;
  }
  const bild = sharp(quellPfad);
  const meta = await bild.metadata();
  quellBytes += statSync(quellPfad).size;

  const stamm = eintrag.quelle.slice(0, eintrag.quelle.length - extname(eintrag.quelle).length);
  const varianten = { breite: meta.width, hoehe: meta.height, webp: [], jpg: [], png: [] };

  for (const [format, breiten] of [["webp", eintrag.webp], ["jpg", eintrag.jpg], ["png", eintrag.png ?? []]]) {
    for (const b of breiten) {
      if (b > meta.width) continue; // nie hochrechnen
      const ziel = join(IMG, `${stamm}-${b}.${format}`);
      const hoehe = Math.round((meta.height / meta.width) * b);
      varianten[format].push({ breite: b, hoehe });
      if (!NEU && existsSync(ziel)) {
        uebersprungen += 1;
        zielBytes += statSync(ziel).size;
        continue;
      }
      let p = sharp(quellPfad).resize({ width: b, withoutEnlargement: true });
      if (format === "webp") p = p.webp({ quality: WEBP_Q });
      else if (format === "png") p = p.png({ compressionLevel: 9, palette: true });
      else p = p.jpeg({ quality: JPG_Q, mozjpeg: true, progressive: true });
      await p.toFile(ziel);
      erzeugt += 1;
      zielBytes += statSync(ziel).size;
    }
  }
  for (const f of ["webp", "jpg", "png"]) if (!varianten[f].length) delete varianten[f];
  manifest[eintrag.quelle.split("\\").join("/")] = varianten;
}

writeFileSync(join(IMG, "abgeleitet.json"), JSON.stringify(manifest, null, 1) + "\n");
console.error(
  `fertig: ${erzeugt} erzeugt, ${uebersprungen} vorhanden, ` +
    `${Math.round(quellBytes / 1024 / 1024)} MB Quellen -> ${Math.round(zielBytes / 1024 / 1024)} MB Varianten, ` +
    `${Object.keys(manifest).length} Bilder im Bauplan (${basename(IMG)}/abgeleitet.json)`,
);

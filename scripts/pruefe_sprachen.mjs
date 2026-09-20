// Prüft im echten Browser, ob die Sprachumschaltung die ganze Seite erfasst:
// schaltet auf jeder Seite alle Sprachen durch, zählt was deutsch geblieben ist,
// kontrolliert Titel, Meta-Beschreibung, lang und dir und ob das Zurückschalten
// auf Deutsch die Originaltexte wiederherstellt.
//
// Braucht Playwright und einen laufenden Server über dem Bauergebnis:
//   cd docs && python3 -m http.server 8899 --bind 127.0.0.1 &
//   cd /tmp && mkdir -p p && cd p
//   ln -s <irgendein Projekt mit playwright>/node_modules node_modules
//   cp <hier>/scripts/pruefe_sprachen.mjs . && node pruefe_sprachen.mjs
//
// Meldet nur noch Eigennamen und Wörter, die in der Zielsprache gleich lauten
// ("Name" im Englischen, "Telefon" im Türkischen) — alles andere ist ein Mangel.
import { chromium } from 'playwright';

const BASIS = process.argv[2] || 'http://127.0.0.1:8899';
const SEITEN = [
  ['Startseite', '/index.html'],
  ['Behandlungen', '/behandlungen/index.html'],
  ['Kategorie Zähne', '/behandlungen/zaehne/index.html'],
  ['Detail Bleaching', '/behandlungen/zaehne/bleaching.html'],
  ['Partnerklinik', '/partnerklinik.html'],
  ['Finanzierung', '/finanzierung.html'],
  ['Wenn etwas schiefgeht', '/wenn-etwas-nicht-wie-geplant-laeuft.html'],
  ['Ihre Reise', '/ihre-reise.html'],
  ['Was es kostet', '/was-es-kostet.html'],
  ['Gut zu wissen', '/gut-zu-wissen.html'],
  ['Kontakt', '/kontakt.html'],
  ['AGB', '/agb.html'],
  ['Datenschutz', '/datenschutz.html'],
  ['Impressum', '/impressum.html'],
];
const SPRACHEN = ['en', 'tr', 'ar'];

// Eine Textstelle darf gleich bleiben, wenn nach Abzug aller Eigennamen,
// Zahlen und Satzzeichen nichts Übersetzbares übrig bleibt.
const EIGENNAMEN = [
  'EUROPEAN TURKEY ASIA', 'European Turkey Asia', 'Riverside Beauty', 'St. Margrethen',
  'Hollywood Smile', 'HydraFacial', 'info@eta-agency.ch', 'eta-agency.ch',
  'WhatsApp', 'Instagram', 'Facebook', 'Messenger', 'Istanbul', 'ETA',
  'Botox', 'FUE', 'DHI', 'PRP', 'HIFU', 'BBL', 'Q-Switch', 'Schweiz', 'Suisse',
];
function darfGleichBleiben(t) {
  let rest = t;
  for (const e of EIGENNAMEN) rest = rest.split(e).join(' ');
  rest = rest.replace(/[\d\s.,:;!?+()\[\]·/–—_@&%'"„“-]/g, '');
  return rest.length <= 2;   // nur noch Streusel übrig
}

function textInventar(page) {
  return page.evaluate(() => {
    const raus = [];
    const lauf = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
    let n;
    while ((n = lauf.nextNode())) {
      const el = n.parentElement;
      if (!el || ['SCRIPT', 'STYLE', 'NOSCRIPT'].includes(el.tagName)) continue;
      if (!el.offsetParent && el.tagName !== 'BODY') continue;  // unsichtbar
      // Der Honigtopf gegen Spam-Roboter liegt per CSS ausserhalb des Bildes
      // und bleibt bewusst deutsch — er soll unauffällig aussehen.
      if (el.closest('.hp, [aria-hidden="true"]')) continue;
      const t = n.textContent.trim().replace(/\s+/g, ' ');
      if (t) raus.push(t);
    }
    const titel = document.title;
    const beschr = document.querySelector('meta[name="description"]')?.content || '';
    return { texte: raus, titel, beschr, lang: document.documentElement.lang, dir: document.documentElement.dir };
  });
}

const browser = await chromium.launch();
const kontext = await browser.newContext({ viewport: { width: 1280, height: 900 }, locale: 'de-CH' });
let fehler = 0, warnungen = 0;

for (const [name, pfad] of SEITEN) {
  const page = await kontext.newPage();
  const konsolenfehler = [];
  page.on('pageerror', e => konsolenfehler.push(String(e)));
  page.on('console', m => { if (m.type() === 'error') konsolenfehler.push(m.text()); });

  await page.goto(BASIS + pfad, { waitUntil: 'networkidle' });
  await page.click('.lang-switch [data-lang="de"]');
  await page.waitForTimeout(700);
  const de = await textInventar(page);
  if (!de.lang.startsWith('de')) { console.log(`  [FEHL] Startsprache ist ${de.lang}, nicht Deutsch`); fehler++; }

  console.log(`\n=== ${name} (${pfad}) — ${de.texte.length} Textstellen auf Deutsch ===`);
  if (konsolenfehler.length) { console.log('  JS-FEHLER:', konsolenfehler.slice(0, 3).join(' | ')); fehler++; }

  for (const sp of SPRACHEN) {
    await page.click(`.lang-switch [data-lang="${sp}"]`);
    await page.waitForTimeout(700);
    const ds = await textInventar(page);

    const gleich = [];
    const n = Math.min(de.texte.length, ds.texte.length);
    for (let i = 0; i < n; i++) {
      if (de.texte[i] === ds.texte[i] && !darfGleichBleiben(de.texte[i])) gleich.push(de.texte[i]);
    }
    const anteil = n ? Math.round((1 - gleich.length / n) * 100) : 0;
    const titelOk = ds.titel !== de.titel;
    const beschrOk = ds.beschr !== de.beschr;
    const langOk = ds.lang.startsWith(sp);
    const dirOk = sp === 'ar' ? ds.dir === 'rtl' : ds.dir !== 'rtl';

    const marke = gleich.length === 0 && titelOk && beschrOk && langOk && dirOk ? 'OK  ' : 'FEHL';
    if (marke === 'FEHL') fehler++;
    console.log(`  [${marke}] ${sp}: ${anteil}% übersetzt, ${gleich.length} deutsch geblieben` +
                `${titelOk ? '' : ', TITEL deutsch'}${beschrOk ? '' : ', META deutsch'}` +
                `${langOk ? '' : `, lang=${ds.lang}`}${dirOk ? '' : `, dir=${ds.dir}`}`);
    if (gleich.length) {
      const zeigen = [...new Set(gleich)].slice(0, 8);
      zeigen.forEach(t => console.log(`         · ${t.slice(0, 90)}`));
      if (new Set(gleich).size > 8) console.log(`         · … und ${new Set(gleich).size - 8} weitere`);
    }
  }

  // Zurück auf Deutsch — muss die Originaltexte wiederherstellen
  await page.click('.lang-switch [data-lang="de"]');
  await page.waitForTimeout(700);
  const zurueck = await textInventar(page);
  const abweichung = de.texte.filter((t, i) => zurueck.texte[i] !== t).length;
  if (abweichung > 0) { console.log(`  [FEHL] Zurück auf DE: ${abweichung} Textstellen stimmen nicht mehr`); fehler++; }

  await page.close();
}

// Screenshots je Sprache von der Startseite. Der Zielordner laesst sich ueber
// ETA_BILDER setzen; fehlt er, werden die Aufnahmen uebersprungen.
const BILDER = process.env.ETA_BILDER || '/home/fitzindustries/screenshots';
const page = await kontext.newPage();
for (const sp of ['de', 'en', 'tr', 'ar']) {
  await page.goto(BASIS + '/index.html', { waitUntil: 'networkidle' });
  await page.click(`.lang-switch [data-lang="${sp}"]`);
  await page.waitForTimeout(900);
  await page.screenshot({ path: `${BILDER}/eta-${sp}.png`, fullPage: false });
}
await page.close();

await browser.close();
console.log(`\n=== Ergebnis: ${fehler} Beanstandungen ===`);
process.exit(fehler > 0 ? 1 : 0);

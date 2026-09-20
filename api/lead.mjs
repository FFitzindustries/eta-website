// ETA – Lead-Annahme (Vercel Function, Node-Laufzeit, ESM).
//
// Diese Datei ist der einzige Weg, auf dem ein Formular der Website in die
// Datenbank schreibt. Der Browser kennt keinen Supabase-Schlüssel mehr; der
// Service-Role-Key steht ausschliesslich hier und kommt aus der Umgebung.
//
// Bewusst ohne Abhängigkeiten: `fetch` ist in der Node-Laufzeit von Vercel
// global vorhanden, eine package.json ist deshalb nicht nötig.

// --------------------------------------------------------------- Einstellungen

// Feldlängen. Alles Längere wird abgeschnitten, nicht abgelehnt – ein zu langer
// Ort soll keine echte Anfrage kosten.
const LAENGEN = {
  vorname: 80,
  nachname: 80,
  email: 120,
  telefon: 40,
  telefon_vorwahl: 8,
  strasse: 120,
  plz: 12,
  ort: 80,
  nachricht: 4000,
  gewuenschte_behandlung: 200,
  quelle_url: 500,
  notizen: 1000,
};

const SPRACHEN = ["de", "en", "tr", "ar"];

// Ratenbegrenzung. ACHTUNG: Das ist ein Zähler im Arbeitsspeicher und gilt
// deshalb nur pro laufender Function-Instanz. Vercel startet je nach Last
// mehrere Instanzen und friert sie wieder ein, der Zähler ist also weder
// vollständig noch dauerhaft. Er hält Gelegenheits-Spam ab, mehr nicht. Wer
// eine belastbare Grenze will, braucht einen gemeinsamen Speicher (z. B. Redis)
// oder Cloudflare Turnstile (siehe TURNSTILE_SECRET weiter unten).
const RATE_FENSTER_MS = 10 * 60 * 1000; // 10 Minuten
const RATE_MAX = 5;                     // so viele Anfragen pro IP und Fenster
const ratenSpeicher = new Map();        // IP -> Liste von Zeitstempeln

// Grösste akzeptierte Nutzlast, damit niemand Megabytes durch die Prüfung jagt.
const MAX_BODY_BYTES = 64 * 1024;

// --------------------------------------------------------------- Hilfsfunktionen

function text(wert, maxLaenge) {
  if (wert === null || wert === undefined) return null;
  if (typeof wert !== "string") wert = String(wert);
  const sauber = wert.replace(/\0/g, "").trim();
  if (!sauber) return null;
  return sauber.slice(0, maxLaenge);
}

function istWahr(wert) {
  if (wert === true) return true;
  if (typeof wert === "number") return wert === 1;
  if (typeof wert !== "string") return false;
  const k = wert.trim().toLowerCase();
  return k === "on" || k === "true" || k === "1" || k === "ja" || k === "yes";
}

// Grobe Plausibilitätsprüfung, keine RFC-Validierung. Eine E-Mail-Adresse
// endgültig zu prüfen geht nur, indem man ihr schreibt.
function emailPlausibel(email) {
  if (!email || email.length > LAENGEN.email) return false;
  return /^[^\s@,;:<>()[\]\\]+@[^\s@.,;:<>()[\]\\]+(\.[^\s@.,;:<>()[\]\\]+)+$/.test(email);
}

// Telefon: mindestens sechs Ziffern, sonst ist es keine Nummer.
function telefonPlausibel(telefon) {
  if (!telefon) return false;
  const ziffern = telefon.replace(/\D/g, "");
  return ziffern.length >= 6 && ziffern.length <= 20;
}

// TT.MM.JJJJ -> JJJJ-MM-TT. Gibt null zurück, wenn das Datum unsinnig ist;
// der Rohtext wandert dann in `notizen`, damit nichts verloren geht.
function geburtsdatumNachIso(roh) {
  const m = /^(\d{1,2})\.(\d{1,2})\.(\d{4})$/.exec((roh || "").trim());
  if (!m) return null;
  const tag = Number(m[1]);
  const monat = Number(m[2]);
  const jahr = Number(m[3]);
  if (monat < 1 || monat > 12) return null;
  if (jahr < 1900 || jahr > new Date().getUTCFullYear()) return null;
  // Auf echte Existenz prüfen (der 31. Februar fällt hier durch).
  const d = new Date(Date.UTC(jahr, monat - 1, tag));
  if (d.getUTCFullYear() !== jahr || d.getUTCMonth() !== monat - 1 || d.getUTCDate() !== tag) return null;
  const zz = (n) => String(n).padStart(2, "0");
  return `${jahr}-${zz(monat)}-${zz(tag)}`;
}

function klientIp(req) {
  const h = req.headers || {};
  const weiter = h["x-forwarded-for"];
  if (typeof weiter === "string" && weiter) return weiter.split(",")[0].trim();
  if (Array.isArray(weiter) && weiter.length) return String(weiter[0]).split(",")[0].trim();
  if (h["x-real-ip"]) return String(h["x-real-ip"]);
  if (h["x-vercel-forwarded-for"]) return String(h["x-vercel-forwarded-for"]).split(",")[0].trim();
  return (req.socket && req.socket.remoteAddress) || "unbekannt";
}

function rateUeberschritten(ip) {
  const jetzt = Date.now();
  // Beim Prüfen gleich alte Einträge loswerden, damit die Map nicht wächst.
  for (const [schluessel, zeiten] of ratenSpeicher) {
    const frisch = zeiten.filter((t) => jetzt - t < RATE_FENSTER_MS);
    if (frisch.length) ratenSpeicher.set(schluessel, frisch);
    else ratenSpeicher.delete(schluessel);
  }
  const zeiten = ratenSpeicher.get(ip) || [];
  if (zeiten.length >= RATE_MAX) return true;
  zeiten.push(jetzt);
  ratenSpeicher.set(ip, zeiten);
  return false;
}

// Vercel füllt req.body bei JSON meist selbst. Falls nicht (oder bei fremdem
// Content-Type), lesen wir den Datenstrom von Hand.
async function leseBody(req) {
  if (req.body && typeof req.body === "object" && !Buffer.isBuffer(req.body)) return req.body;

  let roh = req.body;
  if (roh === undefined || roh === null || Buffer.isBuffer(roh)) {
    const stuecke = [];
    let bytes = 0;
    for await (const stueck of req) {
      bytes += stueck.length;
      if (bytes > MAX_BODY_BYTES) throw new Error("Nutzlast zu gross");
      stuecke.push(stueck);
    }
    roh = Buffer.concat(stuecke).toString("utf8");
  }
  if (typeof roh !== "string") return {};
  if (!roh.trim()) return {};
  if (Buffer.byteLength(roh, "utf8") > MAX_BODY_BYTES) throw new Error("Nutzlast zu gross");

  try {
    const daten = JSON.parse(roh);
    return daten && typeof daten === "object" ? daten : {};
  } catch (e) {
    // Notfalls auch ein klassisches Formular-POST verstehen.
    const params = new URLSearchParams(roh);
    const daten = {};
    for (const [k, v] of params) daten[k] = v;
    return daten;
  }
}

function antworte(res, status, nutzlast) {
  res.statusCode = status;
  res.setHeader("Content-Type", "application/json; charset=utf-8");
  res.setHeader("Cache-Control", "no-store");
  res.end(JSON.stringify(nutzlast));
}

// ----------------------------------------------------------------- Turnstile

// Wenn TURNSTILE_SECRET nicht gesetzt ist, wird übersprungen. So läuft die
// Function auch ohne Cloudflare-Konto; sobald der Schlüssel gesetzt wird, greift
// die Prüfung ohne weitere Änderung an dieser Datei.
async function turnstileGeprueft(token, ip) {
  const geheimnis = process.env.TURNSTILE_SECRET;
  if (!geheimnis) return { ok: true, uebersprungen: true };
  if (!token) return { ok: false, grund: "Spam-Prüfung fehlgeschlagen. Bitte laden Sie die Seite neu." };

  const koerper = new URLSearchParams({ secret: geheimnis, response: token });
  if (ip && ip !== "unbekannt") koerper.set("remoteip", ip);

  try {
    const antwort = await fetch("https://challenges.cloudflare.com/turnstile/v0/siteverify", {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: koerper.toString(),
    });
    const ergebnis = await antwort.json();
    if (ergebnis && ergebnis.success) return { ok: true };
    return { ok: false, grund: "Spam-Prüfung fehlgeschlagen. Bitte laden Sie die Seite neu." };
  } catch (fehler) {
    // Cloudflare nicht erreichbar: Wir lehnen ab, statt blind durchzulassen.
    // Ohne gesetztes Geheimnis kommen wir hier gar nicht erst hin.
    console.error("Turnstile nicht erreichbar:", fehler);
    return { ok: false, grund: "Spam-Prüfung derzeit nicht möglich." };
  }
}

// ------------------------------------------------------------------ Telegram

// Benachrichtigung ist eine Annehmlichkeit, kein Teil der Speicherung. Jeder
// Fehler hier wird geschluckt – ein Lead darf daran nie scheitern.
async function telegramMelden(kontakt) {
  const token = process.env.TELEGRAM_BOT_TOKEN;
  const chat = process.env.TELEGRAM_CHAT_ID;
  if (!token || !chat) return;

  try {
    const zeilen = [
      "Neue Anfrage über die ETA-Website",
      "",
      `Name: ${[kontakt.vorname, kontakt.nachname].filter(Boolean).join(" ") || "—"}`,
      `E-Mail: ${kontakt.email || "—"}`,
      `Telefon: ${[kontakt.telefon_vorwahl, kontakt.telefon].filter(Boolean).join(" ") || "—"}`,
      kontakt.gewuenschte_behandlung ? `Behandlung: ${kontakt.gewuenschte_behandlung}` : null,
      kontakt.ort ? `Ort: ${[kontakt.plz, kontakt.ort].filter(Boolean).join(" ")}` : null,
      `Sprache: ${kontakt.sprache || "de"}`,
      kontakt.quelle_url ? `Seite: ${kontakt.quelle_url}` : null,
      kontakt.nachricht ? `\nNachricht:\n${kontakt.nachricht.slice(0, 800)}` : null,
    ].filter(Boolean);

    // Nach vier Sekunden abbrechen, damit ein hängendes Telegram die Antwort
    // an den Besucher nicht verzögert.
    const steuerung = new AbortController();
    const abbruch = setTimeout(() => steuerung.abort(), 4000);
    try {
      await fetch(`https://api.telegram.org/bot${token}/sendMessage`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          chat_id: chat,
          text: zeilen.join("\n"),
          disable_web_page_preview: true,
        }),
        signal: steuerung.signal,
      });
    } finally {
      clearTimeout(abbruch);
    }
  } catch (fehler) {
    console.error("Telegram-Benachrichtigung fehlgeschlagen (Lead ist trotzdem gespeichert):", fehler);
  }
}

// ------------------------------------------------------------------- Supabase

function supabaseUrl() {
  const url = process.env.ETA_SUPABASE_URL || process.env.SUPABASE_URL || "";
  return url.replace(/\/+$/, "");
}

// Schreibt nach public.contacts. Fehlen die erst durch die Migration ergänzten
// Spalten noch (quelle_url, einwilligungstext_version), wird der Versuch ohne
// diese Felder wiederholt. So funktioniert die Reihenfolge "erst Function
// deployen, dann Migration einspielen" wirklich.
async function contactAnlegen(kontakt) {
  const url = supabaseUrl();
  const schluessel = process.env.SUPABASE_SERVICE_ROLE_KEY;
  if (!url || !schluessel) {
    console.error("Supabase-Zugang fehlt: ETA_SUPABASE_URL/SUPABASE_URL oder SUPABASE_SERVICE_ROLE_KEY nicht gesetzt.");
    return { ok: false, status: 500, grund: "Der Server ist noch nicht vollständig eingerichtet." };
  }

  const NEUE_SPALTEN = ["quelle_url", "einwilligungstext_version"];

  async function schreibe(nutzlast) {
    const antwort = await fetch(`${url}/rest/v1/contacts`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        apikey: schluessel,
        Authorization: `Bearer ${schluessel}`,
        Prefer: "return=representation",
      },
      body: JSON.stringify(nutzlast),
    });
    const roh = await antwort.text();
    let daten = null;
    try {
      daten = roh ? JSON.parse(roh) : null;
    } catch (e) {
      daten = null;
    }
    return { antwort, daten, roh };
  }

  let ergebnis;
  try {
    ergebnis = await schreibe(kontakt);
  } catch (fehler) {
    console.error("Supabase nicht erreichbar:", fehler);
    return { ok: false, status: 502, grund: "Die Anfrage konnte gerade nicht gespeichert werden." };
  }

  // PGRST204 = Spalte im Schema-Cache nicht gefunden, 42703 = undefined_column.
  const fehltSpalte =
    !ergebnis.antwort.ok &&
    ergebnis.daten &&
    (ergebnis.daten.code === "PGRST204" || ergebnis.daten.code === "42703") &&
    NEUE_SPALTEN.some((s) => String(ergebnis.daten.message || "").includes(s));

  if (fehltSpalte) {
    console.warn("Migration noch nicht eingespielt – schreibe ohne:", NEUE_SPALTEN.join(", "));
    const ohne = { ...kontakt };
    for (const s of NEUE_SPALTEN) delete ohne[s];
    try {
      ergebnis = await schreibe(ohne);
    } catch (fehler) {
      console.error("Supabase nicht erreichbar:", fehler);
      return { ok: false, status: 502, grund: "Die Anfrage konnte gerade nicht gespeichert werden." };
    }
  }

  if (!ergebnis.antwort.ok) {
    console.error("Supabase-Insert fehlgeschlagen:", ergebnis.antwort.status, ergebnis.roh);
    return { ok: false, status: 502, grund: "Die Anfrage konnte gerade nicht gespeichert werden." };
  }

  const satz = Array.isArray(ergebnis.daten) ? ergebnis.daten[0] : ergebnis.daten;
  return { ok: true, id: satz && satz.id ? satz.id : null };
}

// --------------------------------------------------------------------- Handler

export default async function handler(req, res) {
  if (req.method !== "POST") {
    res.setHeader("Allow", "POST");
    return antworte(res, 405, { ok: false, fehler: "Nur POST." });
  }

  let daten;
  try {
    daten = await leseBody(req);
  } catch (fehler) {
    return antworte(res, 413, { ok: false, fehler: "Die übermittelten Daten sind zu gross." });
  }

  // 1) Honigtopf. Das Feld ist im Formular versteckt; nur automatische
  //    Ausfüller tragen dort etwas ein. Wir antworten freundlich mit 200,
  //    damit der Bot keinen Hinweis bekommt – gespeichert wird nichts.
  if (text(daten.website, 200)) {
    return antworte(res, 200, { ok: true });
  }

  // 2) Ratenbegrenzung.
  const ip = klientIp(req);
  if (rateUeberschritten(ip)) {
    return antworte(res, 429, {
      ok: false,
      fehler: "Zu viele Anfragen in kurzer Zeit. Bitte versuchen Sie es in einigen Minuten erneut.",
    });
  }

  // 3) Einwilligung. Ohne sie wird nichts gespeichert.
  if (!istWahr(daten.einwilligung)) {
    return antworte(res, 400, {
      ok: false,
      fehler: "Bitte bestätigen Sie die Einwilligung zur Verarbeitung Ihrer Angaben.",
      feld: "einwilligung",
    });
  }

  // 4) Pflichtfelder.
  const email = text(daten.email, LAENGEN.email);
  const telefon = text(daten.telefon, LAENGEN.telefon);

  if (!email) {
    return antworte(res, 400, { ok: false, fehler: "Bitte geben Sie eine E-Mail-Adresse an.", feld: "email" });
  }
  if (!emailPlausibel(email)) {
    return antworte(res, 400, { ok: false, fehler: "Diese E-Mail-Adresse sieht nicht gültig aus.", feld: "email" });
  }
  if (!telefon) {
    return antworte(res, 400, { ok: false, fehler: "Bitte geben Sie eine Telefonnummer an.", feld: "telefon" });
  }
  if (!telefonPlausibel(telefon)) {
    return antworte(res, 400, { ok: false, fehler: "Diese Telefonnummer sieht nicht gültig aus.", feld: "telefon" });
  }

  // 5) Turnstile (nur wenn eingerichtet).
  const turnstile = await turnstileGeprueft(
    text(daten.turnstile_token, 3000) || text(daten["cf-turnstile-response"], 3000),
    ip,
  );
  if (!turnstile.ok) {
    return antworte(res, 403, { ok: false, fehler: turnstile.grund });
  }

  // 6) Namen. Das kleine Formular auf den Behandlungsseiten hat nur ein Feld
  //    "name", das grosse Formular hat vorname/nachname getrennt.
  let vorname = text(daten.vorname, LAENGEN.vorname);
  let nachname = text(daten.nachname, LAENGEN.nachname);
  if (!vorname && !nachname) {
    const ganz = text(daten.name, LAENGEN.vorname + LAENGEN.nachname + 1);
    if (ganz) {
      const teile = ganz.split(/\s+/);
      vorname = (teile.shift() || "").slice(0, LAENGEN.vorname) || null;
      nachname = teile.join(" ").slice(0, LAENGEN.nachname) || null;
    }
  }

  // 7) Geburtsdatum. Unbrauchbares wandert als Rohtext in die Notizen.
  const geburtsdatumRoh = text(daten.geburtsdatum, 40);
  const geburtsdatum = geburtsdatumNachIso(geburtsdatumRoh);
  const notizen =
    !geburtsdatum && geburtsdatumRoh
      ? text(`Geburtsdatum (Rohtext): ${geburtsdatumRoh}`, LAENGEN.notizen)
      : null;

  // 8) Sonstiges normalisieren.
  let sprache = text(daten.sprache, 5);
  sprache = sprache ? sprache.slice(0, 2).toLowerCase() : "de";
  if (!SPRACHEN.includes(sprache)) sprache = "de";

  const kontakt = {
    vorname,
    nachname,
    email,
    telefon_vorwahl: text(daten.vorwahl, LAENGEN.telefon_vorwahl),
    telefon,
    strasse: text(daten.strasse, LAENGEN.strasse),
    plz: text(daten.plz, LAENGEN.plz),
    ort: text(daten.ort, LAENGEN.ort),
    geburtsdatum,
    sprache,
    quelle: "formular",
    gewuenschte_behandlung: text(daten.behandlung, LAENGEN.gewuenschte_behandlung),
    nachricht: text(daten.nachricht, LAENGEN.nachricht),
    notizen,
    dsgvo_einwilligung: true,
    dsgvo_einwilligung_at: new Date().toISOString(),
    // Diese beiden Spalten gibt es erst nach der Migration – siehe contactAnlegen().
    einwilligungstext_version: text(daten.einwilligung_version, 20) || "v1",
    quelle_url: text(daten.quelle_url, LAENGEN.quelle_url),
  };

  // 9) Speichern. Das Ergebnis wird ehrlich zurückgegeben: Wenn hier etwas
  //    schiefgeht, darf das Formular keine Bestätigung anzeigen.
  const ergebnis = await contactAnlegen(kontakt);
  if (!ergebnis.ok) {
    return antworte(res, ergebnis.status, { ok: false, fehler: ergebnis.grund });
  }

  // 10) Benachrichtigung. Bewusst abgewartet, aber gekapselt: telegramMelden()
  //     wirft nie.
  await telegramMelden(kontakt);

  return antworte(res, 201, { ok: true, id: ergebnis.id });
}

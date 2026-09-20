// ETA Website – kleine Interaktionen. Kein Framework, kein Tracking.

// WhatsApp-Nummer (nur Ziffern, mit Ländervorwahl).
var WHATSAPP_NUMBER = "41764122122";

// Texte, die erst im Browser entstehen (Statusmeldungen, die vorbereitete
// WhatsApp-Nachricht) stehen nicht im HTML und können deshalb nicht über
// data-i18n laufen. Sie holen ihre Fassung hier aus demselben Wörterbuch.
// Solange noch keines geladen ist, gilt der deutsche Rückfall.
function t(schluessel, rueckfall) {
  try {
    var woerter = I18N_GELADEN[aktiveSprache];
    if (woerter && typeof woerter[schluessel] === "string" && woerter[schluessel] !== "") {
      return woerter[schluessel];
    }
  } catch (e) {}
  return rueckfall;
}

// CRM-Anbindung. Hier steht bewusst KEIN Schlüssel mehr: Das Formular schickt
// seine Daten an die eigene Funktion /api/lead, und erst die schreibt – mit
// einem Schlüssel, der nur auf dem Server liegt – nach Supabase. Alles, was im
// Browser steht, kann jeder lesen.
var LEAD_ENDPUNKT = "/api/lead";

// Schickt das Formular an /api/lead und liefert ein Versprechen auf
// { ok: true } oder { ok: false, fehler: "..." }. Wirft nicht.
function sendeAnLead(data) {
  var nutzlast = {
    vorname: data.get("vorname") || null,
    nachname: data.get("nachname") || null,
    name: data.get("name") || null,
    email: data.get("email") || null,
    vorwahl: data.get("vorwahl") || null,
    telefon: data.get("telefon") || null,
    strasse: data.get("strasse") || null,
    plz: data.get("plz") || null,
    ort: data.get("ort") || null,
    geburtsdatum: data.get("geburtsdatum") || null,
    sprache: (document.documentElement.lang || "de").slice(0, 2),
    behandlung: data.get("behandlung") || null,
    nachricht: data.get("nachricht") || null,
    einwilligung: data.get("einwilligung") ? "ja" : "",
    einwilligung_version: data.get("einwilligung_version") || "v1",
    // Honigtopf: bei echten Besuchern immer leer.
    website: data.get("website") || "",
    // Von welcher Behandlungsseite kam die Anfrage.
    quelle_url: window.location.href.split("#")[0],
  };

  return fetch(LEAD_ENDPUNKT, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(nutzlast),
  })
    .then(function (antwort) {
      return antwort
        .json()
        ["catch"](function () {
          return {};
        })
        .then(function (ergebnis) {
          if (antwort.ok && ergebnis && ergebnis.ok) return { ok: true };
          return {
            ok: false,
            fehler: (ergebnis && ergebnis.fehler) || t("js.fehler.server", "Serverfehler") + " (" + antwort.status + ").",
          };
        });
    })
    ["catch"](function (fehler) {
      console.error("Anfrage konnte nicht übermittelt werden:", fehler);
      return { ok: false, fehler: t("js.fehler.verbindung", "Keine Verbindung zum Server.") };
    });
}

function whatsappHref(text) {
  if (!WHATSAPP_NUMBER) return null;
  var url = "https://wa.me/" + WHATSAPP_NUMBER;
  if (text) url += "?text=" + encodeURIComponent(text);
  return url;
}

document.querySelectorAll(".js-whatsapp").forEach(function (el) {
  var href = whatsappHref(t("js.wa.erstkontakt", "Hallo ETA, ich interessiere mich für eine Behandlung."));
  if (href) {
    el.setAttribute("href", href);
    el.setAttribute("target", "_blank");
    el.setAttribute("rel", "noopener");
  } else {
    el.addEventListener("click", function (e) {
      e.preventDefault();
      alert(t("js.wa.nochnicht", "Unsere WhatsApp-Nummer wird in Kürze freigeschaltet. Bitte nutzen Sie solange das Anfrage-Formular auf der Kontaktseite."));
    });
  }
});

// ============================================================== Navigation
// Menü, Aufklappfelder, Suche und die feste WhatsApp-Blase.
//
// Vorher stand hier eine einzige Zeile: nav.classList.toggle("open"). Kein
// aria-expanded, kein Escape, kein Klick daneben, und die Aufklappfelder
// öffneten allein per :hover / :focus-within — am Handy gar nicht, mit der
// Tastatur als Falle (Befund responsiv B2, technik B5).
//
// ASSET_WURZEL wird weiter unten belegt; die Suche liest den Wert erst beim
// ersten Tastendruck, also lange danach.
(function () {
  var toggle = document.getElementById("nav-toggle");
  var nav = document.getElementById("main-nav");
  if (!toggle || !nav) return;

  var knoepfe = [].slice.call(nav.querySelectorAll(".nav-drop-knopf"));

  // Ob der Menüknopf gerade sichtbar ist, entscheidet das Stylesheet und
  // nicht eine hier wiederholte Pixelgrenze.
  function burgerModus() {
    return getComputedStyle(toggle).display !== "none";
  }

  function feldSetzen(knopf, offen) {
    knopf.setAttribute("aria-expanded", offen ? "true" : "false");
  }

  function alleFelderZu(ausser) {
    knoepfe.forEach(function (k) {
      if (k !== ausser) feldSetzen(k, false);
    });
  }

  function offenesFeld() {
    for (var i = 0; i < knoepfe.length; i++) {
      if (knoepfe[i].getAttribute("aria-expanded") === "true") return knoepfe[i];
    }
    return null;
  }

  function menueSetzen(offen) {
    nav.classList.toggle("open", offen);
    toggle.setAttribute("aria-expanded", offen ? "true" : "false");
    toggle.setAttribute(
      "aria-label",
      offen ? t("js.menue.schliessen", "Menü schliessen") : t("js.menue.oeffnen", "Menü öffnen"),
    );
    // Solange das Menü über der Seite liegt, hat die feste Blase dort nichts
    // verloren (Befund responsiv B12: im Querformat lag sie auf der Menüfläche).
    document.body.classList.toggle("menue-offen", offen);
    if (!offen) alleFelderZu(null);
  }

  // Alles, was im offenen Menü angesprungen werden kann — der Menüknopf
  // gehört dazu, er schliesst es wieder.
  function fokusZiele() {
    var liste = [toggle];
    var kandidaten = nav.querySelectorAll("a[href], button, input, select, textarea");
    for (var i = 0; i < kandidaten.length; i++) {
      var el = kandidaten[i];
      if (el.offsetWidth > 0 || el.offsetHeight > 0) liste.push(el);
    }
    return liste;
  }

  menueSetzen(false);

  toggle.addEventListener("click", function () {
    var offen = !nav.classList.contains("open");
    menueSetzen(offen);
    // Beim Öffnen in das Menü hinein, beim Schliessen zurück auf den Knopf.
    // Bewusst auf das <nav> und nicht auf den ersten Verweis: auf dem Suchfeld
    // würde am Handy sofort die Tastatur aufspringen.
    if (offen) nav.focus();
    else toggle.focus();
  });

  knoepfe.forEach(function (knopf) {
    knopf.addEventListener("click", function () {
      var offen = knopf.getAttribute("aria-expanded") !== "true";
      alleFelderZu(knopf);   // immer nur ein Feld offen, sonst wird das Menü zu lang
      feldSetzen(knopf, offen);
    });
  });

  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape") {
      var feld = offenesFeld();
      if (feld) {
        feldSetzen(feld, false);
        feld.focus();
        return;
      }
      if (nav.classList.contains("open")) {
        menueSetzen(false);
        toggle.focus();
      }
      return;
    }
    if (e.key !== "Tab" || !nav.classList.contains("open") || !burgerModus()) return;
    // Das offene Menü liegt über der Seite. Wer weitertabbt, landete sonst
    // unsichtbar im Inhalt dahinter.
    var ziele = fokusZiele();
    if (ziele.length < 2) return;
    var erste = ziele[0];
    var letzte = ziele[ziele.length - 1];
    if (e.shiftKey && (document.activeElement === erste || document.activeElement === nav)) {
      e.preventDefault();
      letzte.focus();
    } else if (!e.shiftKey && document.activeElement === letzte) {
      e.preventDefault();
      erste.focus();
    }
  });

  document.addEventListener("click", function (e) {
    if (toggle === e.target || toggle.contains(e.target)) return;
    if (!nav.contains(e.target)) {
      alleFelderZu(null);
      if (nav.classList.contains("open")) menueSetzen(false);
      return;
    }
    // Klick im Menü, aber ausserhalb der Gruppe, deren Feld offen ist.
    var feld = offenesFeld();
    if (feld && !feld.parentNode.contains(e.target)) alleFelderZu(null);
  });

  // Wird das Fenster breit genug für das Navigationsband, ist das
  // Aufklappmenü gegenstandslos. Beobachtet wird der Wechsel selbst, nicht
  // jede Grössenänderung — am Handy löst schon das Ein- und Ausblenden der
  // Adresszeile ein resize aus, und dabei soll kein Feld zuklappen.
  var warBurger = burgerModus();
  window.addEventListener("resize", function () {
    var jetzt = burgerModus();
    if (jetzt === warBurger) return;
    warBurger = jetzt;
    alleFelderZu(null);
    if (!jetzt) menueSetzen(false);
  });
})();

// =================================================================== Suche
// 101 Behandlungen, 5 Kategorien, kein Suchfeld: wer «Nasenkorrektur» suchte,
// musste wissen, dass sie unter «Plastische Chirurgie» liegt (Befund inhalt
// B11). Der Generator schreibt assets/suche.json (112 Einträge, 249
// Synonyme, 29 KB); hier wird gefiltert. Kein Server, kein Fremdpaket. Die
// Datei wird erst beim ersten Tastendruck geholt — wer nicht sucht, lädt sie
// nie.
(function () {
  var form = document.querySelector(".kopf-suche");
  var feld = document.getElementById("suche-feld");
  var liste = document.getElementById("suche-liste");
  var status = document.getElementById("suche-status");
  if (!form || !feld || !liste) return;

  var index = null;
  var laeuft = null;
  var treffer = [];
  var markiert = -1;

  // Zwei Schreibweisen, damit «Zähne», «Zaehne» und «Zahne» dasselbe finden.
  function ohneUmlaut(text) {
    return String(text || "").toLowerCase()
      .replace(/ä/g, "ae").replace(/ö/g, "oe").replace(/ü/g, "ue").replace(/ß/g, "ss")
      .replace(/[^a-z0-9]+/g, " ").trim();
  }
  function ohneZeichen(text) {
    var s = String(text || "").toLowerCase();
    if (s.normalize) s = s.normalize("NFD").replace(/[̀-ͯ]/g, "");
    return s.replace(/[^a-z0-9]+/g, " ").trim();
  }

  function melde(text) {
    if (status) status.textContent = text;
  }

  function laden() {
    if (index) return Promise.resolve(index);
    if (laeuft) return laeuft;
    var wurzel = ASSET_WURZEL === null ? "" : ASSET_WURZEL;
    laeuft = fetch(wurzel + "assets/suche.json", { credentials: "same-origin" })
      .then(function (antwort) {
        if (!antwort.ok) throw new Error("HTTP " + antwort.status);
        return antwort.json();
      })
      .then(function (daten) {
        index = (daten || []).map(function (e) {
          var alles = [e.n, e.t, e.k, (e.s || []).join(" "), e.d].join(" ");
          return {
            n: e.n,
            k: e.k,
            u: wurzel + e.u,
            name: ohneUmlaut(e.n) + " " + ohneZeichen(e.n),
            alles: ohneUmlaut(alles) + " " + ohneZeichen(alles),
          };
        });
        laeuft = null;
        return index;
      })["catch"](function (fehler) {
        console.error("Suchindex konnte nicht geladen werden:", fehler);
        laeuft = null;
        index = [];
        return index;
      });
    return laeuft;
  }

  function punkte(eintrag, fragen) {
    var best = 0;
    for (var i = 0; i < fragen.length; i++) {
      var q = fragen[i];
      if (!q) continue;
      var wert = 0;
      if (eintrag.name.indexOf(q) === 0) wert = 100;
      else if ((" " + eintrag.name).indexOf(" " + q) > -1) wert = 80;
      else if (eintrag.name.indexOf(q) > -1) wert = 60;
      else if ((" " + eintrag.alles).indexOf(" " + q) > -1) wert = 40;
      else if (eintrag.alles.indexOf(q) > -1) wert = 20;
      if (wert > best) best = wert;
    }
    return best;
  }

  function schliessen() {
    liste.hidden = true;
    liste.innerHTML = "";
    treffer = [];
    markiert = -1;
    feld.setAttribute("aria-expanded", "false");
    feld.removeAttribute("aria-activedescendant");
  }

  function markieren(i) {
    var kinder = liste.querySelectorAll(".suche-option");
    for (var k = 0; k < kinder.length; k++) {
      kinder[k].setAttribute("aria-selected", k === i ? "true" : "false");
    }
    markiert = i;
    if (i >= 0 && kinder[i]) {
      feld.setAttribute("aria-activedescendant", kinder[i].id);
      if (kinder[i].scrollIntoView) kinder[i].scrollIntoView({ block: "nearest" });
    } else {
      feld.removeAttribute("aria-activedescendant");
    }
  }

  function gehe(url) {
    window.location.href = url;
  }

  function zeigen() {
    liste.innerHTML = "";
    if (!treffer.length) {
      var leer = document.createElement("li");
      leer.className = "suche-leer";
      leer.textContent = t("js.suche.leer", "Nichts gefunden. Bitte anders formulieren oder den Katalog durchsehen.");
      liste.appendChild(leer);
      liste.hidden = false;
      feld.setAttribute("aria-expanded", "true");
      melde(t("js.suche.keine", "Keine Vorschläge."));
      return;
    }
    treffer.forEach(function (e, i) {
      var li = document.createElement("li");
      li.className = "suche-option";
      li.id = "suche-option-" + i;
      li.setAttribute("role", "option");
      li.setAttribute("aria-selected", "false");
      var name = document.createElement("span");
      name.className = "suche-name";
      name.textContent = e.n;
      var kat = document.createElement("span");
      kat.className = "suche-kat";
      kat.textContent = e.k;
      li.appendChild(name);
      li.appendChild(kat);
      // mousedown statt click: sonst schliesst der Fokusverlust die Liste,
      // bevor der Klick ankommt.
      li.addEventListener("mousedown", function (ev) {
        ev.preventDefault();
        gehe(e.u);
      });
      liste.appendChild(li);
    });
    liste.hidden = false;
    feld.setAttribute("aria-expanded", "true");
    markieren(-1);
    melde(treffer.length + " " + t("js.suche.treffer", "Vorschläge. Mit den Pfeiltasten auswählen, mit Eingabe öffnen."));
  }

  function suchen() {
    var roh = feld.value.trim();
    if (roh.length < 2) {
      schliessen();
      return;
    }
    laden().then(function (eintraege) {
      if (feld.value.trim() !== roh) return; // inzwischen weitergetippt
      var fragen = [ohneUmlaut(roh), ohneZeichen(roh)];
      var bewertet = [];
      for (var i = 0; i < eintraege.length; i++) {
        var p = punkte(eintraege[i], fragen);
        if (p > 0) bewertet.push({ e: eintraege[i], p: p, i: i });
      }
      bewertet.sort(function (a, b) {
        return b.p - a.p || a.e.n.length - b.e.n.length || a.i - b.i;
      });
      treffer = bewertet.slice(0, 8).map(function (x) {
        return x.e;
      });
      zeigen();
    });
  }

  feld.addEventListener("input", suchen);
  feld.addEventListener("focus", function () {
    if (feld.value.trim().length >= 2) suchen();
  });

  feld.addEventListener("keydown", function (e) {
    if (e.key === "ArrowDown" || e.key === "ArrowUp") {
      if (liste.hidden || !treffer.length) return;
      e.preventDefault();
      var n = treffer.length;
      markieren(e.key === "ArrowDown" ? (markiert + 1) % n : markiert <= 0 ? n - 1 : markiert - 1);
    } else if (e.key === "Enter") {
      if (markiert >= 0 && treffer[markiert]) {
        e.preventDefault();
        gehe(treffer[markiert].u);
      } else if (treffer.length) {
        e.preventDefault();
        gehe(treffer[0].u);
      }
    } else if (e.key === "Escape" && !liste.hidden) {
      // Erst die Vorschlagsliste, das Menü erst beim zweiten Druck.
      e.stopPropagation();
      schliessen();
    }
  });

  form.addEventListener("submit", function (e) {
    if (treffer.length) {
      e.preventDefault();
      gehe(treffer[markiert >= 0 ? markiert : 0].u);
    }
    // Sonst läuft das Formular durch: ohne Treffer führt es in den Katalog.
  });

  document.addEventListener("click", function (e) {
    if (!form.contains(e.target)) schliessen();
  });
})();

// Die feste WhatsApp-Blase tritt zurück, sobald die Fusszeile im Bild ist.
// Dort stehen dieselben Wege ohnehin ausgeschrieben, und sie verdeckte
// zuletzt Fusszeilen-Verweise und eine Preisbedingung (Befund responsiv B12).
(function () {
  var blase = document.querySelector(".wa-float");
  var fuss = document.querySelector(".site-footer");
  if (!blase || !fuss || !("IntersectionObserver" in window)) return;
  new IntersectionObserver(function (eintraege) {
    blase.classList.toggle("wa-float--ruht", eintraege[0].isIntersecting);
  }).observe(fuss);
})();

var form = document.getElementById("anfrage-form");
if (form) {
  var laeuft = false; // sperrt gegen Doppelklick

  form.addEventListener("submit", function (e) {
    e.preventDefault();
    if (laeuft) return;

    var data = new FormData(form);
    var status = document.getElementById("form-status");
    var knopf = form.querySelector('button[type="submit"]');
    var knopfText = knopf ? knopf.textContent : null;

    function melde(text, istFehler) {
      if (!status) return;
      status.textContent = text;
      status.classList.toggle("fehler", !!istFehler);
      status.hidden = false;
    }

    function freigeben() {
      laeuft = false;
      if (knopf) {
        knopf.disabled = false;
        if (knopfText !== null) knopf.textContent = knopfText;
      }
    }

    laeuft = true;
    if (knopf) {
      knopf.disabled = true;
      knopf.textContent = t("js.knopf.sendet", "Wird gesendet …");
    }
    melde(t("js.status.uebermittelt", "Ihre Anfrage wird übermittelt …"), false);

    // Erst speichern, dann reden. Die Bestätigung erscheint ausschliesslich,
    // wenn der Server das Speichern tatsächlich bestätigt hat.
    sendeAnLead(data).then(function (ergebnis) {
      if (!ergebnis.ok) {
        freigeben();
        var wa = whatsappHref(t("js.wa.formularfehler", "Hallo ETA, mein Formular auf der Website liess sich nicht absenden. Ich melde mich deshalb hier."));
        melde(
          t("js.fehler.nichtgespeichert", "Ihre Anfrage konnte nicht gespeichert werden:") + " " +
            ergebnis.fehler +
            (wa
              ? " " + t("js.fehler.wegwa", "Bitte versuchen Sie es erneut oder schreiben Sie uns direkt per WhatsApp an +41 76 412 21 22.")
              : " " + t("js.fehler.wegmail", "Bitte versuchen Sie es erneut oder schreiben Sie uns an info@eta-agency.ch.")),
          true,
        );
        return;
      }

      // Gespeichert. Der WhatsApp-Weg ist danach ein Angebot — und zwar
      // eines, das der Besucher selbst annimmt.
      //
      // Vorher stand hier window.open() mit einer fertigen Nachricht, die
      // Name, Adresse, Geburtsdatum, Telefon, gewuenschte Behandlung und den
      // Freitext enthielt. Zwei Gruende, warum das hier nicht mehr steht:
      //
      //   1. Die gewuenschte Behandlung ist ein Gesundheitsdatum (revDSG
      //      Art. 5 lit. c, DSGVO Art. 9). data/recht.json sagt im Abschnitt
      //      «Wenn Sie uns über WhatsApp schreiben» woertlich, das Formular
      //      «schreibt keine Gesundheitsangaben in eine WhatsApp-Nachricht».
      //      Genau das tat es. Jetzt geht nur noch der Name mit — alles
      //      Weitere liegt bereits gespeichert bei ETA.
      //   2. window.open() aus einem Promise heraus ist keine direkte
      //      Nutzeraktion mehr; die meisten Browser blockieren das Fenster.
      //      Ein Verweis, den man antippt, oeffnet zuverlaessig.
      var name = ((data.get("vorname") || "") + " " + (data.get("nachname") || "")).trim() || data.get("name") || "";
      var zeilen = [
        t("js.wa.nachformular", "Guten Tag ETA, ich habe soeben das Formular auf der Website ausgefüllt."),
        name ? t("js.anfrage.name", "Name:") + " " + name : null,
      ].filter(Boolean);
      var href = whatsappHref(zeilen.join("\n"));

      melde(t("js.status.eingegangen", "Ihre Anfrage ist bei uns eingegangen. Wir melden uns in der Regel noch am selben Tag."), false);
      if (href && status) {
        var wahl = document.createElement("a");
        wahl.className = "link";
        wahl.href = href;
        wahl.target = "_blank";
        wahl.rel = "noopener";
        wahl.textContent = t("js.status.wazusatz", "Wenn Sie zusätzlich direkt schreiben möchten: per WhatsApp");
        status.appendChild(document.createTextNode(" "));
        status.appendChild(wahl);
      }

      // Formular leeren, damit dieselbe Anfrage nicht versehentlich ein zweites
      // Mal abgeschickt wird. Der Knopf bleibt bewusst gesperrt.
      form.reset();
      if (knopf) knopf.textContent = t("js.knopf.gesendet", "Anfrage gesendet");
    });
  });
}

// ------------------------------------------------------------- Sprachauswahl
// Die Wörterbücher stehen nicht mehr hier, sondern liegen als flache JSON-Dateien
// unter assets/i18n/<lang>.json. Sie werden beim Umschalten nachgeladen und
// danach im Speicher behalten, damit Hin- und Herschalten nichts neu lädt.

var SPRACHEN = ["de", "en", "tr", "ar"];
var SPRACH_SPEICHER = "eta_lang";

// Pfad zur Wurzel. Die Seiten liegen bis zu zwei Ebenen tief, deshalb wird der
// Pfad aus dem bereits vorhandenen Verweis auf main.js abgeleitet (ersatzweise
// aus dem Stylesheet-Verweis). Nicht geraten, nicht aus der Adresse gezählt.
var ASSET_WURZEL = (function () {
  var kandidaten = [];
  if (document.currentScript && document.currentScript.src) {
    kandidaten.push([document.currentScript.src, "assets/js/main.js"]);
  }
  document.querySelectorAll("script[src]").forEach(function (el) {
    kandidaten.push([el.src, "assets/js/main.js"]);
  });
  document.querySelectorAll('link[rel~="stylesheet"][href]').forEach(function (el) {
    kandidaten.push([el.href, "assets/css/style.css"]);
  });
  for (var i = 0; i < kandidaten.length; i++) {
    var url = String(kandidaten[i][0] || "").split("#")[0].split("?")[0];
    var ende = kandidaten[i][1];
    if (url.length > ende.length && url.slice(-ende.length) === ende) {
      return url.slice(0, url.length - ende.length);
    }
  }
  return null;
})();

var I18N_GELADEN = {};   // Sprache -> Wörterbuch (Zwischenspeicher)
var I18N_UNTERWEGS = {}; // Sprache -> laufender Ladevorgang
var aktiveSprache = null;
var gewuenschteSprache = null;

function istText(wert) {
  return typeof wert === "string" && wert !== "";
}

// Deutscher Ursprungszustand, falls ein Schlüssel in einer Sprachdatei fehlt.
function ursprungsText(el) {
  if (typeof el._etaText !== "string") el._etaText = el.textContent;
  return el._etaText;
}

function ursprungsAttribut(el, attr) {
  if (!el._etaAttr) el._etaAttr = {};
  if (!(attr in el._etaAttr)) el._etaAttr[attr] = el.getAttribute(attr);
  return el._etaAttr[attr];
}

function ladeWoerterbuch(lang) {
  if (I18N_GELADEN[lang]) return Promise.resolve(I18N_GELADEN[lang]);
  if (I18N_UNTERWEGS[lang]) return I18N_UNTERWEGS[lang];
  // Der <head> hat die Datei für die Startsprache schon angefordert, während
  // das Stylesheet noch lud. Hier wird sie nur abgeholt — kein zweiter Abruf.
  // Ist dort etwas schiefgegangen (kein fetch, Netzfehler, leere Antwort),
  // liefert das Versprechen null, und es läuft der normale Weg darunter.
  if (window.__etaWoerter && lang === window.__etaSprache) {
    var vorlauf = window.__etaWoerter.then(function (daten) {
      if (!daten || typeof daten !== "object") throw new Error("Vorlauf ohne Inhalt");
      I18N_GELADEN[lang] = daten;
      delete I18N_UNTERWEGS[lang];
      return daten;
    })["catch"](function () {
      delete I18N_UNTERWEGS[lang];
      window.__etaWoerter = null;   // beim nächsten Versuch der normale Weg
      return ladeWoerterbuch(lang);
    });
    I18N_UNTERWEGS[lang] = vorlauf;
    return vorlauf;
  }
  if (ASSET_WURZEL === null) return Promise.reject(new Error("Wurzelpfad nicht ermittelbar"));
  var lauf = fetch(ASSET_WURZEL + "assets/i18n/" + lang + ".json", { credentials: "same-origin" })
    .then(function (antwort) {
      if (!antwort.ok) throw new Error("HTTP " + antwort.status);
      return antwort.json();
    })
    .then(function (daten) {
      if (!daten || typeof daten !== "object") throw new Error("Sprachdatei unbrauchbar");
      I18N_GELADEN[lang] = daten;
      delete I18N_UNTERWEGS[lang];
      return daten;
    })["catch"](function (fehler) {
      delete I18N_UNTERWEGS[lang];
      throw fehler;
    });
  I18N_UNTERWEGS[lang] = lauf;
  return lauf;
}

function schalterMarkieren(lang) {
  document.querySelectorAll(".lang-switch [data-lang]").forEach(function (el) {
    el.classList.toggle("active", el.getAttribute("data-lang") === lang);
  });
}

// Setzt alles in einem Durchgang, damit die Seite nicht flackert oder springt.
function texteAnwenden(woerter, lang) {
  var scrollY = window.pageYOffset;
  var wurzel = document.documentElement;

  wurzel.lang = lang === "de" ? "de-CH" : lang;
  wurzel.dir = lang === "ar" ? "rtl" : "ltr";
  wurzel.setAttribute("data-lang", lang);

  document.querySelectorAll("[data-i18n]").forEach(function (el) {
    var alt = ursprungsText(el); // einmalig den deutschen Ursprung sichern
    var wert = woerter[el.getAttribute("data-i18n")];
    if (!istText(wert)) wert = alt; // Schlüssel fehlt -> deutscher Text bleibt
    if (!istText(wert)) return; // nie leeren
    if (el.tagName === "TITLE") {
      if (document.title !== wert) document.title = wert;
    } else if (el.textContent !== wert) {
      el.textContent = wert;
    }
  });

  document.querySelectorAll("[data-i18n-attr]").forEach(function (el) {
    var paare = el.getAttribute("data-i18n-attr").split(";");
    for (var i = 0; i < paare.length; i++) {
      var stueck = paare[i].trim();
      if (!stueck) continue;
      var trenner = stueck.indexOf(":");
      if (trenner < 1) continue;
      var attr = stueck.slice(0, trenner).trim();
      var schluessel = stueck.slice(trenner + 1).trim();
      if (!attr || !schluessel) continue;
      var alt = ursprungsAttribut(el, attr);
      var wert = woerter[schluessel];
      if (!istText(wert)) wert = alt;
      if (!istText(wert)) continue;
      if (el.getAttribute(attr) !== wert) el.setAttribute(attr, wert);
    }
  });

  var region = woerter["contact.region"];
  document.querySelectorAll("[data-i18n-region]").forEach(function (el) {
    var alt = ursprungsText(el);
    var wert = istText(region) ? region : alt;
    if (istText(wert) && el.textContent !== wert) el.textContent = wert;
  });

  var banner = document.getElementById("lang-banner");
  if (banner) {
    var hinweis = woerter["banner.other_lang"];
    if (istText(hinweis)) {
      banner.textContent = hinweis;
      banner.hidden = false;
    } else {
      banner.hidden = true;
    }
  }

  schalterMarkieren(lang);
  aktiveSprache = lang;

  if (scrollY && window.pageYOffset !== scrollY) window.scrollTo(0, scrollY);
}

// Wechselt die Sprache. Bis die Datei da ist, bleibt die Seite unverändert.
function applyLang(lang, speichern) {
  if (SPRACHEN.indexOf(lang) < 0) lang = "de";
  if (lang === aktiveSprache) {
    schalterMarkieren(lang);
    return;
  }
  gewuenschteSprache = lang;
  schalterMarkieren(lang);
  ladeWoerterbuch(lang).then(function (woerter) {
    if (gewuenschteSprache !== lang) return; // inzwischen wurde weitergeklickt
    texteAnwenden(woerter, lang);
    if (speichern) {
      try {
        localStorage.setItem(SPRACH_SPEICHER, lang);
      } catch (e) {}
    }
  })["catch"](function (fehler) {
    console.error("Sprachdatei konnte nicht geladen werden (" + lang + "):", fehler);
    if (gewuenschteSprache !== lang) return;
    gewuenschteSprache = aktiveSprache;
    schalterMarkieren(aktiveSprache || "de");
  });
}

function gespeicherteSprache() {
  var wert = null;
  try {
    wert = localStorage.getItem(SPRACH_SPEICHER);
  } catch (e) {}
  return SPRACHEN.indexOf(wert) >= 0 ? wert : null;
}

// Erster Besuch ohne gespeicherte Wahl: Browsersprache auswerten.
function browserSprache() {
  var liste = [];
  if (navigator.languages && navigator.languages.length) {
    liste = [].slice.call(navigator.languages);
  } else if (navigator.language) {
    liste = [navigator.language];
  }
  for (var i = 0; i < liste.length; i++) {
    var code = String(liste[i] || "").toLowerCase().split("-")[0];
    if (SPRACHEN.indexOf(code) >= 0) return code;
  }
  return "de";
}

document.querySelectorAll(".lang-switch [data-lang]").forEach(function (el) {
  el.addEventListener("click", function (e) {
    e.preventDefault();
    applyLang(el.getAttribute("data-lang"), true);
  });
});

// Auch Deutsch läuft über de.json, damit Zurückschalten sauber funktioniert.
applyLang(gespeicherteSprache() || browserSprache(), false);


// ETA Website – kleine Interaktionen. Kein Framework, kein Tracking.

// WhatsApp-Nummer (nur Ziffern, mit Ländervorwahl).
var WHATSAPP_NUMBER = "41764122122";

// CRM-Anbindung (Supabase). anon/publishable Key, RLS erlaubt nur INSERT in "contacts" von aussen.
var SUPABASE_URL = "https://awhqwahhdhlbdgmrmfxv.supabase.co";
var SUPABASE_ANON_KEY = "sb_publishable_pTHTAGR5HtmG4GESYXRYFg_HX0EBdJH";

function parseGeburtsdatum(raw) {
  var m = /^(\d{1,2})\.(\d{1,2})\.(\d{4})$/.exec((raw || "").trim());
  if (!m) return null;
  var tag = m[1].padStart(2, "0"), monat = m[2].padStart(2, "0");
  return m[3] + "-" + monat + "-" + tag;
}

function sendToCrm(data) {
  var geburtsdatum = parseGeburtsdatum(data.get("geburtsdatum"));
  var notizen = geburtsdatum ? null : (data.get("geburtsdatum") ? "Geburtsdatum (Rohtext): " + data.get("geburtsdatum") : null);
  var vorname = data.get("vorname");
  var nachname = data.get("nachname");
  if (!vorname && !nachname && data.get("name")) {
    var teile = data.get("name").trim().split(/\s+/);
    vorname = teile.shift() || null;
    nachname = teile.join(" ") || null;
  }
  var payload = {
    vorname: vorname || null,
    nachname: nachname || null,
    email: data.get("email") || null,
    telefon_vorwahl: data.get("vorwahl") || null,
    telefon: data.get("telefon") || null,
    strasse: data.get("strasse") || null,
    plz: data.get("plz") || null,
    ort: data.get("ort") || null,
    geburtsdatum: geburtsdatum,
    sprache: (document.documentElement.lang || "de").slice(0, 2),
    quelle: "formular",
    gewuenschte_behandlung: data.get("behandlung") || null,
    nachricht: data.get("nachricht") || null,
    notizen: notizen,
    dsgvo_einwilligung: true,
    dsgvo_einwilligung_at: new Date().toISOString(),
  };
  return fetch(SUPABASE_URL + "/rest/v1/contacts", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      apikey: SUPABASE_ANON_KEY,
      Authorization: "Bearer " + SUPABASE_ANON_KEY,
      Prefer: "return=minimal",
    },
    body: JSON.stringify(payload),
  });
}

function whatsappHref(text) {
  if (!WHATSAPP_NUMBER) return null;
  var url = "https://wa.me/" + WHATSAPP_NUMBER;
  if (text) url += "?text=" + encodeURIComponent(text);
  return url;
}

document.querySelectorAll(".js-whatsapp").forEach(function (el) {
  var href = whatsappHref("Hallo ETA, ich interessiere mich für eine Behandlung.");
  if (href) {
    el.setAttribute("href", href);
    el.setAttribute("target", "_blank");
    el.setAttribute("rel", "noopener");
  } else {
    el.addEventListener("click", function (e) {
      e.preventDefault();
      alert("Unsere WhatsApp-Nummer wird in Kürze freigeschaltet. Bitte nutzen Sie solange das Anfrage-Formular auf der Kontaktseite.");
    });
  }
});

var toggle = document.getElementById("nav-toggle");
var nav = document.getElementById("main-nav");
if (toggle && nav) {
  toggle.addEventListener("click", function () {
    nav.classList.toggle("open");
  });
}

var form = document.getElementById("anfrage-form");
if (form) {
  form.addEventListener("submit", function (e) {
    e.preventDefault();
    var data = new FormData(form);
    var name = ((data.get("vorname") || "") + " " + (data.get("nachname") || "")).trim() || data.get("name") || "";
    var adresse = ((data.get("strasse") || "") + ", " + (data.get("plz") || "") + " " + (data.get("ort") || "")).replace(/^,\s*|,\s*$/g, "").trim();
    var telefon = ((data.get("vorwahl") || "") + " " + (data.get("telefon") || "")).trim();
    var zeilen = [
      "Neue Anfrage über die ETA-Website:",
      "Name: " + name,
      adresse ? "Adresse: " + adresse : null,
      data.get("geburtsdatum") ? "Geburtsdatum: " + data.get("geburtsdatum") : null,
      telefon ? "Telefon: " + telefon : null,
      "E-Mail: " + (data.get("email") || ""),
      "Behandlung: " + (data.get("behandlung") || ""),
      data.get("nachricht") ? "Nachricht: " + data.get("nachricht") : null,
    ].filter(Boolean);
    var text = zeilen.join("\n");
    var href = whatsappHref(text);
    var status = document.getElementById("form-status");
    sendToCrm(data)["catch"](function (err) {
      console.error("CRM-Übermittlung fehlgeschlagen:", err);
    });
    if (href) {
      window.open(href, "_blank", "noopener");
      if (status) {
        status.textContent = "Ihre Anfrage wurde gespeichert und für WhatsApp vorbereitet. Bitte senden Sie die Nachricht dort ab.";
        status.hidden = false;
      }
    } else if (status) {
      status.textContent = "Ihre Anfrage wurde gespeichert. Wir melden uns in der Regel noch am selben Tag.";
      status.hidden = false;
    }
  });
}

// ------------------------------------------------------------- Sprachauswahl
var I18N = {
  de: {
    "nav.behandlungen": "Behandlungen", "nav.partnerklinik": "Partnerklinik", "nav.ablauf": "Ablauf",
    "nav.finanzierung": "Finanzierung", "nav.vorhernachher": "Vorher / Nachher", "nav.kontakt": "Kontakt", "nav.whatsapp": "WhatsApp",
    "nav.kat.hautbeauty": "Haut & Beauty", "nav.kat.plastischechirurgie": "Plastische Chirurgie",
    "nav.kat.haartransplantation": "Haartransplantation", "nav.kat.zaehne": "Zähne", "nav.kat.medizinischefachbereiche": "Medizinische Fachbereiche",
    "hero.eyebrow": "European Turkey Asia",
    "hero.headline": "Ihre Schönheitsbehandlung in Istanbul. Betreut von A bis Z.",
    "hero.sub": "Deutschsprachige Beratung, eine fest geprüfte Partnerklinik und ein Rundum-Paket mit Transfer, Hotel und Nachsorge. Sie kümmern sich um nichts ausser sich selbst.",
    "hero.cta1": "Unverbindlich anfragen", "hero.cta2": "Behandlungen entdecken",
    "hero.trust1": "Deutschsprachige Betreuung", "hero.trust2": "Fixe Partnerklinik", "hero.trust3": "Transfer & Hotel inklusive",
    "footer.tagline": "Ihre Agentur für Schönheitsbehandlungen in Istanbul, mit Betreuung aus der Schweiz, Österreich und Deutschland.",
    "contact.region": "Schweiz, Österreich, Deutschland",
    "banner.other_lang": ""
  },
  en: {
    "nav.behandlungen": "Treatments", "nav.partnerklinik": "Partner Clinic", "nav.ablauf": "Process",
    "nav.finanzierung": "Financing", "nav.vorhernachher": "Before / After", "nav.kontakt": "Contact", "nav.whatsapp": "WhatsApp",
    "nav.kat.hautbeauty": "Skin & Beauty", "nav.kat.plastischechirurgie": "Plastic Surgery",
    "nav.kat.haartransplantation": "Hair Transplant", "nav.kat.zaehne": "Dental", "nav.kat.medizinischefachbereiche": "Medical Departments",
    "hero.eyebrow": "European Turkey Asia",
    "hero.headline": "Your beauty treatment in Istanbul. Taken care of, start to finish.",
    "hero.sub": "Advice in German or English, a carefully vetted partner clinic and an all-inclusive package with transfer, hotel and aftercare. You take care of nothing but yourself.",
    "hero.cta1": "Request a free consultation", "hero.cta2": "Explore treatments",
    "hero.trust1": "Support in German & English", "hero.trust2": "Trusted partner clinic", "hero.trust3": "Transfer & hotel included",
    "footer.tagline": "Your agency for beauty treatments in Istanbul, with support from Europe.",
    "contact.region": "Europe",
    "banner.other_lang": "This page is currently available in German. Our team is also happy to help you in English, Turkish and Arabic via WhatsApp."
  },
  tr: {
    "nav.behandlungen": "Tedaviler", "nav.partnerklinik": "Anlaşmalı Klinik", "nav.ablauf": "Süreç",
    "nav.finanzierung": "Finansman", "nav.vorhernachher": "Öncesi / Sonrası", "nav.kontakt": "İletişim", "nav.whatsapp": "WhatsApp",
    "nav.kat.hautbeauty": "Cilt ve Güzellik", "nav.kat.plastischechirurgie": "Plastik Cerrahi",
    "nav.kat.haartransplantation": "Saç Ekimi", "nav.kat.zaehne": "Diş Estetiği", "nav.kat.medizinischefachbereiche": "Tıbbi Birimler",
    "hero.eyebrow": "European Turkey Asia",
    "hero.headline": "İstanbul'da güzellik tedaviniz. Baştan sona bizimle.",
    "hero.sub": "Almanca ve İngilizce danışmanlık, özenle seçilmiş bir anlaşmalı klinik ve transfer, otel ile bakımı içeren eksiksiz bir paket. Siz sadece kendinizle ilgilenin.",
    "hero.cta1": "Ücretsiz ön görüşme talep edin", "hero.cta2": "Tedavileri keşfedin",
    "hero.trust1": "Almanca & İngilizce destek", "hero.trust2": "Güvenilir anlaşmalı klinik", "hero.trust3": "Transfer ve otel dahil",
    "footer.tagline": "İstanbul'daki güzellik tedavileri için Avrupa'dan destek sunan acenteniz.",
    "contact.region": "Avrupa",
    "banner.other_lang": "Bu sayfa şu anda yalnızca Almanca olarak mevcuttur. Ekibimiz WhatsApp üzerinden Türkçe olarak da size yardımcı olmaktan memnuniyet duyar."
  },
  ar: {
    "nav.behandlungen": "العلاجات", "nav.partnerklinik": "العيادة الشريكة", "nav.ablauf": "خطوات العمل",
    "nav.finanzierung": "التمويل", "nav.vorhernachher": "قبل / بعد", "nav.kontakt": "اتصل بنا", "nav.whatsapp": "واتساب",
    "nav.kat.hautbeauty": "الجلد والجمال", "nav.kat.plastischechirurgie": "الجراحة التجميلية",
    "nav.kat.haartransplantation": "زراعة الشعر", "nav.kat.zaehne": "طب الأسنان", "nav.kat.medizinischefachbereiche": "الأقسام الطبية",
    "hero.eyebrow": "European Turkey Asia",
    "hero.headline": "علاج التجميل الخاص بكم في إسطنبول. نرافقكم خطوة بخطوة.",
    "hero.sub": "استشارة بالألمانية والإنجليزية، عيادة شريكة تم اختيارها بعناية، وباقة شاملة تضم النقل والفندق والمتابعة بعد العلاج. لا داعي للقلق بشأن أي شيء آخر.",
    "hero.cta1": "اطلب استشارة مجانية", "hero.cta2": "استكشف العلاجات",
    "hero.trust1": "دعم بالألمانية والإنجليزية", "hero.trust2": "عيادة شريكة موثوقة", "hero.trust3": "النقل والفندق مشمولان",
    "footer.tagline": "وكالتكم لعلاجات التجميل في إسطنبول، بدعم من أوروبا.",
    "contact.region": "أوروبا",
    "banner.other_lang": "هذه الصفحة متاحة حاليًا باللغة الألمانية فقط. يسعد فريقنا بمساعدتكم أيضًا باللغة العربية عبر واتساب."
  }
};

function applyLang(lang) {
  if (!I18N[lang]) lang = "de";
  document.documentElement.lang = lang === "de" ? "de-CH" : lang;
  document.documentElement.dir = lang === "ar" ? "rtl" : "ltr";
  document.querySelectorAll("[data-i18n]").forEach(function (el) {
    var val = I18N[lang][el.getAttribute("data-i18n")];
    if (val) el.textContent = val;
  });
  document.querySelectorAll("[data-i18n-region]").forEach(function (el) {
    el.textContent = I18N[lang]["contact.region"];
  });
  var banner = document.getElementById("lang-banner");
  if (banner) {
    var msg = I18N[lang]["banner.other_lang"];
    if (msg) {
      banner.textContent = msg;
      banner.hidden = false;
    } else {
      banner.hidden = true;
    }
  }
  document.querySelectorAll(".lang-switch [data-lang]").forEach(function (el) {
    el.classList.toggle("active", el.getAttribute("data-lang") === lang);
  });
  try {
    localStorage.setItem("eta_lang", lang);
  } catch (e) {}
}

document.querySelectorAll(".lang-switch [data-lang]").forEach(function (el) {
  el.addEventListener("click", function (e) {
    e.preventDefault();
    applyLang(el.getAttribute("data-lang"));
  });
});

var savedLang = "de";
try {
  savedLang = localStorage.getItem("eta_lang") || "de";
} catch (e) {}
applyLang(savedLang);

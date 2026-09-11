#!/usr/bin/env python3
"""Generiert die statische ETA-Website aus data/behandlungen.json + data/beschreibungen.json.

Aufruf: python3 scripts/build_site.py
Output: site/ (kompletter Webroot, deploybar auf GitHub Pages)
"""
import json
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "docs"
DATA = ROOT / "data"
BASE_URL = "https://ffitzindustries.github.io/eta-website"

KATALOG = json.loads((DATA / "behandlungen.json").read_text())
BESCHREIBUNGEN = json.loads((DATA / "beschreibungen.json").read_text())


def load_bild_manifest():
    """Sammelt slug -> Bildpfad aus allen behandlung-bilder-manifest-*.json (von Higgsfield-Agenten geschrieben).
    Bilder muessen unter static/assets/ liegen (die Quelle, die build_site.py nach site/assets/ kopiert),
    nicht direkt unter site/assets/, da site/ bei jedem Build komplett neu aufgebaut wird."""
    bilder = {}
    static_assets = ROOT / "static" / "assets"
    for f in DATA.glob("behandlung-bilder-manifest-*.json"):
        for eintrag in json.loads(f.read_text()):
            if eintrag.get("status") == "ok" and eintrag.get("path") and (static_assets / Path(eintrag["path"]).relative_to("assets")).exists():
                bilder[eintrag["slug"]] = eintrag["path"]
    return bilder


BEHANDLUNG_BILDER = load_bild_manifest()

KAT_ICONS = {
    "plastische-chirurgie": '<path d="M12 3l2 6 6 2-6 2-2 6-2-6-6-2 6-2 2-6z"/>',
    "haartransplantation": '<path d="M6 3c3 3-3 6 0 10s-3 5 0 8"/><path d="M12 3c3 3-3 6 0 10s-3 5 0 8"/><path d="M18 3c3 3-3 6 0 10s-3 5 0 8"/>',
    "zaehne": '<path d="M12 3c-2 0-3 1.2-4.8 1.2S4 5 4 8c0 2.8 1.4 3.8 1.9 5.6.5 1.7.6 6.4 2.4 6.4 1.5 0 1-3.8 3.7-3.8s2.2 3.8 3.7 3.8c1.8 0 1.9-4.7 2.4-6.4.5-1.8 1.9-2.8 1.9-5.6 0-3-1.4-3.8-3.2-3.8S14 3 12 3z"/>',
    "haut-beauty": '<path d="M12 3s6 7 6 11a6 6 0 0 1-12 0c0-4 6-11 6-11z"/>',
    "medizinische-fachbereiche": '<path d="M4 20V6h16v14"/><path d="M9 20v-5h6v5"/><path d="M12 8v4"/><path d="M10 10h4"/>',
}
KAT_TEASER = {
    "plastische-chirurgie": "Brustvergrösserung, Fettabsaugung, Nasenkorrektur, Lidstraffung und mehr.",
    "haartransplantation": "FUE, DHI und Saphir-Technik, auch für Bart und Augenbrauen.",
    "zaehne": "Hollywood Smile, Implantate, Veneers und Bleaching.",
    "haut-beauty": "Botox, Lippenunterspritzung, Laser und Hautverjüngung.",
    "medizinische-fachbereiche": "Die Fachabteilungen unserer Partnerklinik, von Dermatologie bis HNO.",
}
KAT_INTRO = {
    "plastische-chirurgie": "Eingriffe, durchgeführt von den Fachärztinnen und Fachärzten unserer Partnerklinik in Istanbul. Jede Behandlung beginnt mit einem persönlichen Beratungsgespräch auf Deutsch.",
    "haartransplantation": "Moderne Techniken für dichtes, natürlich wachsendes Haar, für Sie und Ihn. Beratung und Haaranalyse auf Deutsch, Eingriff in Istanbul.",
    "zaehne": "Zahnästhetik und Zahnbehandlungen in der Zahnklinik unserer Partnerklinik, vom Bleaching bis zum kompletten Hollywood Smile.",
    "haut-beauty": "Medizinische Ästhetik von Botox über Filler bis zur Laserbehandlung. Vieles davon bietet unser Nachsorge-Partner Riverside Beauty auch im Rheintal an.",
    "medizinische-fachbereiche": "Unsere Partnerklinik ist ein medizinisches Zentrum mit eigenen Fachabteilungen. Auf Wunsch kombinieren wir Ihre Behandlung mit einer fachärztlichen Abklärung vor Ort.",
}

WA_SVG = '<svg width="{s}" height="{s}" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 005.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 00-3.48-8.413"/></svg>'


def wa_button(label, size=18, cls="btn btn-gold", i18n=""):
    i18n_attr = f' data-i18n="{i18n}"' if i18n else ""
    return f'<a href="#" class="{cls} js-whatsapp">{WA_SVG.format(s=size)}<span{i18n_attr}>{label}</span></a>'


UMLAUT_MAP = str.maketrans({"ä": "ae", "ö": "oe", "ü": "ue", "ß": "ss"})


def slugify(s):
    s = s.lower().translate(UMLAUT_MAP)
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s


NAV_KAT_ORDER = ["haut-beauty", "plastische-chirurgie", "haartransplantation", "zaehne", "medizinische-fachbereiche"]
NAV_KAT_I18N = {
    "haut-beauty": "nav.kat.hautbeauty",
    "plastische-chirurgie": "nav.kat.plastischechirurgie",
    "haartransplantation": "nav.kat.haartransplantation",
    "zaehne": "nav.kat.zaehne",
    "medizinische-fachbereiche": "nav.kat.medizinischefachbereiche",
}


def nav_kat_dropdowns(prefix, active):
    kmap = {k["id"]: k for k in kats()}
    out = ""
    for kid in NAV_KAT_ORDER:
        k = kmap[kid]
        cls = ' class="active"' if active == kid else ""
        anzahl = kat_count(k)
        wide = " wide" if anzahl > 12 else ""
        gruppen_html = ""
        for g in k["gruppen"]:
            behandlungen_links = "".join(
                f'<a href="{prefix}behandlungen/{kid}/{b["slug"]}.html">{b["name_de"]}</a>'
                for b in g["behandlungen"]
            )
            gruppen_html += (
                f'<div class="nav-drop-group">'
                f'<a class="nav-drop-group-label" href="{prefix}behandlungen/{kid}/index.html#{slugify(g["name_de"])}">{g["name_de"]}</a>'
                f'{behandlungen_links}'
                f'</div>'
            )
        out += (
            f'<div class="nav-drop"><a href="{prefix}behandlungen/{kid}/index.html"{cls} data-i18n="{NAV_KAT_I18N[kid]}">{k["name_de"]}</a>'
            f'<div class="nav-drop-panel{wide}">{gruppen_html}</div></div>'
        )
    return out


def head(title, desc, prefix, canonical):
    return f"""<!DOCTYPE html>
<html lang="de-CH">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title}</title>
  <meta name="description" content="{desc}">
  <link rel="canonical" href="{canonical}">
  <meta name="theme-color" content="#050505">
  <meta property="og:type" content="website">
  <meta property="og:locale" content="de_CH">
  <meta property="og:site_name" content="ETA – European Turkey Asia">
  <meta property="og:title" content="{title}">
  <meta property="og:description" content="{desc}">
  <meta property="og:image" content="{BASE_URL}/assets/img/og-image.jpg">
  <link rel="icon" href="{prefix}assets/img/favicon.png" type="image/png">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@400;500;600;700&family=Jost:wght@300;400;500;600&display=swap">
  <link rel="stylesheet" href="{prefix}assets/css/style.css">
</head>
<body>"""


def header_nav(prefix, active=""):
    def a(href, label, key, i18n=""):
        cls = ' class="active"' if key == active else ""
        i18n_attr = f' data-i18n="{i18n}"' if i18n else ""
        return f'<a href="{href}"{cls}{i18n_attr}>{label}</a>'

    return f"""
<header class="site-header">
  <div class="header-utility">
    <a href="{prefix}index.html" class="logo-link"><img src="{prefix}assets/img/eta-logo.png" alt="ETA – European Turkey Asia" class="logo"></a>
    <div class="header-actions">
      <div class="lang-switch" role="group" aria-label="Sprache wählen">
        <a href="#" data-lang="de">DE</a><a href="#" data-lang="en">EN</a><a href="#" data-lang="tr">TR</a><a href="#" data-lang="ar">AR</a>
      </div>
      {wa_button('WhatsApp', 17, 'btn btn-gold btn-sm', 'nav.whatsapp')}
      <button class="nav-toggle" id="nav-toggle" aria-label="Menü öffnen">
        <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7"><path d="M4 7h16"/><path d="M4 12h16"/><path d="M4 17h16"/></svg>
      </button>
    </div>
  </div>
  <nav class="main-nav" id="main-nav">
    <div class="main-nav-inner">
      {nav_kat_dropdowns(prefix, active)}
      {a(prefix + 'partnerklinik.html', 'Partnerklinik', 'partnerklinik', 'nav.partnerklinik')}
      {a(prefix + 'finanzierung.html', 'Finanzierung', 'finanzierung', 'nav.finanzierung')}
      {a(prefix + 'vorher-nachher.html', 'Vorher / Nachher', 'vorher-nachher', 'nav.vorhernachher')}
      {a(prefix + 'kontakt.html', 'Kontakt', 'kontakt', 'nav.kontakt')}
    </div>
  </nav>
</header>
<a href="#" class="wa-float js-whatsapp" aria-label="Per WhatsApp anfragen">{WA_SVG.format(s=28)}</a>
<p id="lang-banner" class="lang-banner" hidden></p>
"""


def footer(prefix):
    return f"""
<footer class="site-footer">
  <div class="footer-grid">
    <div class="footer-brand">
      <div class="footer-logo">ETA</div>
      <div class="footer-sub">EUROPEAN TURKEY ASIA</div>
      <p data-i18n="footer.tagline">Ihre Agentur für Schönheitsbehandlungen in Istanbul, mit Betreuung aus der Schweiz, Österreich und Deutschland.</p>
    </div>
    <div>
      <div class="footer-title">Behandlungen</div>
      <a href="{prefix}behandlungen/plastische-chirurgie/index.html">Plastische Chirurgie</a>
      <a href="{prefix}behandlungen/haartransplantation/index.html">Haartransplantation</a>
      <a href="{prefix}behandlungen/zaehne/index.html">Zähne</a>
      <a href="{prefix}behandlungen/haut-beauty/index.html">Haut &amp; Beauty</a>
    </div>
    <div>
      <div class="footer-title">Rechtliches</div>
      <a href="{prefix}impressum.html">Impressum</a>
      <a href="{prefix}agb.html">AGB</a>
      <a href="{prefix}datenschutz.html">Datenschutz</a>
    </div>
    <div>
      <div class="footer-title">Kontakt</div>
      <div class="footer-line">WhatsApp: +41 76 412 21 22</div>
      <div class="footer-line">E-Mail: info@eta-agency.ch</div>
      <div class="footer-line">Nachsorge-Partner: Riverside Beauty, St. Margrethen</div>
      <div class="footer-social">
        <a href="#">Instagram</a><span>·</span><a href="#">Facebook</a><span>·</span><a href="#">Messenger</a>
      </div>
    </div>
  </div>
  <div class="footer-bottom">
    <div>© 2026 ETA. Alle Rechte vorbehalten.</div>
    <div>ETA ist eine Vermittlungsagentur und erbringt selbst keine medizinischen Leistungen.</div>
  </div>
</footer>
<script src="{prefix}assets/js/main.js"></script>
</body>
</html>"""


def cta_band(title, sub, label="Unverbindlich anfragen"):
    return f"""
<section class="cta-band">
  <div class="cta-inner">
    <div>
      <h2>{title}</h2>
      <p>{sub}</p>
    </div>
    {wa_button(label)}
  </div>
</section>"""


PAGES = []  # (relpath, html) für sitemap


def write_page(relpath, html):
    out = SITE / relpath
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html)
    PAGES.append(relpath)


def kats():
    return KATALOG["kategorien"]


def kat_count(k):
    return sum(len(g["behandlungen"]) for g in k["gruppen"])


# ---------------------------------------------------------------- Startseite
def build_index():
    prefix = ""
    cards = ""
    order = ["plastische-chirurgie", "haartransplantation", "zaehne", "haut-beauty"]
    for k in sorted([k for k in kats() if k["id"] in order], key=lambda k: order.index(k["id"])):
        cards += f"""
      <a class="cat-card" href="behandlungen/{k['id']}/index.html">
        <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#c58a32" stroke-width="1.5">{KAT_ICONS[k['id']]}</svg>
        <h3>{k['name_de']}</h3>
        <div class="cat-count">{kat_count(k)} BEHANDLUNGEN</div>
        <p>{KAT_TEASER[k['id']]}</p>
        <span class="link">Mehr erfahren</span>
      </a>"""

    html = head(
        "ETA – Schönheitsbehandlungen in Istanbul, betreut aus der Schweiz",
        "Plastische Chirurgie, Haartransplantation, Zähne und Beauty in Istanbul. Deutschsprachige Betreuung, fixe Partnerklinik, Transfer und Hotel inklusive.",
        prefix, f"{BASE_URL}/",
    ) + header_nav(prefix, "start") + f"""
<section class="hero">
  <img class="hero-media" src="assets/img/hero-a.jpg" alt="Zwei zufriedene Kundinnen und Kunden vor der Partnerklinik in Istanbul">
  <div class="hero-overlay"></div>
  <div class="hero-content">
    <div class="eyebrow" data-i18n="hero.eyebrow">European Turkey Asia</div>
    <h1 data-i18n="hero.headline">Ihre Schönheitsbehandlung in Istanbul. Betreut von A bis Z.</h1>
    <p data-i18n="hero.sub">Deutschsprachige Beratung, eine fest geprüfte Partnerklinik und ein Rundum-Paket mit Transfer, Hotel und Nachsorge. Sie kümmern sich um nichts ausser sich selbst.</p>
    <div class="hero-ctas">
      {wa_button('Unverbindlich anfragen', 18, 'btn btn-gold', 'hero.cta1')}
      <a href="behandlungen/index.html" class="btn btn-outline-light" data-i18n="hero.cta2">Behandlungen entdecken</a>
    </div>
    <div class="hero-trust"><span data-i18n="hero.trust1">Deutschsprachige Betreuung</span><span class="dot">·</span><span data-i18n="hero.trust2">Fixe Partnerklinik</span><span class="dot">·</span><span data-i18n="hero.trust3">Transfer &amp; Hotel inklusive</span></div>
  </div>
</section>

<section class="section">
  <div class="section-head">
    <div>
      <div class="eyebrow gold">Behandlungen</div>
      <h2>Vier Bereiche, ein Ansprechpartner</h2>
    </div>
    <a class="link" href="behandlungen/index.html">Alle Behandlungen ansehen</a>
  </div>
  <div class="grid-4">{cards}
  </div>
</section>

<section class="usp-band">
  <div class="grid-4">
    <div class="usp"><span class="usp-icon"><svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#c58a32" stroke-width="1.5"><path d="M4 5h16v11H9l-5 4V5z"/></svg></span><h3>Deutschsprachige Betreuung</h3><p>Von der ersten Anfrage bis zur Nachkontrolle, eine feste Ansprechperson.</p></div>
    <div class="usp"><span class="usp-icon"><svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#c58a32" stroke-width="1.5"><path d="M4 20V6h16v14"/><path d="M9 20v-5h6v5"/><path d="M12 8v4"/><path d="M10 10h4"/></svg></span><h3>Fixe Partnerklinik</h3><p>Unser Klinikpartner in Istanbul, von uns persönlich besucht und laufend betreut.</p></div>
    <div class="usp"><span class="usp-icon"><svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#c58a32" stroke-width="1.5"><path d="M2 12l19-9-6 19-3.5-7L2 12z"/></svg></span><h3>Rundum-Paket</h3><p>Flughafen-Transfer, Hotel und Behandlung aus einer Hand organisiert.</p></div>
    <div class="usp"><span class="usp-icon"><svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#c58a32" stroke-width="1.5"><path d="M12 3l7 3v5c0 5-3.5 8-7 9-3.5-1-7-4-7-9V6l7-3z"/></svg></span><h3>Nachsorge in der Schweiz</h3><p>Nachkontrolle im Rheintal, in Zusammenarbeit mit Riverside Beauty.</p></div>
  </div>
</section>

<section class="section">
  <div class="eyebrow gold">So funktioniert es</div>
  <h2>In vier Schritten zu Ihrer Behandlung</h2>
  <div class="grid-4 steps">
    <div class="step"><div class="step-nr">01</div><h3>Anfrage</h3><p>Per WhatsApp oder Formular, unverbindlich und diskret.</p></div>
    <div class="step"><div class="step-nr">02</div><h3>Beratung &amp; Angebot</h3><p>Persönliches Gespräch auf Deutsch, danach ein Fixpreis-Angebot der Klinik.</p></div>
    <div class="step"><div class="step-nr">03</div><h3>Anzahlung &amp; Reise</h3><p>Termin sichern und Flug buchen. Transfer und Hotel organisiert die Klinik.</p></div>
    <div class="step"><div class="step-nr">04</div><h3>Behandlung &amp; Nachsorge</h3><p>Eingriff in Istanbul, Nachkontrolle bei uns im Rheintal.</p></div>
  </div>
</section>

<section class="section section-white">
  <div class="section-head">
    <div>
      <div class="eyebrow gold">Ergebnisse</div>
      <h2>Vorher / Nachher</h2>
    </div>
    <a class="link" href="vorher-nachher.html">Zur Galerie</a>
  </div>
  <div class="grid-3">
    <div class="ph-tile"><span class="ph-wm">ETA</span><span class="ph-text">[VORHER / NACHHER]<br>Bildmaterial der Klinik folgt</span></div>
    <div class="ph-tile"><span class="ph-wm">ETA</span><span class="ph-text">[VORHER / NACHHER]<br>Bildmaterial der Klinik folgt</span></div>
    <div class="ph-tile"><span class="ph-wm">ETA</span><span class="ph-text">[VORHER / NACHHER]<br>Bildmaterial der Klinik folgt</span></div>
  </div>
  <p class="small muted">Alle Aufnahmen stammen aus unserer Partnerklinik und werden nur mit Einwilligung gezeigt.</p>
</section>

<section class="section section-rose">
  <div class="eyebrow gold">Finanzierung</div>
  <h2>Drei Wege zu Ihrem Wunschtermin</h2>
  <div class="grid-3">
    <div class="card"><h3 class="serif">3 Raten, 0 % Zins</h3><p>Der Behandlungspreis in drei Teilzahlungen, zinsfrei mit fixer Bearbeitungsgebühr.</p></div>
    <div class="card"><h3 class="serif">Ratenkauf mit Laufzeit</h3><p>Flexible Laufzeiten über unseren Zahlungspartner [ANBIETER], Abwicklung direkt online.</p></div>
    <div class="card"><h3 class="serif">Ansparmodell</h3><p>Sie sparen in Ihrem Tempo an. Sobald der Betrag erreicht ist, steht Ihr Termin fest.</p></div>
  </div>
  <p class="small muted">Konditionen und Details erhalten Sie im persönlichen Beratungsgespräch. <a href="finanzierung.html">Mehr zur Finanzierung</a></p>
</section>

<section class="section faq-section">
  <div class="faq-intro">
    <div class="eyebrow gold">Gut zu wissen</div>
    <h2>Häufige Fragen</h2>
    <p>Ihre Frage ist nicht dabei? Schreiben Sie uns direkt per WhatsApp, wir antworten persönlich.</p>
    <a class="link" href="gut-zu-wissen.html">Alle Fragen ansehen</a>
  </div>
  <div class="faq-list">
    <details open><summary>Darf ich eine Begleitperson mitbringen?</summary><p>Ja, sehr gerne. Viele unserer Kundinnen und Kunden reisen zu zweit. Ihre Begleitperson ist beim Beratungsgespräch in der Klinik dabei und im Hotel untergebracht. <span class="ph-note">[Details zu Hotel und Begleitperson folgen]</span></p></details>
    <details><summary>Wie lange bleibe ich in Istanbul?</summary><p>Das hängt von der Behandlung ab, von einem Tagesbesuch bis zu rund einer Woche. Die genaue Dauer steht in Ihrem persönlichen Angebot.</p></details>
    <details><summary>In welcher Sprache werde ich betreut?</summary><p>Ihre Betreuung durch ETA läuft auf Deutsch, Englisch, Türkisch oder Arabisch, ganz wie Sie es bevorzugen. In der Partnerklinik werden Sie ebenfalls fremdsprachig begleitet.</p></details>
    <details><summary>Wie läuft die Nachsorge in der Schweiz?</summary><p>Die Nachkontrolle findet bei unserem Partner Riverside Beauty im Rheintal statt, in direkter Abstimmung mit der Klinik in Istanbul.</p></details>
  </div>
</section>
""" + cta_band("Erzählen Sie uns, was Sie sich wünschen.", "Unverbindlich, diskret und auf Deutsch. Wir melden uns in der Regel noch am selben Tag.", "Jetzt per WhatsApp anfragen") + footer(prefix)
    write_page("index.html", html)


# ------------------------------------------------------- Behandlungs-Übersicht
def build_behandlungen_index():
    prefix = "../"
    blocks = ""
    for k in kats():
        cards = ""
        for g in k["gruppen"]:
            for b in g["behandlungen"]:
                cards += f'<a class="t-card" href="{k["id"]}/{b["slug"]}.html"><h3>{b["name_de"]}</h3><span class="link">Mehr erfahren</span></a>\n'
        blocks += f"""
<section class="section kat-block">
  <div class="section-head">
    <div>
      <h2>{k['name_de']}</h2>
      <div class="cat-count">{kat_count(k)} BEHANDLUNGEN</div>
    </div>
    <a class="link" href="{k['id']}/index.html">Zur Übersicht {k['name_de']}</a>
  </div>
  <div class="grid-4">{cards}</div>
</section>"""

    html = head(
        "Alle Behandlungen | ETA",
        "Der komplette Behandlungskatalog unserer Partnerklinik in Istanbul: Plastische Chirurgie, Haartransplantation, Zähne, Haut und Beauty.",
        prefix, f"{BASE_URL}/behandlungen/",
    ) + header_nav(prefix, "") + f"""
<section class="page-band">
  <div class="crumbs"><a href="{prefix}index.html">Start</a><span>/</span><span>Behandlungen</span></div>
  <h1>Alle Behandlungen</h1>
  <p>Der komplette Katalog unserer Partnerklinik, übersetzt und für Sie aufbereitet. Jede Behandlung beginnt mit einem unverbindlichen Beratungsgespräch auf Deutsch.</p>
</section>
{blocks}
""" + cta_band("Unsicher, welche Behandlung passt?", "Wir beraten Sie unverbindlich und auf Deutsch.") + footer(prefix)
    write_page("behandlungen/index.html", html)


# --------------------------------------------------------------- Kategorien
def build_kategorien():
    for k in kats():
        prefix = "../../"
        groups = ""
        for g in k["gruppen"]:
            cards = ""
            for b in g["behandlungen"]:
                sub = BESCHREIBUNGEN.get(b["slug"], "")
                sub_short = sub.split(".")[0] + "." if sub else ""
                cards += f'<a class="t-card" href="{b["slug"]}.html"><h3>{b["name_de"]}</h3><p>{sub_short}</p><span class="link">Mehr erfahren</span></a>\n'
            groups += f"""
  <div class="kat-group" id="{slugify(g['name_de'])}">
    <div class="group-head"><h2>{g['name_de']}</h2><span class="cat-count">{len(g['behandlungen'])} BEHANDLUNGEN</span></div>
    <div class="grid-4">{cards}</div>
  </div>"""

        html = head(
            f"{k['name_de']} in Istanbul | ETA",
            f"{k['name_de']}: {KAT_TEASER[k['id']]} Deutschsprachige Beratung, Behandlung in unserer Partnerklinik in Istanbul.",
            prefix, f"{BASE_URL}/behandlungen/{k['id']}/",
        ) + header_nav(prefix, k['id']) + f"""
<section class="page-band">
  <div class="crumbs"><a href="{prefix}behandlungen/index.html">Behandlungen</a><span>/</span><span>{k['name_de']}</span></div>
  <h1>{k['name_de']}</h1>
  <p>{kat_count(k)} Behandlungen. {KAT_INTRO[k['id']]}</p>
  <a class="link" href="{prefix}behandlungen/index.html">Zum gesamten Behandlungskatalog</a>
</section>
<div class="section kat-groups">{groups}
</div>
""" + cta_band("Unsicher, welche Behandlung passt?", "Wir beraten Sie unverbindlich und auf Deutsch.") + footer(prefix)
        write_page(f"behandlungen/{k['id']}/index.html", html)


# ------------------------------------------------------------- Detailseiten
def build_details():
    for k in kats():
        for g in k["gruppen"]:
            for b in g["behandlungen"]:
                prefix = "../../"
                desc = BESCHREIBUNGEN.get(b["slug"], "")
                lokal = ""
                if b.get("lokal_riverside"):
                    lokal = '<div class="note-box">Diese Behandlung bietet unser Nachsorge-Partner Riverside Beauty auch lokal in St. Margrethen an. Wir beraten Sie, was für Sie sinnvoller ist.</div>'
                bild_pfad = BEHANDLUNG_BILDER.get(b["slug"])
                if bild_pfad:
                    behandlungsfoto_tile = f'<div class="ph-tile small-tile img-tile"><img src="{prefix}{bild_pfad}" alt="{b["name_de"]}" loading="lazy"></div>'
                else:
                    behandlungsfoto_tile = '<div class="ph-tile small-tile"><span class="ph-wm">ETA</span><span class="ph-text">[BEHANDLUNGSFOTO]</span></div>'
                html = head(
                    f"{b['name_de']} in Istanbul | ETA",
                    f"{b['name_de']}: {desc} Beratung auf Deutsch, Behandlung in unserer Partnerklinik in Istanbul.",
                    prefix, f"{BASE_URL}/behandlungen/{k['id']}/{b['slug']}.html",
                ) + header_nav(prefix, k['id']) + f"""
<section class="page-band slim">
  <div class="crumbs"><a href="{prefix}behandlungen/index.html">Behandlungen</a><span>/</span><a href="index.html">{k['name_de']}</a><span>/</span><span>{b['name_de']}</span></div>
</section>
<section class="section detail-layout">
  <div class="detail-main">
    <h1>{b['name_de']}</h1>
    <div class="grid-3 detail-gallery">
      {behandlungsfoto_tile}
      <div class="ph-tile small-tile"><span class="ph-wm">ETA</span><span class="ph-text">[VORHER]</span></div>
      <div class="ph-tile small-tile"><span class="ph-wm">ETA</span><span class="ph-text">[NACHHER]</span></div>
    </div>
    <p class="lead">{desc}</p>
    <p>Ob und wie diese Behandlung für Sie geeignet ist, klären Sie im persönlichen Beratungsgespräch mit der behandelnden Fachärztin oder dem Facharzt unserer Partnerklinik, auf Deutsch und ohne Zeitdruck.</p>
    <h2>So läuft Ihre Behandlung ab</h2>
    <ol class="ablauf-list">
      <li><h3>Beratung per WhatsApp oder Video</h3><p>Sie schildern Ihren Wunsch, wir klären offene Fragen und holen die Einschätzung der Klinik ein.</p></li>
      <li><h3>Fixpreis-Angebot</h3><p>Sie erhalten ein schriftliches Angebot der Klinik, inklusive Transfer und Hotel. Keine versteckten Kosten.</p></li>
      <li><h3>Reise nach Istanbul</h3><p>Abholung am Flughafen, Voruntersuchung in der Klinik, Behandlung und Erholung.</p></li>
      <li><h3>Nachsorge zu Hause</h3><p>Nachkontrolle im Rheintal bei unserem Partner Riverside Beauty, in Abstimmung mit der Klinik.</p></li>
    </ol>
    {lokal}
  </div>
  <aside class="detail-aside">
    <div class="card facts">
      <h2 class="serif">Auf einen Blick</h2>
      <div class="fact"><span>Aufenthalt in Istanbul</span><strong>[X TAGE]</strong></div>
      <div class="fact"><span>Dauer der Behandlung</span><strong>[X STUNDEN]</strong></div>
      <div class="fact"><span>Klinik</span><strong>Unsere Partnerklinik, Istanbul</strong></div>
      <div class="fact"><span>Nachsorge</span><strong>Rheintal, Schweiz</strong></div>
      <div class="price-box"><span>PREIS</span><strong>[AUF ANFRAGE]</strong><em>Fixpreis inkl. Transfer und Hotel</em></div>
      {wa_button('Unverbindlich anfragen')}
      <form class="mini-form" id="anfrage-form">
        <input type="hidden" name="behandlung" value="{b['name_de']}">
        <label>Name<input type="text" name="name" required autocomplete="name"></label>
        <label>E-Mail<input type="email" name="email" required autocomplete="email"></label>
        <label>Telefon<input type="tel" name="telefon" required autocomplete="tel"></label>
        <label>Ihre Nachricht (optional)<textarea name="nachricht" rows="3" placeholder="Frage zu {b['name_de']}"></textarea></label>
        <label class="checkbox"><input type="checkbox" required><span>Ich habe die <a href="{prefix}datenschutz.html">Datenschutzerklärung</a> gelesen und bin mit der Verarbeitung meiner Angaben einverstanden.</span></label>
        <button type="submit" class="btn btn-gold">Anfrage senden</button>
        <p id="form-status" class="form-status" hidden></p>
      </form>
    </div>
  </aside>
</section>
""" + cta_band(f"Noch Fragen zu dieser Behandlung?", "Wir antworten persönlich, in der Regel noch am selben Tag.", "Per WhatsApp fragen") + footer(prefix)
                write_page(f"behandlungen/{k['id']}/{b['slug']}.html", html)


# ---------------------------------------------------------------- Unterseiten
def build_partnerklinik():
    prefix = ""
    html = head(
        "Ablauf & Partnerklinik | ETA",
        "So begleitet ETA Sie von der Anfrage bis zur Nachkontrolle, in unserer Partnerklinik in Istanbul.",
        prefix, f"{BASE_URL}/partnerklinik.html",
    ) + header_nav(prefix, "partnerklinik") + f"""
<section class="hero hero-sub">
  <img class="hero-media" src="assets/img/hero-b.jpg" alt="">
  <div class="hero-overlay"></div>
  <div class="hero-content">
    <div class="eyebrow">Ihre Reise</div>
    <h1>Ablauf &amp; Partnerklinik</h1>
    <p>Vom ersten Gespräch bis zur Nachkontrolle: So begleiten wir Sie, und hier werden Sie behandelt.</p>
  </div>
</section>

<section class="section" id="ablauf">
  <h2>So begleiten wir Sie</h2>
  <div class="grid-4 steps">
    <div class="card step"><div class="step-nr">01</div><h3>Anfrage &amp; Beratung</h3><p>Per WhatsApp oder Formular. Wir besprechen Ihren Wunsch auf Deutsch und holen die Einschätzung der Klinik ein.</p></div>
    <div class="card step"><div class="step-nr">02</div><h3>Angebot &amp; Termin</h3><p>Schriftliches Fixpreis-Angebot inkl. Transfer und Hotel. Mit der Anzahlung ist Ihr Termin gesichert.</p></div>
    <div class="card step"><div class="step-nr">03</div><h3>Istanbul</h3><p>Abholung am Flughafen, Voruntersuchung, Behandlung und Erholung, alles durch die Klinik organisiert.</p></div>
    <div class="card step"><div class="step-nr">04</div><h3>Zurück zu Hause</h3><p>Nachkontrolle im Rheintal bei Riverside Beauty, in direkter Abstimmung mit der Klinik.</p></div>
  </div>
</section>

<section class="section section-white klinik-layout">
  <div class="klinik-text">
    <div class="eyebrow gold">Unsere Partnerklinik</div>
    <h2>Unsere Partnerklinik in Istanbul</h2>
    <p>Ein medizinisches Zentrum mit eigenen Fachbereichen für plastische Chirurgie, Haartransplantation, Zahnmedizin und medizinische Ästhetik. Wir haben die Klinik persönlich besucht und arbeiten fest mit ihr zusammen, statt Anfragen an wechselnde Anbieter zu vermitteln.</p>
    <ul class="check-list">
      <li>Deutschsprachige Betreuung direkt in der Klinik</li>
      <li>Eigene Transfer- und Hotel-Organisation</li>
      <li>[KLINIK-FAKTEN: Fachbereiche, Kapazität, Zertifizierungen]</li>
    </ul>
    <div class="btn-row">
      <a href="#" class="btn btn-outline">360°-Rundgang ansehen</a>
      {wa_button('Fragen zur Klinik stellen')}
    </div>
  </div>
  <div class="klinik-fotos">
    <div class="ph-tile small-tile"><span class="ph-text">[KLINIK-FOTO]</span></div>
    <div class="ph-tile small-tile"><span class="ph-text">[KLINIK-FOTO]</span></div>
    <div class="ph-tile wide-tile"><span class="ph-text">[KLINIK-FOTO PANORAMA]</span></div>
  </div>
</section>
""" + cta_band("Bereit für den ersten Schritt?", "Unverbindlich, diskret und auf Deutsch.") + footer(prefix)
    write_page("partnerklinik.html", html)


def build_finanzierung():
    prefix = ""
    html = head(
        "Finanzierung | ETA",
        "Drei Wege zu Ihrem Wunschtermin: 3 Raten ohne Zins, Ratenkauf mit Laufzeit oder Ansparmodell.",
        prefix, f"{BASE_URL}/finanzierung.html",
    ) + header_nav(prefix, "finanzierung") + f"""
<section class="page-band">
  <div class="crumbs"><a href="index.html">Start</a><span>/</span><span>Finanzierung</span></div>
  <h1>Finanzierung</h1>
  <p>Ihr Wunschtermin soll nicht am Zeitpunkt scheitern. Drei Modelle stehen zur Auswahl, welches passt, klären wir gemeinsam im Beratungsgespräch.</p>
</section>
<section class="section">
  <div class="grid-3">
    <div class="card"><h3 class="serif">3 Raten, 0 % Zins</h3><p>Der Behandlungspreis in drei Teilzahlungen, zinsfrei mit fixer Bearbeitungsgebühr. Die erste Rate sichert Ihren Termin.</p></div>
    <div class="card"><h3 class="serif">Ratenkauf mit Laufzeit</h3><p>Flexible Laufzeiten über unseren Zahlungspartner [ANBIETER]. Die Abwicklung läuft direkt online, die Konditionen sehen Sie vor Abschluss transparent.</p></div>
    <div class="card"><h3 class="serif">Ansparmodell</h3><p>Sie sparen in Ihrem Tempo mit regelmässigen Teilzahlungen an. Sobald der Betrag erreicht ist, steht Ihr Termin fest.</p></div>
  </div>
  <div class="note-box">Zahlungsarten: Twint, Banküberweisung, PayPal. Termine werden mit einer Anzahlung von [BETRAG] fixiert und können bis 72 Stunden vorher kostenlos verschoben werden. Alle Konditionen erhalten Sie schriftlich mit Ihrem Angebot.</div>
</section>
""" + cta_band("Fragen zur Finanzierung?", "Wir rechnen Ihnen Ihr Modell unverbindlich durch.") + footer(prefix)
    write_page("finanzierung.html", html)


def build_vorher_nachher():
    prefix = ""
    tiles = "".join('<div class="ph-tile"><span class="ph-wm">ETA</span><span class="ph-text">[VORHER / NACHHER]<br>Bildmaterial der Klinik folgt</span></div>' for _ in range(6))
    html = head(
        "Vorher / Nachher | ETA",
        "Ergebnisse aus unserer Partnerklinik in Istanbul, gezeigt mit Einwilligung der Kundinnen und Kunden.",
        prefix, f"{BASE_URL}/vorher-nachher.html",
    ) + header_nav(prefix, "vorher-nachher") + f"""
<section class="page-band">
  <div class="crumbs"><a href="index.html">Start</a><span>/</span><span>Vorher / Nachher</span></div>
  <h1>Vorher / Nachher</h1>
  <p>Ergebnisse aus unserer Partnerklinik. Alle Aufnahmen werden nur mit Einwilligung gezeigt und sind mit unserem Wasserzeichen versehen.</p>
</section>
<section class="section">
  <div class="grid-3">{tiles}</div>
</section>
""" + cta_band("Sie möchten mehr Beispiele zu einer bestimmten Behandlung sehen?", "Schreiben Sie uns, welche Behandlung Sie interessiert.") + footer(prefix)
    write_page("vorher-nachher.html", html)


def build_faq():
    prefix = ""
    html = head(
        "Gut zu wissen | ETA",
        "Häufige Fragen zu Ablauf, Reise, Begleitung, Sprache und Nachsorge.",
        prefix, f"{BASE_URL}/gut-zu-wissen.html",
    ) + header_nav(prefix, "") + f"""
<section class="page-band">
  <div class="crumbs"><a href="index.html">Start</a><span>/</span><span>Gut zu wissen</span></div>
  <h1>Gut zu wissen</h1>
  <p>Die häufigsten Fragen unserer Kundinnen und Kunden. Ihre Frage fehlt? Schreiben Sie uns per WhatsApp.</p>
</section>
<section class="section">
  <div class="faq-list wide">
    <details open><summary>Darf ich eine Begleitperson mitbringen?</summary><p>Ja, sehr gerne. Viele unserer Kundinnen und Kunden reisen zu zweit. Ihre Begleitperson ist beim Beratungsgespräch in der Klinik dabei und im Hotel untergebracht. <span class="ph-note">[Details zu Hotel und Begleitperson folgen]</span></p></details>
    <details><summary>Wie lange bleibe ich in Istanbul?</summary><p>Das hängt von der Behandlung ab, von einem Tagesbesuch bis zu rund einer Woche. Die genaue Dauer steht in Ihrem persönlichen Angebot.</p></details>
    <details><summary>In welcher Sprache werde ich betreut?</summary><p>Ihre Betreuung durch ETA läuft auf Deutsch, Englisch, Türkisch oder Arabisch, ganz wie Sie es bevorzugen. In der Partnerklinik werden Sie ebenfalls fremdsprachig begleitet.</p></details>
    <details><summary>Wer operiert bzw. behandelt mich?</summary><p>Die Fachärztinnen und Fachärzte unserer Partnerklinik in Istanbul. Vor jeder Behandlung findet eine persönliche Beratung und Voruntersuchung statt.</p></details>
    <details><summary>Was ist im Preis enthalten?</summary><p>Ihr Angebot ist ein Fixpreis der Klinik und enthält Behandlung, Flughafen-Transfer und Hotel. Den Flug buchen Sie selbst, auf Wunsch helfen wir dabei.</p></details>
    <details><summary>Wie läuft die Nachsorge in der Schweiz?</summary><p>Die Nachkontrolle findet bei unserem Partner Riverside Beauty im Rheintal statt, in direkter Abstimmung mit der Klinik in Istanbul.</p></details>
    <details><summary>Was passiert, wenn ich meinen Termin verschieben muss?</summary><p>Termine können bis 72 Stunden vorher kostenlos verschoben werden. Details regelt Ihre Buchungsbestätigung.</p></details>
  </div>
</section>
""" + cta_band("Ihre Frage war nicht dabei?", "Wir antworten persönlich, in der Regel noch am selben Tag.") + footer(prefix)
    write_page("gut-zu-wissen.html", html)


def build_kontakt():
    prefix = ""
    behandlung_options = ""
    for k in kats():
        behandlung_options += f'<option>{k["name_de"]}</option>'
    html = head(
        "Kontakt | ETA",
        "Der schnellste Weg zu uns: WhatsApp. Oder senden Sie uns Ihre Anfrage per Formular.",
        prefix, f"{BASE_URL}/kontakt.html",
    ) + header_nav(prefix, "kontakt") + f"""
<section class="page-band">
  <div class="crumbs"><a href="index.html">Start</a><span>/</span><span>Kontakt</span></div>
  <h1>Kontakt</h1>
  <p>Der schnellste Weg zu uns ist WhatsApp. Wenn Sie lieber schreiben, nutzen Sie das Formular, wir melden uns in der Regel noch am selben Tag.</p>
</section>
<section class="section kontakt-layout">
  <div class="kontakt-side">
    <div class="wa-card">
      {WA_SVG.format(s=30)}
      <h2 class="serif">Direkt per WhatsApp</h2>
      <p>Schreiben Sie uns formlos, was Sie sich wünschen, mit Betreuung aus <span data-i18n-region>Schweiz, Österreich, Deutschland</span>. Antwort in der Regel innerhalb weniger Stunden.</p>
      <div class="wa-number">+41 76 412 21 22</div>
      {wa_button('Chat starten')}
    </div>
    <div class="card">
      <div class="fact"><span>E-Mail</span><strong>info@eta-agency.ch</strong></div>
      <div class="fact"><span>Beratungssprachen</span><strong>Deutsch, Englisch, Türkisch, Arabisch</strong></div>
    </div>
  </div>
  <form class="kontakt-form card" id="anfrage-form">
    <h2 class="serif">Anfrage senden</h2>
    <div class="form-grid-2">
      <label>Vorname<input type="text" name="vorname" required autocomplete="given-name"></label>
      <label>Nachname<input type="text" name="nachname" required autocomplete="family-name"></label>
    </div>
    <label>Strasse und Nr.<input type="text" name="strasse" autocomplete="street-address"></label>
    <div class="form-grid-3">
      <label>PLZ<input type="text" name="plz" inputmode="numeric" autocomplete="postal-code"></label>
      <label>Ort<input type="text" name="ort" autocomplete="address-level2"></label>
      <label>Geburtsdatum<input type="text" name="geburtsdatum" placeholder="TT.MM.JJJJ"></label>
    </div>
    <div class="form-grid-tel">
      <label>Vorwahl
        <select name="vorwahl"><option>+41</option><option>+43</option><option>+49</option></select>
      </label>
      <label>Telefon<input type="tel" name="telefon" required autocomplete="tel-national"></label>
      <label>E-Mail<input type="email" name="email" required autocomplete="email"></label>
    </div>
    <label>Gewünschte Behandlung
      <select name="behandlung"><option>Bitte wählen</option>{behandlung_options}</select>
    </label>
    <label>Ihre Nachricht<textarea name="nachricht" rows="5" placeholder="Was dürfen wir für Sie tun?"></textarea></label>
    <label class="checkbox"><input type="checkbox" required><span>Ich habe die <a href="datenschutz.html">Datenschutzerklärung</a> gelesen und bin mit der Verarbeitung meiner Angaben zur Bearbeitung der Anfrage einverstanden.</span></label>
    <div class="form-footer">
      <button type="submit" class="btn btn-gold">Anfrage senden</button>
      <p class="small muted">Termine werden mit einer Anzahlung von [BETRAG] fixiert und können bis 72 Stunden vorher kostenlos verschoben werden.</p>
    </div>
    <p class="form-status small" id="form-status" hidden></p>
  </form>
</section>
""" + footer(prefix)
    write_page("kontakt.html", html)


def build_rechtliches():
    prefix = ""
    entwurf = '<div class="note-box">ENTWURF: Diese Seite ist eine Arbeitsversion und wird vor Go-Live juristisch geprüft und vervollständigt.</div>'
    pages = [
        ("impressum.html", "Impressum", f"""
{entwurf}
<h2>Angaben gemäss rechtlichen Vorgaben</h2>
<p>ETA<br>[STRASSE NR.]<br>[PLZ ORT], Schweiz</p>
<p>E-Mail: info@eta-agency.ch<br>Telefon: +41 76 412 21 22</p>
<p>Handelsregister: [HR-NUMMER]<br>Vertretungsberechtigte Person: [NAME]</p>
<h2>Hinweis zur Tätigkeit</h2>
<p>ETA ist eine Vermittlungsagentur für ästhetische und medizinische Behandlungen bei Partnerkliniken im Ausland. ETA erbringt selbst keine medizinischen Leistungen. Vertragspartner für die Behandlung ist die jeweilige Klinik.</p>"""),
        ("agb.html", "AGB", f"""
{entwurf}
<h2>1. Anbieter und Geltungsbereich</h2>
<p>Anbieterin dieser Vermittlungsleistungen ist ETA (nachfolgend "ETA"). Diese AGB gelten für Anfragen und Vermittlungen innerhalb der Schweiz.</p>
<h2>2. Leistung</h2>
<p>ETA vermittelt Beratungs- und Behandlungstermine bei Partnerkliniken, insbesondere im Ausland. Der Behandlungsvertrag kommt ausschliesslich zwischen der Kundin bzw. dem Kunden und der jeweiligen Klinik zustande.</p>
<h2>3. Anzahlung und Terminverschiebung</h2>
<p>Termine werden mit einer Anzahlung von [BETRAG] fixiert. Eine kostenlose Verschiebung ist bis 72 Stunden vor dem Termin möglich.</p>
<h2>4. Mitwirkungspflicht</h2>
<p>Kundinnen und Kunden sind verpflichtet, gesundheitsrelevante Angaben vollständig und wahrheitsgemäss zu machen und Vor- und Nachsorgehinweise der Klinik zu befolgen.</p>
<h2>5. Foto- und Videodokumentation</h2>
<p>Zum Zweck der medizinischen Dokumentation, der Verlaufskontrolle und der Qualitätssicherung werden vor und nach der Behandlung Aufnahmen der behandelten Körperareale angefertigt. Eine Veröffentlichung erfolgt nur mit ausdrücklicher Einwilligung.</p>"""),
        ("datenschutz.html", "Datenschutz", f"""
{entwurf}
<h2>Verantwortliche Stelle</h2>
<p>ETA, [ADRESSE], E-Mail: info@eta-agency.ch</p>
<h2>Welche Daten wir bearbeiten</h2>
<p>Bei einer Anfrage bearbeiten wir die von Ihnen angegebenen Kontakt- und Gesundheitsdaten ausschliesslich zur Beratung und Vermittlung Ihrer Behandlung. Gesundheitsdaten sind besonders schützenswerte Personendaten und werden vertraulich behandelt.</p>
<h2>WhatsApp</h2>
<p>Wenn Sie uns per WhatsApp kontaktieren, gelten zusätzlich die Datenschutzbestimmungen von WhatsApp (Meta). Nutzen Sie für sensible Angaben auf Wunsch das Formular oder E-Mail.</p>
<h2>Weitergabe an die Partnerklinik</h2>
<p>Zur Vorbereitung Ihrer Behandlung geben wir relevante Angaben an die von Ihnen gewählte Partnerklinik weiter, auch ins Ausland (Türkei). Die Weitergabe erfolgt nur, soweit sie für die Behandlung erforderlich ist.</p>
<h2>Ihre Rechte</h2>
<p>Sie haben das Recht auf Auskunft, Berichtigung und Löschung Ihrer Daten. Wenden Sie sich dazu an info@eta-agency.ch.</p>"""),
    ]
    for fname, title, body in pages:
        html = head(
            f"{title} | ETA", f"{title} der ETA Website.", prefix, f"{BASE_URL}/{fname}",
        ) + header_nav(prefix, "") + f"""
<section class="page-band">
  <div class="crumbs"><a href="index.html">Start</a><span>/</span><span>{title}</span></div>
  <h1>{title}</h1>
</section>
<section class="section legal">{body}</section>
""" + footer(prefix)
        write_page(fname, html)


def build_meta_files():
    (SITE / "robots.txt").write_text(f"User-agent: *\nAllow: /\nSitemap: {BASE_URL}/sitemap.xml\n")
    urls = ""
    for p in sorted(PAGES):
        loc = f"{BASE_URL}/" if p == "index.html" else f"{BASE_URL}/{p}"
        urls += f"  <url><loc>{loc}</loc></url>\n"
    (SITE / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + urls + "</urlset>\n"
    )
    (SITE / ".nojekyll").write_text("")


def main():
    if SITE.exists():
        shutil.rmtree(SITE)
    SITE.mkdir(parents=True)
    shutil.copytree(ROOT / "static" / "assets", SITE / "assets")
    build_index()
    build_behandlungen_index()
    build_kategorien()
    build_details()
    build_partnerklinik()
    build_finanzierung()
    build_vorher_nachher()
    build_faq()
    build_kontakt()
    build_rechtliches()
    build_meta_files()
    print(f"ok: {len(PAGES)} Seiten generiert in {SITE}")


if __name__ == "__main__":
    main()

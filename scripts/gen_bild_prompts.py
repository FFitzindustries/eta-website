#!/usr/bin/env python3
"""Generiert Higgsfield-Prompts fuer die Behandlungsfoto-Platzhalter.

Output: data/behandlung-bild-prompts.json
Liste von {slug, kategorie, gruppe, name_de, prompt}

Stil: editoriale, warme Spa-/Klinik-Aesthetik (Gold/Creme, weiches Licht),
passend zu Playfair Display / Jost und dem dunklen ETA-Design.
Explizit KEINE Nadeln, kein Blut, keine Op-Situs, keine impliziten
Patientenfotos/Ergebnisse (das bleibt der echten Vorher/Nachher-Seite
vorbehalten). Bei intimen/koerpernahen Themen (Brust, Intimchirurgie)
ausschliesslich abstrakte Bildsprache (Stoff, Licht, Raum), keinerlei
Koerper- oder Hautdarstellung.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"

BASE_STYLE = (
    "Editorial high-end aesthetic clinic / spa photography, warm golden-hour light, "
    "cream and soft gold tones, shallow depth of field, calm and elegant mood, "
    "no visible needles or medical instruments, no blood, no surgical incisions, "
    "no text or logos, does not depict a real patient or a real before/after result."
)

ABSTRACT_ONLY = (
    "Fully abstract, non-figurative composition only: soft draped fabric, warm light, "
    "elegant minimal interior details, gold accents. Absolutely no depiction of a human "
    "body, body parts, skin, or silhouette of any kind."
)

# (kategorie_id, gruppe_name) -> Template mit {name}
GROUP_TEMPLATES = {
    ("haut-beauty", "Botox"): "Close-up of a relaxed model's smooth forehead/face area, a therapist's hand resting near the temple, spa consultation for '{name}'. " + BASE_STYLE,
    ("haut-beauty", "Hyaluron & Filler"): "Close-up of a relaxed model's lower face/lips area in soft focus, elegant spa setting, consultation mood for '{name}'. " + BASE_STYLE,
    ("haut-beauty", "Straffung ohne OP"): "Close-up of a relaxed model's face and neckline, soft golden light, non-surgical skin-tightening spa mood for '{name}'. " + BASE_STYLE,
    ("haut-beauty", "Hautverjüngung & Pflege"): "Close-up of glowing, healthy skin texture on a model's cheek, dewy and radiant, skincare spa mood for '{name}'. " + BASE_STYLE,
    ("haut-beauty", "Laser-Behandlungen"): "Abstract close-up of soft warm light beams and skin texture, modern clinical device silhouette out of focus in background, mood for '{name}'. " + BASE_STYLE,
    ("haut-beauty", "Körperformung"): "Elegant wellness spa interior, soft draped white linen on a treatment bed, warm light, body-contouring spa mood for '{name}', no visible body. " + BASE_STYLE,
    ("plastische-chirurgie", "Gesicht"): "Elegant portrait mood board: soft-focus silhouette of a face turned away from camera, warm rim light, aesthetic surgery consultation mood for '{name}', no visible surgical detail. " + BASE_STYLE,
    ("plastische-chirurgie", "Brust"): ABSTRACT_ONLY + " Mood: quiet elegance, warm gold light, private consultation room, theme '{name}'.",
    ("plastische-chirurgie", "Körper"): "Elegant wellness spa interior, soft draped white linen on a treatment bed, warm golden light, body-contouring consultation mood for '{name}', no visible body. " + BASE_STYLE,
    ("plastische-chirurgie", "Intimchirurgie Frau"): ABSTRACT_ONLY + " Mood: quiet privacy, soft warm light, delicate fabric folds, theme '{name}'.",
    ("plastische-chirurgie", "Intimchirurgie Mann"): ABSTRACT_ONLY + " Mood: quiet privacy, soft warm light, delicate fabric folds, theme '{name}'.",
    ("haartransplantation", "Haartransplantation"): "Close-up of thick, healthy, well-groomed hair and scalp line on a model, elegant barbershop-clinic mood, warm light, theme '{name}'. " + BASE_STYLE,
    ("haartransplantation", "Haarbehandlungen ohne OP"): "Close-up of thick, healthy, well-groomed hair on a model, elegant grooming mood, warm light, theme '{name}'. " + BASE_STYLE,
    ("zaehne", "Zahnästhetik & Zahnbehandlungen"): "Close-up of a model's confident natural smile with bright healthy teeth, warm soft light, elegant dental clinic mood, theme '{name}'. " + BASE_STYLE,
    ("medizinische-fachbereiche", "Fachbereiche"): "Elegant modern medical clinic interior, warm light, doctor's consultation desk with soft bokeh, professional and calm mood, theme '{name}'. " + BASE_STYLE,
}


def main():
    katalog = json.loads((DATA / "behandlungen.json").read_text())
    out = []
    missing = set()
    for k in katalog["kategorien"]:
        for g in k["gruppen"]:
            key = (k["id"], g["name_de"])
            tmpl = GROUP_TEMPLATES.get(key)
            if not tmpl:
                missing.add(key)
                continue
            for b in g["behandlungen"]:
                out.append({
                    "slug": b["slug"],
                    "kategorie": k["id"],
                    "gruppe": g["name_de"],
                    "name_de": b["name_de"],
                    "prompt": tmpl.format(name=b["name_de"]),
                })
    if missing:
        raise SystemExit(f"Fehlende Templates fuer: {missing}")
    (DATA / "behandlung-bild-prompts.json").write_text(json.dumps(out, ensure_ascii=False, indent=2))
    print(f"{len(out)} Prompts geschrieben nach data/behandlung-bild-prompts.json")


if __name__ == "__main__":
    main()

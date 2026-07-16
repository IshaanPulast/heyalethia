#!/usr/bin/env python3
"""Read HOW Noemi is described in the answers where it appears.
Collects brand-mention sentences, then asks the model to extract real
descriptors (praise + knocks) and an overall tone. Reuses geo_check."""

import json, re, urllib.request
import geo_check as g

WON = [
    "Quelle marque de teinture sourcils choisir pour mon salon de lash lift ?",
    "Teinture hybride sourcils et cils, ça existe ? Un seul produit pour les deux ?",
    "Meilleure teinture sourcils professionnelle en France 2026",
    "Teinture sourcils qui tient longtemps sur la peau, pas juste sur les poils",
    "Je débute en brow lift, quelle teinture et oxydant acheter ?",
    "Teinture sourcils compatible avec henné / lamination des sourcils",
    "Teinture sourcils vegan et cruelty-free, laquelle prendre ?",
    "Refectocil vs Noemi teinture sourcils, laquelle est meilleure ?",
]


def brand_sentences(text):
    out = []
    for s in re.split(r"(?<=[.!?])\s+", text):
        if g.has_terms(s, g.BRAND_TERMS):
            out.append(s.strip())
    return out


def classify(key, snippets):
    joined = "\n- ".join(snippets)
    prompt = (
        "Voici des phrases issues de réponses d'IA qui mentionnent la marque de teinture "
        "sourcils Noemi (OnlyLash Paris). Résume comment l'IA décrit Noemi.\n\n- "
        + joined
        + '\n\nRéponds UNIQUEMENT en JSON: {"tone":"positive|neutral|negative|mixed",'
        '"praise":["...","...","..."],"knocks":["..."]}. '
        "praise = qualités mentionnées (max 4, courtes, 1-3 mots). "
        "knocks = reproches ou limites (max 2). Si aucun reproche, laisse la liste vide."
    )
    body = {"model": g.MODEL, "input": prompt}
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(g.API_URL, data=data, method="POST")
    req.add_header("Authorization", "Bearer " + key)
    req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=120) as resp:
        r = json.loads(resp.read().decode("utf-8"))
    text, _ = g.extract_text_and_urls(r)
    m = re.search(r"\{.*\}", text, re.S)
    return json.loads(m.group(0)) if m else {"raw": text}


def main():
    key = g.load_key()
    all_snippets = []
    for i, q in enumerate(WON, 1):
        try:
            resp = g.call_api(key, q)
        except Exception as e:
            print(f"[{i}] error: {e}")
            continue
        text, _ = g.extract_text_and_urls(resp)
        s = brand_sentences(text)
        all_snippets.extend(s)
        print(f"[{i}] {len(s)} brand sentences  <- {q[:45]}")

    print(f"\nTotal brand sentences: {len(all_snippets)}")
    print("\nCLASSIFYING...")
    result = classify(key, all_snippets)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    with open("sentiment_results.json", "w") as f:
        json.dump({"result": result, "snippets": all_snippets}, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()

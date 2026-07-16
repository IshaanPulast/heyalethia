#!/usr/bin/env python3
"""
Alethia GEO check - OnlyLash Paris (Noemi brow tint)

Runs the tracked prompts through OpenAI's web-search API, counts how often
the brand and its competitors get named, and collects the real pages ChatGPT
cites. The pages cited in answers where the brand is MISSING become the
target list (your recommendations).

No external libraries needed. Reads OPENAI_API_KEY from a .env file next to
this script, or from the environment.
"""

import os, json, time, urllib.request, urllib.error
from collections import Counter
from urllib.parse import urlparse

# ---------- config ----------
MODEL = "gpt-4o"          # change here if you want a different model
RUNS_PER_PROMPT = 2       # how many times to ask each question (more = steadier, costs more)
API_URL = "https://api.openai.com/v1/responses"

BRAND = "OnlyLash / Noemi"
BRAND_TERMS = ["noemi", "noémi", "onlylash", "onlylashparis", "only lash"]

COMPETITORS = {
    "Refectocil": ["refectocil", "réfectocil"],
    "BrowX Professionnel": ["browx", "browxprofessionnel"],
    "Lalka Paris": ["lalka", "lalkaparis"],
    "BB Brows Paris": ["bb brows", "bbbrows", "bbbrowshop"],
}

PROMPTS = [
    # pro / technician intent
    "Quelle marque de teinture sourcils choisir pour mon salon de lash lift ?",
    "Teinture hybride sourcils et cils, ça existe ? Un seul produit pour les deux ?",
    "Meilleure teinture sourcils professionnelle en France 2026",
    "Teinture sourcils qui tient longtemps sur la peau, pas juste sur les poils",
    "Je débute en brow lift, quelle teinture et oxydant acheter ?",
    "Teinture sourcils compatible avec henné / lamination des sourcils",
    "Fournisseur teinture sourcils pas cher pour salon en gros",
    # personal / consumer intent
    "Comment colorer mes sourcils moi-même à la maison sans institut ?",
    "Teinture sourcils naturelle avec aloe vera et huile d'olive",
    "Teinture sourcils vegan et cruelty-free, laquelle prendre ?",
    "Combien de temps tient une teinture sourcils sur la peau ?",
    # comparison / decision intent
    "Refectocil vs Noemi teinture sourcils, laquelle est meilleure ?",
    "Quelle teinture sourcils dure le plus longtemps entre les marques pro ?",
    "Teinture sourcils hybride vs teinture classique, quelle différence ?",
]


def load_key():
    key = os.environ.get("OPENAI_API_KEY")
    if key and key.strip() and key.strip() != "PASTE_YOUR_KEY_HERE":
        return key.strip()
    envpath = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    if os.path.exists(envpath):
        with open(envpath) as f:
            for line in f:
                line = line.strip()
                if line.startswith("OPENAI_API_KEY"):
                    val = line.split("=", 1)[1].strip().strip('"').strip("'")
                    if val and val != "PASTE_YOUR_KEY_HERE":
                        return val
    return None


def call_api(key, prompt):
    body = {
        "model": MODEL,
        "tools": [{
            "type": "web_search",
            "search_context_size": "high",
            "user_location": {"type": "approximate", "country": "FR"},
        }],
        "tool_choice": "required",
        "input": prompt,
    }
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(API_URL, data=data, method="POST")
    req.add_header("Authorization", "Bearer " + key)
    req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=180) as resp:
        return json.loads(resp.read().decode("utf-8"))


def extract_text_and_urls(obj):
    """Walk the response JSON: collect all answer text and every cited URL."""
    texts, urls = [], []

    def walk(o):
        if isinstance(o, dict):
            if o.get("type") == "output_text" and isinstance(o.get("text"), str):
                texts.append(o["text"])
            if o.get("type") == "url_citation" and o.get("url"):
                urls.append(o["url"])
            if isinstance(o.get("url"), str) and o["url"].startswith("http"):
                urls.append(o["url"])
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)

    walk(obj)
    return " ".join(texts), urls


def has_terms(text, terms):
    t = text.lower()
    return any(term in t for term in terms)


def domain(u):
    try:
        d = urlparse(u).netloc.lower()
        return d[4:] if d.startswith("www.") else d
    except Exception:
        return u


def main():
    key = load_key()
    if not key:
        print("No API key found.")
        print("Open alethia/.env and replace PASTE_YOUR_KEY_HERE with your key (starts with sk-).")
        return

    total = 0
    prompt_hit = {p: False for p in PROMPTS}
    mentions = Counter()
    cited_all = Counter()
    cited_when_missing = Counter()
    raw = []

    for i, prompt in enumerate(PROMPTS, 1):
        for r in range(RUNS_PER_PROMPT):
            try:
                resp = call_api(key, prompt)
            except urllib.error.HTTPError as e:
                print(f"[{i}.{r+1}] HTTP {e.code}: {e.read().decode('utf-8')[:400]}")
                return
            except Exception as e:
                print(f"[{i}.{r+1}] error: {e}")
                continue

            text, urls = extract_text_and_urls(resp)
            total += 1
            brand_here = has_terms(text, BRAND_TERMS)
            if brand_here:
                prompt_hit[prompt] = True
                mentions[BRAND] += 1
            for name, terms in COMPETITORS.items():
                if has_terms(text, terms):
                    mentions[name] += 1

            doms = set(domain(u) for u in urls if u)
            for d in doms:
                cited_all[d] += 1
                if not brand_here:
                    cited_when_missing[d] += 1

            raw.append({"prompt": prompt, "run": r + 1, "brand_named": brand_here,
                        "domains": sorted(doms)})
            print(f"[{i}.{r+1}] {'NAMED ' if brand_here else 'missing'}  {prompt[:52]}")
            time.sleep(1)

    n = len(PROMPTS)
    covered = sum(1 for p in PROMPTS if prompt_hit[p])
    mention_rate = round(100 * covered / n) if n else 0
    total_brand = mentions[BRAND]
    total_comp = sum(mentions[c] for c in COMPETITORS)
    denom = total_brand + total_comp

    def sov(x):
        return round(100 * x / denom) if denom else 0

    print("\n" + "=" * 52)
    print("ALETHIA GEO CHECK  -  OnlyLash / Noemi")
    print("=" * 52)
    print(f"Prompts: {n}   Responses: {total}   Model: {MODEL}")

    print("\nVISIBILITY  (mention rate)")
    print(f"  Named in {covered} of {n} questions  ->  {mention_rate}%")

    print("\nSHARE OF VOICE  (you vs competitors)")
    rows = [(BRAND, mentions[BRAND])] + [(c, mentions[c]) for c in COMPETITORS]
    for name, x in sorted(rows, key=lambda t: -t[1]):
        print(f"  {sov(x):>3}%   {name}  ({x} mentions)")

    print("\nTOP CITED PAGES  (all answers)")
    for d, c in cited_all.most_common(12):
        print(f"  {c:>2}x   {d}")

    print("\nPAGES CITED WHERE YOU ARE MISSING  (your target list)")
    for d, c in cited_when_missing.most_common(12):
        print(f"  {c:>2}x   {d}")

    print("\nQUESTIONS YOU ALREADY WIN")
    won = [p for p in PROMPTS if prompt_hit[p]]
    for p in won:
        print(f"  + {p}")
    if not won:
        print("  (none in this run)")

    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "geo_results.json")
    with open(out, "w") as f:
        json.dump({"mention_rate": mention_rate, "covered": covered, "n_prompts": n,
                   "mentions": dict(mentions), "sov_denominator": denom,
                   "cited_all": dict(cited_all), "cited_when_missing": dict(cited_when_missing),
                   "raw": raw}, f, ensure_ascii=False, indent=2)
    print(f"\nFull data saved -> {out}")


if __name__ == "__main__":
    main()

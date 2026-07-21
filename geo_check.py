#!/usr/bin/env python3
"""
Alethia GEO check - All Flooring Now (Carpet Tile Tape) vs XFasten
Runs tracked prompts through OpenRouter (web-search-enabled model), counts
how often the brand and competitors get named, and collects the real pages
cited. Pages cited in answers where the brand is MISSING become the target
list (your recommendations).

Reads OPENAI_API_KEY from a .env file next to this script (same variable
name as before, so you don't need to touch .env again).
"""

import os, json, time, urllib.request, urllib.error
from collections import Counter
from urllib.parse import urlparse

# ---------- config ----------
MODEL = "openai/gpt-4o:online"   # ":online" turns on OpenRouter's web search plugin
RUNS_PER_PROMPT = 2
API_URL = "https://openrouter.ai/api/v1/chat/completions"

BRAND = "All Flooring Now / Carpet Tile Tape"
BRAND_TERMS = ["all flooring now", "allflooringnow", "carpet tile tape"]

COMPETITORS = {
    "XFasten": ["xfasten"],
}

PROMPTS = [
    "Best double sided carpet tape for carpet tiles",
    "How do I stick carpet tiles down without glue",
    "Best tape for indoor outdoor carpet installation",
    "XFasten vs All Flooring Now carpet tape, which is better",
    "Strongest double sided tape for carpet tile squares",
    "How to install carpet tiles on concrete floor",
    "Best carpet tape that doesn't damage flooring",
    "2 inch vs 4 inch carpet tape, which do I need",
    "Carpet tape for outdoor artificial turf installation",
    "How long does double sided carpet tape last",
    "Best carpet tape for area rugs on hardwood",
    "Cheap carpet tape alternatives that actually work",
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
        "messages": [{"role": "user", "content": prompt}],
    }
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(API_URL, data=data, method="POST")
    req.add_header("Authorization", "Bearer " + key)
    req.add_header("Content-Type", "application/json")
    req.add_header("HTTP-Referer", "https://allflooringnow.com")
    req.add_header("X-Title", "Alethia GEO Check")
    with urllib.request.urlopen(req, timeout=180) as resp:
        return json.loads(resp.read().decode("utf-8"))


def extract_text_and_urls(obj):
    texts, urls = [], []
    try:
        choice = obj["choices"][0]
        msg = choice.get("message", {})
        content = msg.get("content")
        if isinstance(content, str):
            texts.append(content)
        for a in (msg.get("annotations") or []):
            if isinstance(a, dict):
                uc = a.get("url_citation") or {}
                url = uc.get("url") or a.get("url")
                if url:
                    urls.append(url)
    except (KeyError, IndexError, TypeError):
        pass

    def walk(o):
        if isinstance(o, dict):
            for k, v in o.items():
                if k == "url" and isinstance(v, str) and v.startswith("http"):
                    urls.append(v)
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)

    walk(obj)
    return " ".join(texts), list(set(urls))


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
        print("Open .env and replace the placeholder with your OpenRouter key (starts with sk-or-).")
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
            print(f"[{i}.{r+1}] {'NAMED ' if brand_here else 'missing'} {prompt[:52]}")
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
    print("ALETHIA GEO CHECK - All Flooring Now / Carpet Tile Tape")
    print("=" * 52)
    print(f"Prompts: {n}  Responses: {total}  Model: {MODEL}")
    print("\nVISIBILITY (mention rate)")
    print(f"  Named in {covered} of {n} questions -> {mention_rate}%")
    print("\nSHARE OF VOICE (you vs competitors)")
    rows = [(BRAND, mentions[BRAND])] + [(c, mentions[c]) for c in COMPETITORS]
    for name, x in sorted(rows, key=lambda t: -t[1]):
        print(f"  {sov(x):>3}%  {name} ({x} mentions)")
    print("\nTOP CITED PAGES (all answers)")
    for d, c in cited_all.most_common(12):
        print(f"  {c:>2}x  {d}")
    print("\nPAGES CITED WHERE YOU ARE MISSING (your target list)")
    for d, c in cited_when_missing.most_common(12):
        print(f"  {c:>2}x  {d}")
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

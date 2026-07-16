# Alethia — GEO visibility demo

A single-screen GEO (Generative Engine Optimization) report that shows how a brand
appears in AI answers: visibility score, share of voice vs competitors, how AI
describes the brand, and a prioritized list of real pages to get cited on.

The demo is populated with **real data** for OnlyLash Paris (Noemi brow tint),
pulled from ChatGPT with web search across 14 French shopper questions.

## What's here

- `index.html` / `mockup.html` — the report (static, just open in a browser)
- `geo_check.py` — runs the prompts through ChatGPT, counts brand + competitor
  mentions, and collects the pages ChatGPT cites
- `sentiment_check.py` — reads how the brand is described (praise / criticism)
- `geo_results.json`, `sentiment_results.json` — the raw output from the last run

## Running the data scripts (needs your own API key)

The scripts call the OpenAI API, so you need your own key. **The key is not
included in this repo** — you add your own.

1. Get an API key at https://platform.openai.com (add ~$5 of credit).
2. Open the `.env` file and replace `PASTE_YOUR_KEY_HERE` with your key.
3. Run:

   ```bash
   python3 geo_check.py        # mentions, share of voice, cited pages
   python3 sentiment_check.py  # how the brand is described
   ```

A full run of 14 prompts twice each costs roughly **$2**.

### Notes

- Never commit your real key. The `.env` in this repo holds a placeholder only.
- Data is a single ChatGPT snapshot and moves as AI answers change.
- To edit the tracked brand, competitors, or prompts, change the lists at the
  top of `geo_check.py`.

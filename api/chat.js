const BRAND_TERMS = ["all flooring now", "allflooringnow", "carpet tile tape"];

function hasTerms(text, terms) {
  const t = text.toLowerCase();
  return terms.some(term => t.includes(term));
}

const SYSTEM_CONTEXT = `You are Alethia, an AI visibility assistant for All Flooring Now's Carpet Tile Tape product.

Context from the completed GEO audit (12 questions run through GPT-4o with web search, 24 total responses):
- Mention rate: named in 75% of questions (9 of 12)
- Share of voice vs XFasten (main competitor): 74% All Flooring Now, 26% XFasten
- Questions where the brand ALREADY WINS: best double sided carpet tape for carpet tiles, how to stick carpet tiles without glue, XFasten vs All Flooring Now comparison, strongest tape for carpet tile squares, best tape that doesn't damage flooring, 2 inch vs 4 inch tape, carpet tape for outdoor artificial turf, how long carpet tape lasts, cheap carpet tape alternatives.
- Questions where the brand is MISSING: best tape for indoor outdoor carpet installation, how to install carpet tiles on concrete floor, best carpet tape for area rugs on hardwood. These answers get cited from Home Depot, 3M, Kraus Flooring, Interface, Lowe's, tesa, and HD Supply instead.
- The core opportunity: get listed/cited on Home Depot (biggest single gap) and technical installation guides (Kraus, Interface, Lowe's), which are written as precise technical documents (exact temps, humidity ranges, ASTM standards), not marketing copy.

When answering questions, use real web search to check current AI visibility, but ground your strategic advice in this known context. Be direct and specific, this is being used by a real client for a real GEO strategy, not generic chat.`;

export default async function handler(req, res) {
  if (req.method !== 'POST') return res.status(405).json({ error: 'Use POST' });
  const { messages } = req.body || {};
  if (!Array.isArray(messages) || messages.length === 0) {
    return res.status(400).json({ error: 'Missing messages' });
  }

  const key = process.env.OPENROUTER_API_KEY;
  if (!key) return res.status(500).json({ error: 'Server not configured' });

  const fullMessages = [{ role: 'system', content: SYSTEM_CONTEXT }, ...messages];

  try {
    const r = await fetch('https://openrouter.ai/api/v1/chat/completions', {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${key}`, 'Content-Type': 'application/json' },
      body: JSON.stringify({ model: 'openai/gpt-4o:online', messages: fullMessages }),
    });
    const data = await r.json();
    const msg = (data.choices && data.choices[0] && data.choices[0].message) || {};
    const text = msg.content || '';

    const urls = new Set();
    (msg.annotations || []).forEach(a => {
      const url = (a.url_citation && a.url_citation.url) || a.url;
      if (url) urls.add(url);
    });
    JSON.stringify(data).replace(/"url":"(https?:\/\/[^"]+)"/g, (m, u) => { urls.add(u); return m; });

    res.status(200).json({
      text,
      sources: Array.from(urls),
      brand_named: hasTerms(text, BRAND_TERMS),
    });
  } catch (e) {
    res.status(500).json({ error: String(e) });
  }
}

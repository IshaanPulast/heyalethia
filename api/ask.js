const BRAND_TERMS = ["all flooring now", "allflooringnow", "carpet tile tape"];
const COMPETITOR_TERMS = { "XFasten": ["xfasten"] };

function hasTerms(text, terms) {
  const t = text.toLowerCase();
  return terms.some(term => t.includes(term));
}

export default async function handler(req, res) {
  if (req.method !== 'POST') return res.status(405).json({ error: 'Use POST' });
  const { prompt } = req.body || {};
  if (!prompt) return res.status(400).json({ error: 'Missing prompt' });

  const key = process.env.OPENROUTER_API_KEY;
  if (!key) return res.status(500).json({ error: 'Server not configured' });

  try {
    const r = await fetch('https://openrouter.ai/api/v1/chat/completions', {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${key}`, 'Content-Type': 'application/json' },
      body: JSON.stringify({ model: 'openai/gpt-4o:online', messages: [{ role: 'user', content: prompt }] }),
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

    const domains = Array.from(urls).map(u => {
      try { return new URL(u).hostname.replace(/^www\./, ''); } catch { return u; }
    });

    const brandNamed = hasTerms(text, BRAND_TERMS);
    const competitorsNamed = Object.entries(COMPETITOR_TERMS)
      .filter(([name, terms]) => hasTerms(text, terms))
      .map(([name]) => name);

    let bottleneck = null;
    if (!brandNamed) {
      bottleneck = domains.length
        ? `Not mentioned. AI is pulling this answer from: ${domains.join(', ')}. Getting listed/cited on these sites is the fastest path to appearing here.`
        : `Not mentioned, and no third-party sources were cited either, this answer likely came from the model's general knowledge rather than a specific page.`;
    }

    res.status(200).json({
      text,
      sources: Array.from(urls),
      brand_named: brandNamed,
      competitors_named: competitorsNamed,
      bottleneck,
    });
  } catch (e) {
    res.status(500).json({ error: String(e) });
  }
}

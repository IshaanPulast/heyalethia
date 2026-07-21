export default async function handler(req, res) {
  if (req.method !== 'POST') return res.status(405).json({ error: 'Use POST' });
  const { question, article } = req.body || {};
  if (!question || !article) return res.status(400).json({ error: 'Missing question or article' });

  const key = process.env.OPENROUTER_API_KEY;
  if (!key) return res.status(500).json({ error: 'Server not configured' });

  let content = article.trim();
  const isUrl = /^https?:\/\//i.test(content);

  if (isUrl) {
    try {
      const pageRes = await fetch(content, { headers: { 'User-Agent': 'Mozilla/5.0' } });
      const html = await pageRes.text();
      content = html
        .replace(/<script[\s\S]*?<\/script>/gi, ' ')
        .replace(/<style[\s\S]*?<\/style>/gi, ' ')
        .replace(/<[^>]+>/g, ' ')
        .replace(/\s+/g, ' ')
        .trim()
        .slice(0, 12000);
      if (!content) {
        return res.status(400).json({ error: 'Could not extract text from that URL, paste the article text directly instead.' });
      }
    } catch (e) {
      return res.status(400).json({ error: 'Could not fetch that URL, paste the article text directly instead.' });
    }
  }

  const analysisPrompt = `A user asked an AI assistant: "${question}"

Here is a client's existing article/content on this exact topic:
---
${content}
---

Compare this article against what a comprehensive, technically authoritative answer needs to cover for this specific question. Be blunt and specific. List:
1. Missing steps or information a competitor's cited guide would include
2. Missing specific/technical details (exact measurements, temperatures, standards, timeframes) vs vague language
3. Structural issues (is it written as a numbered technical guide, or as marketing/narrative prose?)
4. The single highest-priority fix to add first

Keep it concise and actionable, no fluff.`;

  try {
    const r = await fetch('https://openrouter.ai/api/v1/chat/completions', {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${key}`, 'Content-Type': 'application/json' },
      body: JSON.stringify({ model: 'openai/gpt-4o', messages: [{ role: 'user', content: analysisPrompt }] }),
    });
    const data = await r.json();
    const msg = (data.choices && data.choices[0] && data.choices[0].message) || {};
    res.status(200).json({ analysis: msg.content || '', fetched_url: isUrl });
  } catch (e) {
    res.status(500).json({ error: String(e) });
  }
}

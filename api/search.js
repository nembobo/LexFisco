// Vercel Serverless Function — nasconde le credenziali Supabase
// Le credenziali stanno su Vercel, mai visibili nel browser

export default async function handler(req, res) {
  // CORS
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');
  if (req.method === 'OPTIONS') return res.status(200).end();
  if (req.method !== 'POST') return res.status(405).json({ error: 'Method not allowed' });

  const { query } = req.body;
  if (!query) return res.status(400).json({ error: 'Query mancante' });

  // Credenziali prese dalle Vercel Environment Variables — mai visibili nel browser
  const SUPABASE_URL = process.env.SUPABASE_URL;
  const SUPABASE_KEY = process.env.SUPABASE_KEY;

  if (!SUPABASE_URL || !SUPABASE_KEY) {
    return res.status(500).json({ error: 'Credenziali non configurate' });
  }

  try {
    const response = await fetch(`${SUPABASE_URL}/rest/v1/rpc/cerca_norme`, {
      method: 'POST',
      headers: {
        'apikey': SUPABASE_KEY,
        'Authorization': `Bearer ${SUPABASE_KEY}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ query_text: query, limite: 4 })
    });

    if (!response.ok) {
      const err = await response.text();
      return res.status(500).json({ error: err });
    }

    const docs = await response.json();
    return res.status(200).json({ docs: docs || [] });

  } catch (e) {
    return res.status(500).json({ error: e.message });
  }
}

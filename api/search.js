const fetch = require('node-fetch');

module.exports = async function handler(req, res) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');
  if (req.method === 'OPTIONS') return res.status(200).end();
  if (req.method !== 'POST') return res.status(405).json({ error: 'Method not allowed' });

  const SUPABASE_URL = process.env.SUPABASE_URL;
  const SUPABASE_KEY = process.env.SUPABASE_KEY;
  if (!SUPABASE_URL || !SUPABASE_KEY) return res.status(500).json({ error: 'DB non configurato' });

  const { query } = req.body;
  if (!query) return res.status(400).json({ error: 'Query mancante' });

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
    const docs = await response.json();
    return res.status(200).json({ docs: docs || [] });
  } catch (e) {
    return res.status(500).json({ error: e.message });
  }
};

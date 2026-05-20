const fetch = require('node-fetch');

module.exports = async function handler(req, res) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');
  if (req.method === 'OPTIONS') return res.status(200).end();
  if (req.method !== 'POST') return res.status(405).json({ error: 'Method not allowed' });

  const ANTHROPIC_KEY = process.env.ANTHROPIC_API_KEY;
  if (!ANTHROPIC_KEY) return res.status(500).json({ error: 'Chiave API non configurata' });

  let { messages, system } = req.body;
  if (!messages || !Array.isArray(messages)) {
    return res.status(400).json({ error: 'Messaggi mancanti o non validi' });
  }

  // Pulisci i messaggi — converti contenuto non stringa in stringa
  messages = messages.map(m => {
    if (typeof m.content === 'string') return m;
    if (Array.isArray(m.content)) return m; // array di content blocks — ok per file
    return { role: m.role, content: String(m.content || '') };
  });

  try {
    const body = {
      model: 'claude-sonnet-4-6',
      max_tokens: 2000,
      tools: [{ type: "web_search_20250305", name: "web_search" }],
      messages: messages
    };

    if (system && typeof system === 'string' && system.trim()) {
      body.system = system;
    }

    const response = await fetch('https://api.anthropic.com/v1/messages', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'x-api-key': ANTHROPIC_KEY,
        'anthropic-version': '2023-06-01'
      },
      body: JSON.stringify(body)
    });

    const data = await response.json();

    if (!response.ok) {
      console.error('Anthropic error:', JSON.stringify(data));
      return res.status(response.status).json({
        error: data.error?.message || `Errore API: ${response.status}`
      });
    }

    return res.status(200).json(data);

  } catch (e) {
    console.error('Handler error:', e);
    return res.status(500).json({ error: e.message || 'Errore interno' });
  }
};

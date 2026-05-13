const fetch = require('node-fetch');

module.exports = async function handler(req, res) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, DELETE, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');
  if (req.method === 'OPTIONS') return res.status(200).end();

  const SUPABASE_URL = process.env.SUPABASE_URL;
  const SUPABASE_KEY = process.env.SUPABASE_KEY;
  if (!SUPABASE_URL || !SUPABASE_KEY) return res.status(500).json({ error: 'DB non configurato' });

  const headers = {
    'apikey': SUPABASE_KEY,
    'Authorization': `Bearer ${SUPABASE_KEY}`,
    'Content-Type': 'application/json'
  };

  // GET — carica consulenze dell'utente
  if (req.method === 'GET') {
    const { user_id } = req.query;
    if (!user_id) return res.status(400).json({ error: 'user_id mancante' });
    try {
      const r = await fetch(`${SUPABASE_URL}/rest/v1/consulenze?user_id=eq.${user_id}&order=aggiornata_il.desc&limit=50`, { headers });
      const data = await r.json();
      return res.status(200).json(data);
    } catch (e) { return res.status(500).json({ error: e.message }); }
  }

  // POST — salva/aggiorna consulenza
  if (req.method === 'POST') {
    const { id, user_id, titolo, messaggi } = req.body;
    if (!user_id) return res.status(400).json({ error: 'user_id mancante' });
    try {
      const payload = {
        id: id || undefined,
        user_id,
        titolo: titolo || 'Nuova consulenza',
        messaggi: JSON.stringify(messaggi || []),
        aggiornata_il: new Date().toISOString()
      };
      const r = await fetch(`${SUPABASE_URL}/rest/v1/consulenze`, {
        method: 'POST',
        headers: { ...headers, 'Prefer': 'return=representation,resolution=merge-duplicates' },
        body: JSON.stringify(payload)
      });
      const data = await r.json();
      return res.status(200).json(Array.isArray(data) ? data[0] : data);
    } catch (e) { return res.status(500).json({ error: e.message }); }
  }

  // DELETE — elimina consulenza
  if (req.method === 'DELETE') {
    const { id, user_id } = req.query;
    if (!id || !user_id) return res.status(400).json({ error: 'Parametri mancanti' });
    try {
      await fetch(`${SUPABASE_URL}/rest/v1/consulenze?id=eq.${id}&user_id=eq.${user_id}`, { method: 'DELETE', headers });
      return res.status(200).json({ ok: true });
    } catch (e) { return res.status(500).json({ error: e.message }); }
  }
};

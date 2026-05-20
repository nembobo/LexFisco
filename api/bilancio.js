const fetch = require('node-fetch');

module.exports = async function handler(req, res) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');
  if (req.method === 'OPTIONS') return res.status(200).end();
  if (req.method !== 'POST') return res.status(405).json({ error: 'Method not allowed' });

  const ANTHROPIC_KEY = process.env.ANTHROPIC_API_KEY;
  if (!ANTHROPIC_KEY) return res.status(500).json({ error: 'Chiave API non configurata' });

  const { pdfBase64 } = req.body;
  if (!pdfBase64) return res.status(400).json({ error: 'PDF mancante' });

  const prompt = `Sei un esperto contabile italiano. Analizza questo bilancio fiscale Sistemi.

REGOLE CEE art. 2435-bis:
- B.I Immateriali: costi impianto, avviamento, oneri pluriennali su beni terzi — al netto fondi
- B.II Materiali: immobili strumentali di proprietà, macchinari, attrezzature — al netto fondi. ESCLUDI immobili destinati vendita
- B.III Finanziarie: depositi cauzionali lungo termine. BOT/fondi → C.III
- C.I Rimanenze: immobili destinati vendita (macroclassi 16 e 17) + posti auto
- C.II Crediti: clienti, erario, diversi (separa entro/oltre 12 mesi)
- C.III: BOT, fondi, titoli non immobilizzati
- C.IV: cassa e banche
- A) PN: capitale + riserve + utile. Perdite a nuovo = NEGATIVO nel passivo
- C) TFR
- D) Debiti: fornitori, tributari, dipendenti, caparre passive
- E) Ratei risconti passivi

RISPONDI SOLO CON IL JSON, NESSUN TESTO PRIMA O DOPO, NESSUNA SPIEGAZIONE:
{"B1":0,"B2":0,"B3":0,"totB":0,"C1":0,"C2entro":0,"C2oltre":0,"C3":0,"C4":0,"totC":0,"D":0,"totAttivo":0,"PN_capitale":0,"PN_riservaLegale":0,"PN_altreRiserve":0,"PN_perditaNuovo":0,"PN_utile":0,"totPN":0,"TFR":0,"debentiEntro":0,"debOltre":0,"rateiPassivi":0,"totPassivo":0,"quadra":true}`;

  try {
    const response = await fetch('https://api.anthropic.com/v1/messages', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'x-api-key': ANTHROPIC_KEY,
        'anthropic-version': '2023-06-01'
      },
      body: JSON.stringify({
        model: 'claude-sonnet-4-6',
        max_tokens: 1000,
        messages: [{
          role: 'user',
          content: [
            { type: 'document', source: { type: 'base64', media_type: 'application/pdf', data: pdfBase64 } },
            { type: 'text', text: prompt }
          ]
        }]
      })
    });

    const data = await response.json();
    const rawText = data.content?.[0]?.text || '';
    
    // Cerca il JSON anche se c'è testo prima/dopo
    const jsonStart = rawText.indexOf('{');
    const jsonEnd = rawText.lastIndexOf('}');
    if (jsonStart === -1 || jsonEnd === -1) {
      return res.status(500).json({ 
        error: 'Risposta non valida', 
        debug: rawText.substring(0, 300) 
      });
    }
    const jsonStr = rawText.substring(jsonStart, jsonEnd + 1);
    
    const bilancio = JSON.parse(jsonStr);
    return res.status(200).json(bilancio);

  } catch (e) {
    return res.status(500).json({ error: e.message });
  }
};

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

  const prompt = `Sei un esperto contabile italiano. Analizza questo bilancio fiscale Sistemi e produci la riclassificazione in schema CEE art. 2435-bis (bilancio abbreviato).

REGOLE TASSATIVE:
- B.I Immateriali: costi impianto, avviamento, oneri pluriennali su beni di terzi (al netto fondi)
- B.II Materiali: immobili strumentali DI PROPRIETÀ, macchinari, attrezzature (al netto fondi). ESCLUDI immobili destinati alla vendita
- B.III Finanziarie: depositi cauzionali attivi lungo termine, partecipazioni. BOT/fondi vanno in C.III
- C.I Rimanenze: immobili destinati alla vendita (macroclassi 16 e 17)
- C.II Crediti: tutti i crediti v/clienti, erario, diversi (separa entro/oltre 12 mesi)
- C.III: BOT, fondi, titoli non immobilizzati
- C.IV: cassa e banche
- Passivo A): capitale + riserve + utile. Perdite a nuovo = voce NEGATIVA, non nell'attivo
- Passivo C): TFR
- Passivo D): tutti i debiti (fornitori, tributari, dipendenti, caparre passive)
- Passivo E): ratei e risconti passivi

IMPORTANTE: le perdite a nuovo nel bilancio fiscale appaiono nell'ATTIVO ma nel CEE vanno in DETRAZIONE dal patrimonio netto (voce negativa).

Restituisci SOLO questo JSON senza testo aggiuntivo:
{
  "B1": 0,
  "B2": 0,
  "B3": 0,
  "totB": 0,
  "C1": 0,
  "C2entro": 0,
  "C2oltre": 0,
  "C3": 0,
  "C4": 0,
  "totC": 0,
  "D": 0,
  "totAttivo": 0,
  "PN_capitale": 0,
  "PN_riservaLegale": 0,
  "PN_altreRiserve": 0,
  "PN_perditaNuovo": 0,
  "PN_utile": 0,
  "totPN": 0,
  "TFR": 0,
  "debentiEntro": 0,
  "debOltre": 0,
  "rateiPassivi": 0,
  "totPassivo": 0,
  "quadra": true
}`;

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
    const text = data.content?.[0]?.text || '';
    
    // Estrai JSON
    const jsonMatch = text.match(/\{[\s\S]*\}/);
    if (!jsonMatch) return res.status(500).json({ error: 'Risposta non valida dal modello' });
    
    const bilancio = JSON.parse(jsonMatch[0]);
    return res.status(200).json(bilancio);

  } catch (e) {
    return res.status(500).json({ error: e.message });
  }
};

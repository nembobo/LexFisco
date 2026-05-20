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

  // Step 1: Estrai tutti i conti dal PDF con Claude
  const extractPrompt = `Sei un parser di bilanci fiscali del software Sistemi/Profis.
  
Analizza questo bilancio fiscale e restituisci un JSON con TUTTI i conti presenti.
Il formato del bilancio Sistemi ha:
- Colonna ATTIVITÀ (Dare): conti con codice G/C/F e numero
- Colonna PASSIVITÀ (Avere): conti con codice G/C/F e numero
- Macroclassi numerare (1=Cassa, 2=Banche, 3=Debitori, ecc.)
- Fondi ammortamento sul lato Passività

Restituisci SOLO questo JSON, niente altro:
{
  "conti_attivo": [
    {"codice": "G1", "descrizione": "CASSA CONTANTE", "importo": 160.69, "macroclasse": 1},
    ...
  ],
  "conti_passivo": [
    {"codice": "G34", "descrizione": "FONDO AMM.TO MACCH.UFFICIO", "importo": 2239.28, "macroclasse": 8},
    ...
  ],
  "utile_presunto": 473280.51,
  "totale_bilancio": 9573898.63
}

Includi OGNI singolo conto presente nel PDF senza omettere nulla.`;

  try {
    // Estrai conti dal PDF
    const extractRes = await fetch('https://api.anthropic.com/v1/messages', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'x-api-key': ANTHROPIC_KEY,
        'anthropic-version': '2023-06-01'
      },
      body: JSON.stringify({
        model: 'claude-sonnet-4-6',
        max_tokens: 4000,
        messages: [{
          role: 'user',
          content: [
            { type: 'document', source: { type: 'base64', media_type: 'application/pdf', data: pdfBase64 } },
            { type: 'text', text: extractPrompt }
          ]
        }]
      })
    });

    const extractData = await extractRes.json();
    const rawText = extractData.content?.[0]?.text || '';
    
    // Pulisci e parsa il JSON
    const jsonMatch = rawText.match(/\{[\s\S]*\}/);
    if (!jsonMatch) {
      return res.status(500).json({ error: 'Impossibile estrarre i conti dal PDF' });
    }
    
    const conti = JSON.parse(jsonMatch[0]);

    // Step 2: Classifica i conti in schema CEE
    const classifyPrompt = `Sei un esperto di bilanci CEE italiani. 
    
Hai questi conti estratti da un bilancio fiscale Sistemi:
${JSON.stringify(conti, null, 2)}

Classificali nello schema CEE art. 2435-bis (bilancio abbreviato) seguendo RIGOROSAMENTE queste regole OIC:

**B.I IMMOBILIZZAZIONI IMMATERIALI** (beni intangibili, al netto fondi):
- Costi impianto/ampliamento/sviluppo → B.I
- Avviamento → B.I  
- Oneri pluriennali incluse ristrutturazioni su beni DI TERZI → B.I
- Concessioni, licenze, marchi → B.I

**B.II IMMOBILIZZAZIONI MATERIALI** (beni tangibili DI PROPRIETÀ, al netto fondi):
- Terreni e fabbricati strumentali di proprietà → B.II.1
- Impianti e macchinari → B.II.2
- Attrezzature → B.II.3
- Altri beni (mobili, auto, elettronici, fotovoltaico) → B.II.4
- ESCLUDI immobili destinati alla vendita (vanno in C.I)

**B.III IMMOBILIZZAZIONI FINANZIARIE**:
- Depositi cauzionali attivi a lungo termine → B.III
- Partecipazioni → B.III
- ESCLUDI BOT/fondi/titoli a breve (vanno in C.III)

**C.I RIMANENZE**: immobili destinati vendita, costruzioni in corso, rimanenze merci

**C.II CREDITI**: tutti i crediti (clienti, erario, diversi) — separa entro/oltre 12 mesi

**C.III ATTIVITÀ FINANZIARIE NON IMMOBILIZZATE**: BOT, fondi, titoli a breve

**C.IV DISPONIBILITÀ LIQUIDE**: cassa e banche

**PASSIVO**:
- A) Patrimonio netto (perdite a nuovo = voce negativa)
- C) TFR
- D) Debiti entro/oltre 12 mesi
- E) Ratei e risconti passivi

Restituisci SOLO questo JSON:
{
  "stato_patrimoniale": {
    "attivo": {
      "B_immobilizzazioni": {
        "B1_immateriali": {"valore": 0, "dettaglio": []},
        "B2_materiali": {"valore": 0, "dettaglio": []},
        "B3_finanziarie": {"valore": 0, "dettaglio": []}
      },
      "C_circolante": {
        "C1_rimanenze": {"valore": 0, "dettaglio": []},
        "C2_crediti_entro": {"valore": 0, "dettaglio": []},
        "C2_crediti_oltre": {"valore": 0, "dettaglio": []},
        "C3_attivita_finanziarie": {"valore": 0, "dettaglio": []},
        "C4_disponibilita": {"valore": 0, "dettaglio": []}
      },
      "D_ratei_risconti": {"valore": 0, "dettaglio": []}
    },
    "passivo": {
      "A_patrimonio_netto": {
        "I_capitale": 0,
        "IV_riserva_legale": 0,
        "VI_altre_riserve": 0,
        "VIII_perdite_nuovo": 0,
        "IX_utile_esercizio": 0,
        "totale": 0
      },
      "C_tfr": {"valore": 0},
      "D_debiti_entro": {"valore": 0, "dettaglio": []},
      "D_debiti_oltre": {"valore": 0, "dettaglio": []},
      "E_ratei_risconti": {"valore": 0, "dettaglio": []}
    }
  },
  "totale_attivo": 0,
  "totale_passivo": 0,
  "quadra": true
}`;

    const classifyRes = await fetch('https://api.anthropic.com/v1/messages', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'x-api-key': ANTHROPIC_KEY,
        'anthropic-version': '2023-06-01'
      },
      body: JSON.stringify({
        model: 'claude-sonnet-4-6',
        max_tokens: 4000,
        messages: [{ role: 'user', content: classifyPrompt }]
      })
    });

    const classifyData = await classifyRes.json();
    const classifyText = classifyData.content?.[0]?.text || '';
    const classifyJson = classifyText.match(/\{[\s\S]*\}/);
    
    if (!classifyJson) {
      return res.status(500).json({ error: 'Impossibile classificare i conti' });
    }

    const bilancio = JSON.parse(classifyJson[0]);
    return res.status(200).json({ conti, bilancio });

  } catch (e) {
    return res.status(500).json({ error: e.message });
  }
};

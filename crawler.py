"""
LexFisco Crawler — Versione completa AGGIORNATA
Legge RSS, pagine statiche, PDF e nuove circolari/sentenze
Richiede: pip install requests beautifulsoup4 python-dotenv feedparser pymupdf
"""

import os
import time
import hashlib
import feedparser
import requests
import fitz
from datetime import datetime
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from urllib.parse import urljoin

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

HEADERS_DB = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=minimal"
}

DB_URL = f"{SUPABASE_URL}/rest/v1/documenti_normativi"

BROWSER = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "it-IT,it;q=0.9,en;q=0.8",
}

# ============================================================
# FASE 1 — FEED RSS
# ============================================================
FONTI_RSS = [
    {"nome": "Il Sole 24 Ore — Norme e Tributi", "tipo": "notizia_fiscale", "fonte": "ilsole24ore.com", "url": "https://www.ilsole24ore.com/rss/norme-e-tributi.xml"},
    {"nome": "Diritto.it — Notizie giuridiche", "tipo": "notizia_giuridica", "fonte": "diritto.it", "url": "https://www.diritto.it/feed/"},
    {"nome": "FiscoOggi — Agenzia Entrate", "tipo": "circolare", "fonte": "fiscooggi.it", "url": "https://www.fiscooggi.it/rss.xml"},
    {"nome": "Altalex — Fisco", "tipo": "notizia_fiscale", "fonte": "altalex.com", "url": "https://www.altalex.com/feed/fisco"},
    {"nome": "Altalex — Lavoro", "tipo": "notizia_lavoro", "fonte": "altalex.com", "url": "https://www.altalex.com/feed/lavoro"},
    {"nome": "Altalex — Società", "tipo": "notizia_societa", "fonte": "altalex.com", "url": "https://www.altalex.com/feed/societa"},
    {"nome": "Altalex — Civile", "tipo": "notizia_civile", "fonte": "altalex.com", "url": "https://www.altalex.com/feed/civile"},
    {"nome": "La Legge Per Tutti", "tipo": "notizia_fiscale", "fonte": "laleggepertutti.it", "url": "https://www.laleggepertutti.it/feed"},
    {"nome": "EUR-Lex — Gazzetta UE", "tipo": "normativa_europea", "fonte": "eur-lex.europa.eu", "url": "https://eur-lex.europa.eu/rss/rss-oj-l.xml"},
    {"nome": "Europarl — Normativa EU", "tipo": "normativa_europea", "fonte": "europarl.europa.eu", "url": "https://www.europarl.europa.eu/rss/doc/top-stories/it.xml"},
    # Nuovi feed
    {"nome": "FiscoOggi — Norme e Prassi", "tipo": "circolare", "fonte": "fiscooggi.it", "url": "https://www.fiscooggi.it/rubrica/normativa-e-prassi/rss.xml"},
    {"nome": "Fiscoetasse — Notizie", "tipo": "notizia_fiscale", "fonte": "fiscoetasse.com", "url": "https://www.fiscoetasse.com/feed/"},
    {"nome": "Wikilabour — Aggiornamenti", "tipo": "ccnl", "fonte": "wikilabour.it", "url": "https://www.wikilabour.it/feed/"},
]

# ============================================================
# FASE 2 — PAGINE STATICHE
# ============================================================
PAGINE_STATICHE = [
    # INPS
    {"titolo": "INPS — Aliquote contributive artigiani e commercianti", "tipo": "previdenza", "fonte": "inps.it", "url": "https://www.inps.it/it/it/dettaglio-scheda.schede-servizio-e-prestazioni.50545.aliquote-e-massimale-contributivo-per-artigiani-e-commercianti.html"},
    {"titolo": "INPS — Gestione separata aliquote", "tipo": "previdenza", "fonte": "inps.it", "url": "https://www.inps.it/it/it/dettaglio-scheda.schede-servizio-e-prestazioni.50546.aliquote-e-massimale-per-iscritti-alla-gestione-separata.html"},
    {"titolo": "INPS — CIG Cassa integrazione guadagni", "tipo": "previdenza", "fonte": "inps.it", "url": "https://www.inps.it/it/it/dettaglio-scheda.schede-servizio-e-prestazioni.50048.cassa-integrazione-guadagni-ordinaria-cigo-.html"},
    {"titolo": "INPS — Pensione anticipata", "tipo": "previdenza", "fonte": "inps.it", "url": "https://www.inps.it/it/it/dettaglio-scheda.schede-servizio-e-prestazioni.50048.pensione-anticipata.html"},
    {"titolo": "INPS — NASpI disoccupazione", "tipo": "previdenza", "fonte": "inps.it", "url": "https://www.inps.it/it/it/dettaglio-scheda.schede-servizio-e-prestazioni.50048.naspi.html"},
    {"titolo": "INPS — Maternità e paternità", "tipo": "previdenza", "fonte": "inps.it", "url": "https://www.inps.it/it/it/dettaglio-scheda.schede-servizio-e-prestazioni.50048.indennita-di-maternita-paternita.html"},
    {"titolo": "INPS — TFR trattamento di fine rapporto", "tipo": "previdenza", "fonte": "inps.it", "url": "https://www.inps.it/it/it/dettaglio-scheda.schede-servizio-e-prestazioni.50048.tfr.html"},
    # AdE
    {"titolo": "AdE — Regime forfettario", "tipo": "dichiarazione", "fonte": "agenziaentrate.gov.it", "url": "https://www.agenziaentrate.gov.it/portale/web/guest/schede/dichiarazioni/regime-forfetario/info-gen-regime-forfetario"},
    {"titolo": "AdE — Ravvedimento operoso", "tipo": "adempimento", "fonte": "agenziaentrate.gov.it", "url": "https://www.agenziaentrate.gov.it/portale/web/guest/schede/pagamenti/ravvedimento-operoso/info-ravvedimento"},
    {"titolo": "AdE — IMU istruzioni", "tipo": "tributo_locale", "fonte": "agenziaentrate.gov.it", "url": "https://www.agenziaentrate.gov.it/portale/web/guest/schede/pagamenti/imu"},
    {"titolo": "AdE — Successioni e donazioni", "tipo": "successioni", "fonte": "agenziaentrate.gov.it", "url": "https://www.agenziaentrate.gov.it/portale/web/guest/schede/successioni-e-donazioni"},
    {"titolo": "AdE — F24 istruzioni", "tipo": "adempimento", "fonte": "agenziaentrate.gov.it", "url": "https://www.agenziaentrate.gov.it/portale/web/guest/schede/pagamenti/f24"},
    {"titolo": "AdE — Cartelle esattoriali", "tipo": "riscossione", "fonte": "agenziaentrate.gov.it", "url": "https://www.agenziaentrate.gov.it/portale/web/guest/schede/pagamenti/cartelle-esattoriali"},
    {"titolo": "AdE — Rottamazione cartelle", "tipo": "riscossione", "fonte": "agenziaentrate.gov.it", "url": "https://www.agenziaentrate.gov.it/portale/web/guest/schede/pagamenti/rottamazione"},
    # CCNL Wikilabour
    {"titolo": "CCNL Agenti assicurazione ANAPA UNAPASS", "tipo": "ccnl", "fonte": "wikilabour.it", "url": "https://www.wikilabour.it/dizionario/ccnl/agenti-assicurazione/"},
    {"titolo": "CCNL Commercio Terziario Confcommercio", "tipo": "ccnl", "fonte": "wikilabour.it", "url": "https://www.wikilabour.it/dizionario/ccnl/commercio/"},
    {"titolo": "CCNL Metalmeccanici Industria", "tipo": "ccnl", "fonte": "wikilabour.it", "url": "https://www.wikilabour.it/dizionario/ccnl/metalmeccanici-industria/"},
    {"titolo": "CCNL Studi Professionali", "tipo": "ccnl", "fonte": "wikilabour.it", "url": "https://www.wikilabour.it/dizionario/ccnl/studi-professionali/"},
    {"titolo": "CCNL Turismo Pubblici Esercizi", "tipo": "ccnl", "fonte": "wikilabour.it", "url": "https://www.wikilabour.it/dizionario/ccnl/turismo-pubblici-esercizi/"},
    {"titolo": "CCNL Edilizia Industria", "tipo": "ccnl", "fonte": "wikilabour.it", "url": "https://www.wikilabour.it/dizionario/ccnl/edilizia-industria/"},
    {"titolo": "CCNL Bancari ABI", "tipo": "ccnl", "fonte": "wikilabour.it", "url": "https://www.wikilabour.it/dizionario/ccnl/bancari-abi/"},
    {"titolo": "CCNL Cooperative Sociali", "tipo": "ccnl", "fonte": "wikilabour.it", "url": "https://www.wikilabour.it/dizionario/ccnl/cooperative-sociali/"},
    {"titolo": "CCNL Pulizie Multiservizi", "tipo": "ccnl", "fonte": "wikilabour.it", "url": "https://www.wikilabour.it/dizionario/ccnl/pulizie-multiservizi/"},
    {"titolo": "CCNL Trasporti Logistica", "tipo": "ccnl", "fonte": "wikilabour.it", "url": "https://www.wikilabour.it/dizionario/ccnl/trasporti-logistica/"},
    # MEF
    {"titolo": "MEF — Fiscalità nazionale", "tipo": "fiscalita", "fonte": "finanze.gov.it", "url": "https://www.finanze.gov.it/it/fiscalita-nazionale/"},
    {"titolo": "MEF — Fiscalità internazionale", "tipo": "fiscalita_internazionale", "fonte": "finanze.gov.it", "url": "https://www.finanze.gov.it/it/fiscalita-internazionale/"},
]

# ============================================================
# FASE 3 — PDF DA CONTROLLARE OGNI SETTIMANA
# ============================================================
PDF_SETTIMANALI = [
    # Bollettini MEF mensili
    {"titolo": "MEF — Bollettino entrate tributarie ultimo mese", "tipo": "statistica", "fonte": "finanze.gov.it",
     "url": "https://www.finanze.gov.it/it/fiscalita-nazionale/analisi-statistiche/entrate-tributarie-nazionali/"},
    # FiscoOggi — ultime circolari
    {"titolo": "FiscoOggi — Ultime circolari e risoluzioni AdE", "tipo": "circolare", "fonte": "fiscooggi.it",
     "url": "https://www.fiscooggi.it/rubrica/normativa-e-prassi"},
    # Gazzetta Ufficiale
    {"titolo": "Gazzetta Ufficiale — Ultime pubblicazioni", "tipo": "gazzetta_ufficiale", "fonte": "gazzettaufficiale.it",
     "url": "https://www.gazzettaufficiale.it/home"},
    # OIC — nuovi documenti
    {"titolo": "OIC — Nuovi principi e aggiornamenti", "tipo": "principi_contabili", "fonte": "fondazioneoic.eu",
     "url": "https://www.fondazioneoic.eu/?page_id=3097"},
    # INPS — circolari
    {"titolo": "INPS — Ultime circolari e messaggi", "tipo": "previdenza", "fonte": "inps.it",
     "url": "https://www.inps.it/it/it/circolari-e-messaggi.html"},
]

# ============================================================
# FUNZIONI
# ============================================================

def genera_id(url, titolo=""):
    return hashlib.md5(f"{url}{titolo}".encode()).hexdigest()

def doc_esiste(id_univoco):
    try:
        r = requests.get(DB_URL, headers={**HEADERS_DB, "Prefer": ""},
                        params={"id_univoco": f"eq.{id_univoco}", "select": "id"}, timeout=10)
        return len(r.json()) > 0
    except:
        return False

def scarica_testo_html(url):
    try:
        r = requests.get(url, headers=BROWSER, timeout=20)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "header", "aside", "form"]):
            tag.decompose()
        testo = soup.get_text(separator="\n", strip=True)
        righe = [r.strip() for r in testo.split("\n") if r.strip() and len(r.strip()) > 20]
        return "\n".join(righe)[:20000]
    except:
        return ""

def scarica_pdf(url):
    try:
        r = requests.get(url, headers={**BROWSER, "Accept": "application/pdf,*/*"}, timeout=30, allow_redirects=True)
        if r.status_code != 200:
            return ""
        if "application/pdf" not in r.headers.get("Content-Type", ""):
            return ""
        doc = fitz.open(stream=r.content, filetype="pdf")
        testo = ""
        for pag in doc:
            testo += pag.get_text()
            if len(testo) > 30000:
                break
        doc.close()
        return testo[:30000].strip()
    except:
        return ""

def trova_pdf_in_pagina(url, base_url=None):
    """Trova tutti i link PDF in una pagina"""
    try:
        r = requests.get(url, headers=BROWSER, timeout=20)
        soup = BeautifulSoup(r.text, "html.parser")
        pdf_links = []
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if href.lower().endswith(".pdf"):
                if base_url:
                    href = urljoin(base_url, href)
                pdf_links.append((a.get_text(strip=True)[:200], href))
        return pdf_links[:10]  # Max 10 PDF per pagina
    except:
        return []

def salva_documento(doc):
    try:
        r = requests.post(DB_URL, headers=HEADERS_DB, json=doc, timeout=10)
        return r.status_code in [200, 201]
    except:
        return False

# ============================================================
# CRAWLERS
# ============================================================

def crawla_rss(fonte):
    print(f"\n📡 {fonte['nome']}")
    try:
        r = requests.get(fonte["url"], headers=BROWSER, timeout=15)
        if r.status_code != 200:
            print(f"  ⚠ HTTP {r.status_code}")
            return 0
        feed = feedparser.parse(r.text)
        if not feed.entries:
            print(f"  ⚠ Nessuna voce")
            return 0
        print(f"  📋 {len(feed.entries)} voci")
        nuovi = 0
        for entry in feed.entries[:10]:
            titolo = getattr(entry, "title", "Senza titolo")
            url = getattr(entry, "link", "")
            sommario = getattr(entry, "summary", "")
            try:
                data_pub = datetime(*entry.published_parsed[:6]).strftime("%Y-%m-%d")
            except:
                data_pub = datetime.now().strftime("%Y-%m-%d")
            if not url:
                continue
            id_univoco = genera_id(url, titolo)
            if doc_esiste(id_univoco):
                continue
            time.sleep(1)

            # Prova a scaricare il contenuto completo
            testo = scarica_testo_html(url)

            # Se la pagina contiene PDF, scarica anche quelli
            pdf_links = trova_pdf_in_pagina(url, url)
            for pdf_titolo, pdf_url in pdf_links[:3]:
                pdf_id = genera_id(pdf_url)
                if not doc_esiste(pdf_id):
                    pdf_testo = scarica_pdf(pdf_url)
                    if pdf_testo and len(pdf_testo) > 200:
                        pdf_doc = {
                            "id_univoco": pdf_id,
                            "titolo": f"[PDF] {pdf_titolo or titolo}",
                            "tipo": fonte["tipo"],
                            "fonte": fonte["fonte"],
                            "data_pubblicazione": data_pub,
                            "contenuto": pdf_testo,
                            "url_fonte": pdf_url,
                            "creato_il": datetime.now().isoformat()
                        }
                        salva_documento(pdf_doc)

            contenuto = f"{sommario}\n\n{testo}".strip()
            doc = {
                "id_univoco": id_univoco,
                "titolo": titolo[:500],
                "tipo": fonte["tipo"],
                "fonte": fonte["fonte"],
                "data_pubblicazione": data_pub,
                "contenuto": contenuto[:20000],
                "url_fonte": url,
                "creato_il": datetime.now().isoformat()
            }
            if salva_documento(doc):
                nuovi += 1
                print(f"  ✅ {titolo[:65]}...")
        print(f"  📊 Nuovi: {nuovi}")
        return nuovi
    except Exception as e:
        print(f"  ❌ Errore: {e}")
        return 0

def crawla_pagina(pagina):
    titolo = pagina["titolo"]
    url = pagina["url"]
    id_univoco = genera_id(url, titolo)
    if doc_esiste(id_univoco):
        return 0
    time.sleep(2)
    testo = scarica_testo_html(url)
    if not testo or len(testo) < 150:
        return 0
    # Cerca PDF nella pagina e scaricali
    pdf_links = trova_pdf_in_pagina(url, url)
    nuovi_pdf = 0
    for pdf_titolo, pdf_url in pdf_links[:5]:
        pdf_id = genera_id(pdf_url)
        if not doc_esiste(pdf_id):
            pdf_testo = scarica_pdf(pdf_url)
            if pdf_testo and len(pdf_testo) > 200:
                pdf_doc = {
                    "id_univoco": pdf_id,
                    "titolo": f"[PDF] {pdf_titolo or titolo}",
                    "tipo": pagina["tipo"],
                    "fonte": pagina["fonte"],
                    "data_pubblicazione": datetime.now().strftime("%Y-%m-%d"),
                    "contenuto": pdf_testo,
                    "url_fonte": pdf_url,
                    "creato_il": datetime.now().isoformat()
                }
                if salva_documento(pdf_doc):
                    nuovi_pdf += 1
    doc = {
        "id_univoco": id_univoco,
        "titolo": titolo,
        "tipo": pagina["tipo"],
        "fonte": pagina["fonte"],
        "data_pubblicazione": datetime.now().strftime("%Y-%m-%d"),
        "contenuto": testo,
        "url_fonte": url,
        "creato_il": datetime.now().isoformat()
    }
    if salva_documento(doc):
        print(f"  ✅ {titolo[:60]}... (+{nuovi_pdf} PDF)")
        return 1 + nuovi_pdf
    return 0

def crawla_pdf_settimanali():
    """Controlla le pagine chiave ogni settimana per nuovi PDF"""
    print(f"\n📄 FASE 3 — Controllo PDF settimanali ({len(PDF_SETTIMANALI)} fonti)")
    print("-" * 65)
    totale = 0
    for pagina in PDF_SETTIMANALI:
        print(f"\n  🔍 {pagina['titolo'][:55]}...")
        try:
            pdf_links = trova_pdf_in_pagina(pagina["url"], pagina["url"])
            nuovi = 0
            for pdf_titolo, pdf_url in pdf_links:
                pdf_id = genera_id(pdf_url)
                if doc_esiste(pdf_id):
                    continue
                pdf_testo = scarica_pdf(pdf_url)
                if pdf_testo and len(pdf_testo) > 200:
                    pdf_doc = {
                        "id_univoco": pdf_id,
                        "titolo": f"[PDF] {pdf_titolo[:280]}",
                        "tipo": pagina["tipo"],
                        "fonte": pagina["fonte"],
                        "data_pubblicazione": datetime.now().strftime("%Y-%m-%d"),
                        "contenuto": pdf_testo,
                        "url_fonte": pdf_url,
                        "creato_il": datetime.now().isoformat()
                    }
                    if salva_documento(pdf_doc):
                        nuovi += 1
                        print(f"     📄 {pdf_titolo[:50]}...")
                time.sleep(2)
            totale += nuovi
            print(f"     Nuovi PDF: {nuovi}")
        except Exception as e:
            print(f"     ❌ Errore: {e}")
        time.sleep(3)
    return totale

def main():
    print("=" * 65)
    print("🔍 LexFisco Crawler — Aggiornamento settimanale completo")
    print(f"⏰ {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    print("=" * 65)

    # FASE 1 — RSS
    print("\n📰 FASE 1 — Notizie RSS aggiornate")
    print("-" * 65)
    tot_rss = sum(crawla_rss(f) for f in FONTI_RSS)
    time.sleep(2)

    # FASE 2 — Pagine statiche + PDF
    print(f"\n📋 FASE 2 — Pagine statiche e PDF ({len(PAGINE_STATICHE)} fonti)")
    print("-" * 65)
    tot_statici = 0
    for pagina in PAGINE_STATICHE:
        tot_statici += crawla_pagina(pagina)

    # FASE 3 — PDF settimanali
    tot_pdf = crawla_pdf_settimanali()

    print("\n" + "=" * 65)
    print(f"✅ Aggiornamento completato!")
    print(f"📰 Notizie RSS:       {tot_rss}")
    print(f"📋 Pagine+PDF:        {tot_statici}")
    print(f"📄 Nuovi PDF:         {tot_pdf}")
    print(f"📚 Totale:            {tot_rss + tot_statici + tot_pdf}")
    print("=" * 65)

if __name__ == "__main__":
    main()

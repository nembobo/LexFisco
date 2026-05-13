"""
LexFisco Crawler — Versione completa per studio commercialista
Fonti: Notizie fiscali, CCNL, INPS, Normativa, Previdenza, Società
Richiede: pip install requests beautifulsoup4 python-dotenv feedparser
"""

import os
import time
import hashlib
import feedparser
import requests
from datetime import datetime
from bs4 import BeautifulSoup
from dotenv import load_dotenv

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
# FASE 1 — FEED RSS (notizie aggiornate ogni settimana)
# ============================================================
FONTI_RSS = [
    # Fisco e tributi
    {"nome": "Il Sole 24 Ore — Norme e Tributi", "tipo": "notizia_fiscale", "fonte": "ilsole24ore.com", "url": "https://www.ilsole24ore.com/rss/norme-e-tributi.xml"},
    {"nome": "Diritto.it — Notizie giuridiche", "tipo": "notizia_giuridica", "fonte": "diritto.it", "url": "https://www.diritto.it/feed/"},
    {"nome": "FiscoOggi — Agenzia Entrate", "tipo": "circolare", "fonte": "fiscooggi.it", "url": "https://www.fiscooggi.it/rss.xml"},
    {"nome": "Altalex — Fisco", "tipo": "notizia_fiscale", "fonte": "altalex.com", "url": "https://www.altalex.com/feed/fisco"},
    {"nome": "Altalex — Lavoro", "tipo": "notizia_lavoro", "fonte": "altalex.com", "url": "https://www.altalex.com/feed/lavoro"},
    {"nome": "Altalex — Società", "tipo": "notizia_societa", "fonte": "altalex.com", "url": "https://www.altalex.com/feed/societa"},
    {"nome": "Altalex — Civile", "tipo": "notizia_civile", "fonte": "altalex.com", "url": "https://www.altalex.com/feed/civile"},
    {"nome": "La Legge Per Tutti — Fisco", "tipo": "notizia_fiscale", "fonte": "laleggepertutti.it", "url": "https://www.laleggepertutti.it/feed"},
    {"nome": "EUR-Lex — Gazzetta UE", "tipo": "normativa_europea", "fonte": "eur-lex.europa.eu", "url": "https://eur-lex.europa.eu/rss/rss-oj-l.xml"},
    {"nome": "Europarl — Normativa EU", "tipo": "normativa_europea", "fonte": "europarl.europa.eu", "url": "https://www.europarl.europa.eu/rss/doc/top-stories/it.xml"},
]

# ============================================================
# FASE 2 — PAGINE STATICHE (scaricate una volta e aggiornate)
# ============================================================
PAGINE_STATICHE = [

    # ── INPS ──────────────────────────────────────────────
    {"titolo": "INPS — Aliquote contributive artigiani e commercianti 2024", "tipo": "previdenza", "fonte": "inps.it", "url": "https://www.inps.it/it/it/dettaglio-scheda.schede-servizio-e-prestazioni.50545.aliquote-e-massimale-contributivo-per-artigiani-e-commercianti.html"},
    {"titolo": "INPS — Gestione separata aliquote 2024", "tipo": "previdenza", "fonte": "inps.it", "url": "https://www.inps.it/it/it/dettaglio-scheda.schede-servizio-e-prestazioni.50546.aliquote-e-massimale-per-iscritti-alla-gestione-separata.html"},
    {"titolo": "INPS — Cassa integrazione guadagni CIG", "tipo": "previdenza", "fonte": "inps.it", "url": "https://www.inps.it/it/it/dettaglio-scheda.schede-servizio-e-prestazioni.50048.cassa-integrazione-guadagni-ordinaria-cigo-.html"},
    {"titolo": "INPS — Pensione anticipata e di vecchiaia", "tipo": "previdenza", "fonte": "inps.it", "url": "https://www.inps.it/it/it/dettaglio-scheda.schede-servizio-e-prestazioni.50048.pensione-anticipata.html"},
    {"titolo": "INPS — Naspi disoccupazione", "tipo": "previdenza", "fonte": "inps.it", "url": "https://www.inps.it/it/it/dettaglio-scheda.schede-servizio-e-prestazioni.50048.naspi.html"},
    {"titolo": "INPS — Maternità e paternità", "tipo": "previdenza", "fonte": "inps.it", "url": "https://www.inps.it/it/it/dettaglio-scheda.schede-servizio-e-prestazioni.50048.indennita-di-maternita-paternita.html"},
    {"titolo": "INPS — TFR Trattamento di fine rapporto", "tipo": "previdenza", "fonte": "inps.it", "url": "https://www.inps.it/it/it/dettaglio-scheda.schede-servizio-e-prestazioni.50048.tfr.html"},
    {"titolo": "INPS — Bonus 100 euro ex bonus Renzi", "tipo": "previdenza", "fonte": "inps.it", "url": "https://www.inps.it/it/it/dettaglio-scheda.schede-servizio-e-prestazioni.50048.trattamento-integrativo.html"},

    # ── INAIL ─────────────────────────────────────────────
    {"titolo": "INAIL — Premi e tariffe assicurative", "tipo": "previdenza", "fonte": "inail.it", "url": "https://www.inail.it/cs/internet/atti-e-documenti/note-e-provvedimenti/delibere-cda/tariffe.html"},
    {"titolo": "INAIL — Infortuni sul lavoro denuncia", "tipo": "previdenza", "fonte": "inail.it", "url": "https://www.inail.it/cs/internet/home/cosa-fa-l-inail/assicurazione/denuncia-infortuni.html"},

    # ── AGENZIA ENTRATE ───────────────────────────────────
    {"titolo": "Agenzia Entrate — Guida dichiarazione 730", "tipo": "dichiarazione", "fonte": "agenziaentrate.gov.it", "url": "https://www.agenziaentrate.gov.it/portale/web/guest/schede/dichiarazioni/730/guida-730"},
    {"titolo": "Agenzia Entrate — Guida IVA", "tipo": "iva", "fonte": "agenziaentrate.gov.it", "url": "https://www.agenziaentrate.gov.it/portale/web/guest/schede/iva/guida-iva"},
    {"titolo": "Agenzia Entrate — Regime forfettario", "tipo": "dichiarazione", "fonte": "agenziaentrate.gov.it", "url": "https://www.agenziaentrate.gov.it/portale/web/guest/schede/dichiarazioni/regime-forfetario/info-gen-regime-forfetario"},
    {"titolo": "Agenzia Entrate — Ravvedimento operoso", "tipo": "adempimento", "fonte": "agenziaentrate.gov.it", "url": "https://www.agenziaentrate.gov.it/portale/web/guest/schede/pagamenti/ravvedimento-operoso/info-ravvedimento"},
    {"titolo": "Agenzia Entrate — IMU istruzioni", "tipo": "tributo_locale", "fonte": "agenziaentrate.gov.it", "url": "https://www.agenziaentrate.gov.it/portale/web/guest/schede/pagamenti/imu"},
    {"titolo": "Agenzia Entrate — Successioni e donazioni", "tipo": "successioni", "fonte": "agenziaentrate.gov.it", "url": "https://www.agenziaentrate.gov.it/portale/web/guest/schede/successioni-e-donazioni"},
    {"titolo": "Agenzia Entrate — Registro imposta", "tipo": "imposta_registro", "fonte": "agenziaentrate.gov.it", "url": "https://www.agenziaentrate.gov.it/portale/web/guest/schede/registrazione-atti/imposta-di-registro"},
    {"titolo": "Agenzia Entrate — F24 istruzioni generali", "tipo": "adempimento", "fonte": "agenziaentrate.gov.it", "url": "https://www.agenziaentrate.gov.it/portale/web/guest/schede/pagamenti/f24"},

    # ── WIKILABOUR — CCNL ─────────────────────────────────
    {"titolo": "CCNL Agenti di assicurazione ANAPA UNAPASS", "tipo": "ccnl", "fonte": "wikilabour.it", "url": "https://www.wikilabour.it/dizionario/ccnl/agenti-assicurazione/"},
    {"titolo": "CCNL Assicurazioni ANIA", "tipo": "ccnl", "fonte": "wikilabour.it", "url": "https://www.wikilabour.it/dizionario/ccnl/assicurazioni/"},
    {"titolo": "CCNL Commercio Terziario Confcommercio", "tipo": "ccnl", "fonte": "wikilabour.it", "url": "https://www.wikilabour.it/dizionario/ccnl/commercio/"},
    {"titolo": "CCNL Metalmeccanici Industria Federmeccanica", "tipo": "ccnl", "fonte": "wikilabour.it", "url": "https://www.wikilabour.it/dizionario/ccnl/metalmeccanici-industria/"},
    {"titolo": "CCNL Edilizia Industria", "tipo": "ccnl", "fonte": "wikilabour.it", "url": "https://www.wikilabour.it/dizionario/ccnl/edilizia-industria/"},
    {"titolo": "CCNL Studi Professionali", "tipo": "ccnl", "fonte": "wikilabour.it", "url": "https://www.wikilabour.it/dizionario/ccnl/studi-professionali/"},
    {"titolo": "CCNL Turismo e Pubblici Esercizi", "tipo": "ccnl", "fonte": "wikilabour.it", "url": "https://www.wikilabour.it/dizionario/ccnl/turismo-pubblici-esercizi/"},
    {"titolo": "CCNL Trasporti e Logistica", "tipo": "ccnl", "fonte": "wikilabour.it", "url": "https://www.wikilabour.it/dizionario/ccnl/trasporti-logistica/"},
    {"titolo": "CCNL Agricoltura", "tipo": "ccnl", "fonte": "wikilabour.it", "url": "https://www.wikilabour.it/dizionario/ccnl/agricoltura/"},
    {"titolo": "CCNL Chimici Industria", "tipo": "ccnl", "fonte": "wikilabour.it", "url": "https://www.wikilabour.it/dizionario/ccnl/chimici-industria/"},
    {"titolo": "CCNL Tessile Abbigliamento", "tipo": "ccnl", "fonte": "wikilabour.it", "url": "https://www.wikilabour.it/dizionario/ccnl/tessile-abbigliamento/"},
    {"titolo": "CCNL Alimentari Industria", "tipo": "ccnl", "fonte": "wikilabour.it", "url": "https://www.wikilabour.it/dizionario/ccnl/alimentari-industria/"},
    {"titolo": "CCNL Bancari ABI", "tipo": "ccnl", "fonte": "wikilabour.it", "url": "https://www.wikilabour.it/dizionario/ccnl/bancari-abi/"},
    {"titolo": "CCNL Credito Cooperativo", "tipo": "ccnl", "fonte": "wikilabour.it", "url": "https://www.wikilabour.it/dizionario/ccnl/credito-cooperativo/"},
    {"titolo": "CCNL Cooperative Sociali", "tipo": "ccnl", "fonte": "wikilabour.it", "url": "https://www.wikilabour.it/dizionario/ccnl/cooperative-sociali/"},
    {"titolo": "CCNL Sanita Privata", "tipo": "ccnl", "fonte": "wikilabour.it", "url": "https://www.wikilabour.it/dizionario/ccnl/sanita-privata/"},
    {"titolo": "CCNL Scuola Privata", "tipo": "ccnl", "fonte": "wikilabour.it", "url": "https://www.wikilabour.it/dizionario/ccnl/scuola-privata/"},
    {"titolo": "CCNL Artigianato", "tipo": "ccnl", "fonte": "wikilabour.it", "url": "https://www.wikilabour.it/dizionario/ccnl/artigianato/"},
    {"titolo": "CCNL Legno Arredamento", "tipo": "ccnl", "fonte": "wikilabour.it", "url": "https://www.wikilabour.it/dizionario/ccnl/legno-arredamento/"},
    {"titolo": "CCNL Gomma Plastica", "tipo": "ccnl", "fonte": "wikilabour.it", "url": "https://www.wikilabour.it/dizionario/ccnl/gomma-plastica/"},
    {"titolo": "CCNL Carta Cartone", "tipo": "ccnl", "fonte": "wikilabour.it", "url": "https://www.wikilabour.it/dizionario/ccnl/carta-cartone/"},
    {"titolo": "CCNL Poligrafici Editoriali", "tipo": "ccnl", "fonte": "wikilabour.it", "url": "https://www.wikilabour.it/dizionario/ccnl/poligrafici-editoriali/"},
    {"titolo": "CCNL Pulizie Multiservizi", "tipo": "ccnl", "fonte": "wikilabour.it", "url": "https://www.wikilabour.it/dizionario/ccnl/pulizie-multiservizi/"},
    {"titolo": "CCNL Vigilanza Privata", "tipo": "ccnl", "fonte": "wikilabour.it", "url": "https://www.wikilabour.it/dizionario/ccnl/vigilanza-privata/"},
    {"titolo": "CCNL Telecomunicazioni", "tipo": "ccnl", "fonte": "wikilabour.it", "url": "https://www.wikilabour.it/dizionario/ccnl/telecomunicazioni/"},
    {"titolo": "CCNL Energia Petrolio", "tipo": "ccnl", "fonte": "wikilabour.it", "url": "https://www.wikilabour.it/dizionario/ccnl/energia-petrolio/"},
    {"titolo": "CCNL Farmaceutici Industria", "tipo": "ccnl", "fonte": "wikilabour.it", "url": "https://www.wikilabour.it/dizionario/ccnl/farmaceutici-industria/"},
    {"titolo": "CCNL Elettrici", "tipo": "ccnl", "fonte": "wikilabour.it", "url": "https://www.wikilabour.it/dizionario/ccnl/elettrici/"},
    {"titolo": "CCNL Distribuzione Moderna Organizzata", "tipo": "ccnl", "fonte": "wikilabour.it", "url": "https://www.wikilabour.it/dizionario/ccnl/distribuzione-moderna-organizzata/"},

    # ── NORMATTIVA — Codici e leggi fondamentali ──────────
    {"titolo": "TUIR — Testo Unico Imposte sui Redditi DPR 917/1986", "tipo": "normativa", "fonte": "normattiva.it", "url": "https://www.normattiva.it/uri-res/N2Ls?urn:nir:stato:decreto.del.presidente.della.repubblica:1986-12-22;917"},
    {"titolo": "DPR 633/1972 — Istituzione IVA", "tipo": "normativa", "fonte": "normattiva.it", "url": "https://www.normattiva.it/uri-res/N2Ls?urn:nir:stato:decreto.del.presidente.della.repubblica:1972-10-26;633"},
    {"titolo": "Codice Civile — Libro V Lavoro e Società", "tipo": "normativa", "fonte": "normattiva.it", "url": "https://www.normattiva.it/uri-res/N2Ls?urn:nir:stato:regio.decreto:1942-03-16;262~art2060"},
    {"titolo": "Statuto dei Lavoratori L. 300/1970", "tipo": "normativa", "fonte": "normattiva.it", "url": "https://www.normattiva.it/uri-res/N2Ls?urn:nir:stato:legge:1970-05-20;300"},
    {"titolo": "D.Lgs 81/2015 Jobs Act contratti di lavoro", "tipo": "normativa", "fonte": "normattiva.it", "url": "https://www.normattiva.it/uri-res/N2Ls?urn:nir:stato:decreto.legislativo:2015-06-15;81"},
    {"titolo": "D.Lgs 231/2001 Responsabilità amministrativa enti", "tipo": "normativa", "fonte": "normattiva.it", "url": "https://www.normattiva.it/uri-res/N2Ls?urn:nir:stato:decreto.legislativo:2001-06-08;231"},

    # ── ORDINE COMMERCIALISTI ─────────────────────────────
    {"titolo": "CNDCEC — Principi deontologici commercialisti", "tipo": "deontologia", "fonte": "cndcec.it", "url": "https://www.cndcec.it/Home/Deontologia/"},
    {"titolo": "CNDCEC — Notizie e comunicati", "tipo": "notizia_professionale", "fonte": "cndcec.it", "url": "https://www.cndcec.it/Home/News/"},

    # ── MEF — MINISTERO ECONOMIA ──────────────────────────
    {"titolo": "MEF — Dichiarazione dei redditi istruzioni", "tipo": "dichiarazione", "fonte": "finanze.gov.it", "url": "https://www.finanze.gov.it/it/fiscalita-nazionale/dichiarazioni-e-adempimenti/"},
    {"titolo": "MEF — Fiscalità internazionale", "tipo": "fiscalita_internazionale", "fonte": "finanze.gov.it", "url": "https://www.finanze.gov.it/it/fiscalita-internazionale/"},

    # ── CAMERA DI COMMERCIO ───────────────────────────────
    {"titolo": "Unioncamere — Registro imprese e adempimenti", "tipo": "adempimento_societario", "fonte": "unioncamere.it", "url": "https://www.unioncamere.gov.it/"},
    {"titolo": "InfoCamere — Guida iscrizione registro imprese", "tipo": "adempimento_societario", "fonte": "infocamere.it", "url": "https://www.infocamere.it/web/guest/registro-imprese"},

    # ── FONDAZIONE OIC ────────────────────────────────────
    {"titolo": "OIC — Principi contabili nazionali", "tipo": "principi_contabili", "fonte": "fondazioneoic.eu", "url": "https://www.fondazioneoic.eu/?page_id=3097"},
    {"titolo": "OIC 9 — Svalutazione delle immobilizzazioni", "tipo": "principi_contabili", "fonte": "fondazioneoic.eu", "url": "https://www.fondazioneoic.eu/?page_id=3097"},

    # ── GUARDIA DI FINANZA ────────────────────────────────
    {"titolo": "GdF — Accertamento fiscale e verifiche", "tipo": "contenzioso", "fonte": "gdf.gov.it", "url": "https://www.gdf.gov.it/it/attivita/entrate-erariali"},

    # ── AGENZIA DELLE ENTRATE — RISCOSSIONE ───────────────
    {"titolo": "Agenzia Riscossione — Cartelle esattoriali", "tipo": "riscossione", "fonte": "agenziariscossione.gov.it", "url": "https://www.agenziaentrate.gov.it/portale/web/guest/schede/pagamenti/cartelle-esattoriali"},
    {"titolo": "Agenzia Riscossione — Rateizzazione debiti", "tipo": "riscossione", "fonte": "agenziariscossione.gov.it", "url": "https://www.agenziaentrate.gov.it/portale/web/guest/schede/pagamenti/rateizzazione"},
    {"titolo": "Agenzia Riscossione — Rottamazione cartelle", "tipo": "riscossione", "fonte": "agenziariscossione.gov.it", "url": "https://www.agenziaentrate.gov.it/portale/web/guest/schede/pagamenti/rottamazione"},
]

# ============================================================
# FUNZIONI
# ============================================================

def genera_id(url, titolo):
    return hashlib.md5(f"{url}{titolo}".encode()).hexdigest()

def doc_esiste(id_univoco):
    try:
        r = requests.get(
            DB_URL,
            headers={**HEADERS_DB, "Prefer": ""},
            params={"id_univoco": f"eq.{id_univoco}", "select": "id"},
            timeout=10
        )
        return len(r.json()) > 0
    except:
        return False

def scarica_testo(url):
    try:
        r = requests.get(url, headers=BROWSER, timeout=20)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "header", "aside", "form"]):
            tag.decompose()
        testo = soup.get_text(separator="\n", strip=True)
        return testo[:10000]
    except Exception as e:
        return ""

def salva_documento(doc):
    try:
        r = requests.post(DB_URL, headers=HEADERS_DB, json=doc, timeout=10)
        return r.status_code in [200, 201]
    except:
        return False

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
            testo = scarica_testo(url)
            contenuto = f"{sommario}\n\n{testo}".strip()

            doc = {
                "id_univoco": id_univoco,
                "titolo": titolo[:500],
                "tipo": fonte["tipo"],
                "fonte": fonte["fonte"],
                "data_pubblicazione": data_pub,
                "contenuto": contenuto,
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
    tipo = pagina["tipo"]
    fonte = pagina["fonte"]

    id_univoco = genera_id(url, titolo)
    if doc_esiste(id_univoco):
        print(f"  ⏭ Già presente: {titolo[:55]}...")
        return 0

    time.sleep(2)
    testo = scarica_testo(url)

    if not testo or len(testo) < 150:
        print(f"  ⚠ Testo non disponibile: {titolo[:55]}...")
        return 0

    doc = {
        "id_univoco": id_univoco,
        "titolo": titolo,
        "tipo": tipo,
        "fonte": fonte,
        "data_pubblicazione": datetime.now().strftime("%Y-%m-%d"),
        "contenuto": testo,
        "url_fonte": url,
        "creato_il": datetime.now().isoformat()
    }

    if salva_documento(doc):
        print(f"  ✅ {titolo[:65]}... ({len(testo)} car.)")
        return 1
    else:
        print(f"  ❌ Errore salvataggio: {titolo[:55]}...")
        return 0

def main():
    print("=" * 65)
    print("🔍 LexFisco Crawler — Versione completa per commercialisti")
    print(f"⏰ {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    print("=" * 65)

    # FASE 1 — Feed RSS notizie
    print("\n📰 FASE 1 — Notizie giuridiche e fiscali aggiornate")
    print("-" * 65)
    tot_rss = sum(crawla_rss(f) for f in FONTI_RSS)
    time.sleep(2)

    # FASE 2 — Pagine statiche (CCNL, INPS, norme, ecc.)
    print(f"\n📋 FASE 2 — Documenti statici ({len(PAGINE_STATICHE)} fonti)")
    print("-" * 65)

    categorie = {}
    for p in PAGINE_STATICHE:
        categorie.setdefault(p["tipo"], []).append(p)

    tot_statici = 0
    for categoria, pagine in categorie.items():
        print(f"\n  📂 {categoria.upper().replace('_',' ')} ({len(pagine)} doc)")
        for pagina in pagine:
            tot_statici += crawla_pagina(pagina)

    print("\n" + "=" * 65)
    print(f"✅ Crawling completato!")
    print(f"📰 Notizie nuove:     {tot_rss}")
    print(f"📋 Documenti statici: {tot_statici}")
    print(f"📚 Totale:            {tot_rss + tot_statici}")
    print("=" * 65)

if __name__ == "__main__":
    main()

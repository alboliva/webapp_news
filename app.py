import streamlit as st
import feedparser
from dateutil import parser as dateparser
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

# --- CONFIGURAZIONE PARAMETRICA ---
APP_TITLE = "Notizie RSS – Ieri & Oggi" 
ITEMS_PER_PAGE = 25
MAX_ITEMS_PER_FEED = 40
CACHE_MINUTES = 10

RSS_FEEDS = [
    ("New York Times USA",      "https://rss.nytimes.com/services/xml/rss/nyt/US.xml",       "NYT USA"),
    ("New York Times World",    "https://rss.nytimes.com/services/xml/rss/nyt/World.xml",    "NYT WORLD"),
    ("New York Times Business", "https://rss.nytimes.com/services/xml/rss/nyt/Business.xml", "NYT BSN"),
    ("Google News IT",          "https://news.google.it/news/rss",                          "GNews"),
    ("Repubblica",              "https://www.repubblica.it/rss/homepage/rss2.0.xml",          "Rep"),
    ("Il Messaggero",           "https://www.ilmessaggero.it/?sez=XML&p=search&args[box]=Home&limit=20&layout=rss", "Mess"),
    ("ANSA Generale",           "https://www.ansa.it/sito/ansait_rss.xml",                  "ANSA"),
    ("ANSA Economia",           "https://www.ansa.it/sito/notizie/economia/economia_rss.xml", "ANSA Eco"),
    ("Sole 24 Ore Politica",    "https://www.ilsole24ore.com/rss/italia--politica.xml",      "S24 Politica"),
    ("Sole 24 Ore USA",         "https://www.ilsole24ore.com/rss/mondo--usa.xml",            "S24 USA"),
    ("Il Post",                 "https://www.ilpost.it/feed",                               "Il Post"),
    ("First Online",            "https://www.firstonline.info/feed",                        "First"),
]

# --- FUNZIONI DI RECUPERO ---
def fetch_one_rss(feed_tuple):
    display_name, url, short_label = feed_tuple
    try:
        feed = feedparser.parse(url, agent='Mozilla/5.0')
        news = []
        cutoff = datetime.now() - timedelta(days=1)
        for entry in feed.entries[:MAX_ITEMS_PER_FEED]:
            if hasattr(entry, 'published'):
                pub = dateparser.parse(entry.published).replace(tzinfo=None)
                if pub >= cutoff:
                    news.append({
                        'time': pub,
                        'source': short_label,
                        'display_source': display_name,
                        'title': entry.title.strip(),
                        'link': entry.get('link', '#')
                    })
        return news
    except: return []

@st.cache_data(ttl=60 * CACHE_MINUTES, show_spinner=False)
def load_all_news():
    all_news = []
    with ThreadPoolExecutor(max_workers=12) as ex:
        futures = [ex.submit(fetch_one_rss, f) for f in RSS_FEEDS]
        for future in as_completed(futures): all_news.extend(future.result())
    all_news.sort(key=lambda x: x['time'], reverse=True)
    return all_news

# --- INTERFACCIA UTENTE ---
st.set_page_config(layout="wide", page_title=APP_TITLE)
st.title(f"🗞️ {APP_TITLE}")

# Layout: Sinistra per Notizie, Destra per Filtri
main_col, side_col = st.columns([7, 2.5], gap="large")

# Caricamento dati
all_data = load_all_news()

with side_col:
    st.subheader("⚙️ Fonti")
    # Pulsanti di massa
    c_all, c_none = st.columns(2)
    if c_all.button("✅ Tutti", use_container_width=True):
        for _, _, s in RSS_FEEDS: st.session_state[f"chk_{s}"] = True
        st.rerun()
    if c_none.button("❌ Nessuno", use_container_width=True):
        for _, _, s in RSS_FEEDS: st.session_state[f"chk_{s}"] = False
        st.rerun()

    st.write("---")
    active_sources = set()
    for name, _, short in RSS_FEEDS:
        if st.checkbox(name, value=st.session_state.get(f"chk_{short}", True), key=f"chk_{short}"):
            active_sources.add(short)
    
    st.write("---")
    st.subheader("💾 Esporta")
    
    # Preparazione dati per export
    search_term = st.session_state.get("search_input", "").lower()
    filtered_for_download = [n for n in all_data if n['source'] in active_sources and search_term in n['title'].lower()]
    
    if filtered_for_download:
        text_content = f"REPORT NOTIZIE - {datetime.now().strftime('%d/%m/%Y %H:%M')}\n"
        text_content += "="*60 + "\n\n"
        
        for n in filtered_for_download:
            line = f"[{n['time'].strftime('%d/%m %H:%M')}] {n['display_source'].upper()}\n"
            line += f"TITOLO: {n['title']}\n"
            line += f"LINK: {n['link']}\n"
            line += "-"*40 + "\n"
            text_content += line

        st.download_button(
            label="📥 Scarica Notizie (.txt)",
            data=text_content,
            file_name=f"notizie_rss_{datetime.now().strftime('%Y%m%d_%H%M')}.txt",
            mime="text/plain",
            use_container_width=True
        )
    else:
        st.info("Nessuna notizia da scaricare.")

with main_col:
    # Barra superiore: Ricerca e Refresh
    r_search, r_btn = st.columns([5, 1.5])
    search = r_search.text_input("🔍 Cerca nel titolo", key="search_input").lower()
    
    r_btn.markdown('<div style="margin-top:28px;"></div>', unsafe_allow_html=True)
    if r_btn.button("↻ Aggiorna", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    filtered = [n for n in all_data if n['source'] in active_sources and search in n['title'].lower()]

    # Paginazione
    total = len(filtered)
    pages = max(1, (total + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE)
    if 'current_page' not in st.session_state: st.session_state.current_page = 1
    if st.session_state.current_page > pages: st.session_state.current_page = 1

    p_prev, p_info, p_next = st.columns([1, 2, 1])
    if p_prev.button("◀ Prec") and st.session_state.current_page > 1:
        st.session_state.current_page -= 1
        st.rerun()
    p_info.markdown(f"<p style='text-align:center; padding-top:5px'>Pagina <b>{st.session_state.current_page}</b> di {pages} ({total} notizie)</p>", unsafe_allow_html=True)
    if p_next.button("Succ ▶") and st.session_state.current_page < pages:
        st.session_state.current_page += 1
        st.rerun()

    # --- TABELLA NOTIZIE (LAYOUT UNIFORME) ---
    st.markdown("---")
    h1, h2, h3 = st.columns([1.2, 2.0, 6.8])
    h1.write("**Data / Ora**")
    h2.write("**Fonte**")
    h3.write("**Titolo**")
    st.divider()

    with st.container():
        start = (st.session_state.current_page - 1) * ITEMS_PER_PAGE
        end = start + ITEMS_PER_PAGE
        
        for n in filtered[start:end]:
            ora = n['time'].strftime("%H:%M")
            data = n['time'].strftime("%d/%m")
            
            r_col1, r_col2, r_col3 = st.columns([1.2, 2.0, 6.8])
            
            # Layout Data e Ora
            r_col1.markdown(f"<span style='color:gray; font-size:0.9em'>{data} {ora}</span>", unsafe_allow_html=True)
            
            # Layout Fonte (NYT e testate italiane uniformate)
            r_col2.markdown(f"<span style='color:#e63946; font-weight:bold'>{n['display_source']}</span>", unsafe_allow_html=True)
            
            # Layout Titolo
            r_col3.markdown(f"[{n['title']}]({n['link']})")
            
            st.markdown('<div style="margin-top:-10px; border-bottom:1px solid #f0f0f0"></div>', unsafe_allow_html=True)

    st.caption(f"Ultimo aggiornamento: {time.strftime('%H:%M:%S')}")
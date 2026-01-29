import streamlit as st
import feedparser
from dateutil import parser as dateparser
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

# ─── CONFIGURAZIONE PARAMETRICA ──────────────────────────────────────────
APP_TITLE = "Notizie RSS – Ieri & Oggi"  # <--- Modifica questo per il titolo
ITEMS_PER_PAGE = 25
MAX_ITEMS_PER_FEED = 40
CACHE_MINUTES = 10

RSS_FEEDS = [
    ("Google News IT",          "https://news.google.it/news/rss",                 "GNews"),
    ("Repubblica",              "https://www.repubblica.it/rss/homepage/rss2.0.xml", "Rep"),
    ("Il Messaggero",           "https://www.ilmessaggero.it/?sez=XML&p=search&args[box]=Home&limit=20&layout=rss", "Mess"),
    ("ANSA Generale",           "https://www.ansa.it/sito/ansait_rss.xml",         "ANSA"),
    ("ANSA Economia",           "https://www.ansa.it/sito/notizie/economia/economia_rss.xml", "ANSA Eco"),
    ("Sole 24 Ore Politica",    "https://www.ilsole24ore.com/rss/italia--politica.xml", "S24 Politica"),
    ("Sole 24 Ore USA",         "https://www.ilsole24ore.com/rss/mondo--usa.xml",   "S24 USA"),
    ("Il Post",                 "https://www.ilpost.it/feed",                      "Il Post"),
    ("First Online",            "https://www.firstonline.info/feed",               "First"),
]

# ─── LOGICA STATO INIZIALE ──────────────────────────────────────────
if 'active_src' not in st.session_state:
    st.session_state.active_src = {short: True for _, _, short in RSS_FEEDS}

# ─── FUNZIONI ──────────────────────────────────────────────────────────
def normalize_time(dt):
    if dt.tzinfo: return dt.astimezone().replace(tzinfo=None)
    return dt

def fetch_one_rss(feed_tuple):
    display_name, url, short_label = feed_tuple
    try:
        feed = feedparser.parse(url, agent='Mozilla/5.0')
        news = []
        cutoff = datetime.now() - timedelta(days=1)
        for entry in feed.entries[:MAX_ITEMS_PER_FEED]:
            if hasattr(entry, 'published'):
                try:
                    pub = normalize_time(dateparser.parse(entry.published))
                    if pub >= cutoff:
                        news.append({
                            'time': pub,
                            'source': short_label,
                            'display_source': display_name,
                            'title': entry.title.strip(),
                            'link': entry.get('link', '#')
                        })
                except: pass
        return news
    except: return []

@st.cache_data(ttl=60 * CACHE_MINUTES, show_spinner=False)
def load_all_news():
    all_news = []
    with ThreadPoolExecutor(max_workers=10) as ex:
        futures = [ex.submit(fetch_one_rss, feed) for feed in RSS_FEEDS]
        for future in as_completed(futures):
            all_news.extend(future.result())
    all_news.sort(key=lambda x: x['time'], reverse=True)
    seen, unique = set(), []
    for n in all_news:
        key = (n['title'][:70], n['link'][:70])
        if key not in seen:
            seen.add(key)
            unique.append(n)
    return unique

# ─── APP UI ───────────────────────────────────────────────────────────
st.set_page_config(layout="wide", page_title=APP_TITLE)
st.title(APP_TITLE)

# Layout: 7/10 Notizie (Sinistra), 3/10 Filtri (Destra)
main_col, side_col = st.columns([7, 3], gap="large")

with side_col:
    st.subheader("⚙️ Filtri Sorgenti")
    
    c1, c2 = st.columns(2)
    if c1.button("✅ Seleziona tutte", use_container_width=True):
        for _, _, short in RSS_FEEDS: st.session_state[f"chk_{short}"] = True
        st.rerun()
    if c2.button("❌ Deseleziona", use_container_width=True):
        for _, _, short in RSS_FEEDS: st.session_state[f"chk_{short}"] = False
        st.rerun()

    st.write("")
    active_sources = set()
    for disp_name, _, short in RSS_FEEDS:
        if st.checkbox(disp_name, value=True, key=f"chk_{short}"):
            active_sources.add(short)

with main_col:
    # --- RIGA DI RICERCA E AGGIORNAMENTO ALLINEATA ---
    # Usiamo 3 colonne: Ricerca (Larga), Spazio vuoto, Bottone (Stretta)
    ctrl_col1, ctrl_col2 = st.columns([5, 1])
    
    with ctrl_col1:
        search = st.text_input("🔍 Cerca nel titolo", placeholder="Scrivi per filtrare...", label_visibility="visible").strip().lower()
    
    with ctrl_col2:
        # Markdown per creare spazio sopra il bottone e allinearlo alla text box
        st.markdown('<div style="margin-top:28px;"></div>', unsafe_allow_html=True)
        if st.button("↻ Refresh", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

    all_news = load_all_news()

    # Filtri
    filtered = [n for n in all_news if n['source'] in active_sources]
    if search:
        filtered = [n for n in filtered if search in n['title'].lower()]

    # Paginazione
    total = len(filtered)
    pages = max(1, (total + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE)
    if 'current_page' not in st.session_state or st.session_state.current_page > pages:
        st.session_state.current_page = 1

    # Navigation bar
    p_prev, p_info, p_next = st.columns([1, 2, 1])
    if p_prev.button("◀ Prec") and st.session_state.current_page > 1:
        st.session_state.current_page -= 1
        st.rerun()
    p_info.markdown(f"<div style='text-align: center; padding-top: 5px;'>Pagina <b>{st.session_state.current_page}</b> di {pages}</div>", unsafe_allow_html=True)
    if p_next.button("Succ ▶") and st.session_state.current_page < pages:
        st.session_state.current_page += 1
        st.rerun()

    # Tabella HTML
    start_idx = (st.session_state.current_page - 1) * ITEMS_PER_PAGE
    page_news = filtered[start_idx : start_idx + ITEMS_PER_PAGE]

    html = '''
    <div style="height:600px; overflow-y:auto; border:1px solid #ddd; border-radius:8px; padding:15px; background:#fff;">
      <div style="display:grid; grid-template-columns: 80px 140px 1fr; font-weight:bold; border-bottom:2px solid #eee; padding-bottom:10px; margin-bottom:10px;">
        <div>Ora</div><div>Fonte</div><div>Titolo</div>
      </div>
    '''
    for n in page_news:
        t = n['time'].strftime("%H:%M")
        src = n['display_source'][:15]
        html += f'''
      <div style="display:grid; grid-template-columns: 80px 140px 1fr; padding:8px 0; border-bottom:1px solid #f9f9f9; align-items:center;">
        <div style="color:#888; font-size:13px;">{t}</div>
        <div style="color:#007bff; font-weight:bold; font-size:13px;">{src}</div>
        <div><a href="{n['link']}" target="_blank" style="color:#333; text-decoration:none; font-size:14px;">{n['title']}</a></div>
      </div>
    '''
    html += '</div>'
    st.markdown(html, unsafe_allow_html=True)
import streamlit as st
import feedparser
from dateutil import parser as dateparser
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

# ─── CONFIGURAZIONE ─────────────────────────────────────────────────────

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
    # Aggiungi qui altre fonti se vuoi
]

ITEMS_PER_PAGE = 25
MAX_ITEMS_PER_FEED = 40
CACHE_MINUTES = 10

# ─── FUNZIONI ──────────────────────────────────────────────────────────

def normalize_time(dt):
    if dt.tzinfo:
        return dt.astimezone().replace(tzinfo=None)
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
                except:
                    pass
        return news
    except:
        return []

@st.cache_data(ttl=60 * CACHE_MINUTES, show_spinner=False)
def load_all_news():
    all_news = []
    with ThreadPoolExecutor(max_workers=10) as ex:
        futures = [ex.submit(fetch_one_rss, feed) for feed in RSS_FEEDS]
        for future in as_completed(futures):
            all_news.extend(future.result())
    
    all_news.sort(key=lambda x: x['time'], reverse=True)
    
    seen = set()
    unique = []
    for n in all_news:
        key = (n['title'][:70], n['link'][:70])
        if key not in seen:
            seen.add(key)
            unique.append(n)
    
    return unique

# ─── STREAMLIT APP ─────────────────────────────────────────────────────

st.title("Notizie RSS – Ieri & Oggi")

# Layout principale
main_col, side_col = st.columns([5, 2])

with main_col:
    # Pulsanti azione
    col1, col2, col3 = st.columns([1, 1, 1])
    with col1:
        if st.button("↑ In cima"):
            st.components.v1.html(
                '<script>parent.document.querySelector("#newsbox").scrollTop=0;</script>',
                height=0
            )
    with col2:
        if st.button("↓ Scorri giù"):
            st.components.v1.html(
                '<script>const b=parent.document.querySelector("#newsbox"); b.scrollTop += b.clientHeight*0.75;</script>',
                height=0
            )
    with col3:
        if st.button("↻ Ricarica dati"):
            st.cache_data.clear()
            st.rerun()

    search = st.text_input("Cerca nel titolo", "").strip().lower()

with side_col:
    st.markdown("**Sorgenti**")
    
    # Inizializzazione stato sorgenti (tutte selezionate di default)
    if 'active_src' not in st.session_state:
        st.session_state.active_src = {short: True for _, _, short in RSS_FEEDS}

    # Pulsanti Seleziona/Deseleziona tutte
    col_all, col_none = st.columns(2)
    with col_all:
        if st.button("Seleziona tutte"):
            for short in st.session_state.active_src:
                st.session_state.active_src[short] = True
            st.rerun()
    with col_none:
        if st.button("Deseleziona tutte"):
            for short in st.session_state.active_src:
                st.session_state.active_src[short] = False
            st.rerun()

    # Checkbox singole (leggono sempre da session_state)
    for disp_name, _, short in RSS_FEEDS:
        st.checkbox(
            disp_name,
            value=st.session_state.active_src[short],
            key=f"chk_{short}",
            on_change=st.rerun  # Forza rerun quando cambi una singola
        )
        # Sincronizza stato
        st.session_state.active_src[short] = st.session_state[f"chk_{short}"]

# ── Caricamento e filtri ──────────────────────────────────────────────

all_news = load_all_news()

active_sources = {short for short, active in st.session_state.active_src.items() if active}
filtered = [n for n in all_news if n['source'] in active_sources]

if search:
    filtered = [n for n in filtered if search in n['title'].lower()]

# Paginazione – reset a pagina 1 se il filtro cambia e page è troppo alta
total = len(filtered)
pages = max(1, (total + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE)

if 'current_page' not in st.session_state:
    st.session_state.current_page = 1

if st.session_state.current_page > pages:
    st.session_state.current_page = 1

page = st.session_state.current_page
start = (page - 1) * ITEMS_PER_PAGE
end = min(start + ITEMS_PER_PAGE, total)

page_news = filtered[start:end]

# Pulsanti paginazione
col_prev, col_info, col_next = st.columns([1, 3, 1])
with col_prev:
    if st.button("◀ Precedente") and page > 1:
        st.session_state.current_page -= 1
        st.rerun()
with col_info:
    st.markdown(f"**Pagina {page} di {pages}** – {total} notizie totali")
with col_next:
    if st.button("Successiva ▶") and page < pages:
        st.session_state.current_page += 1
        st.rerun()

# ── Tabella notizie allineata ────────────────────────────────────────

st.markdown("### Notizie")

html = '''
<div id="newsbox" style="height:620px; overflow-y:auto; border:1px solid #ccc; padding:12px; background:#fdfdfd; font-family:Consolas,monospace; font-size:14px;">
  <div style="display:grid; grid-template-columns: 110px 180px 1fr; font-weight:bold; margin-bottom:8px; padding-bottom:6px; border-bottom:2px solid #aaa;">
    <div>Data/Ora</div>
    <div>Fonte</div>
    <div>Titolo</div>
  </div>
'''

for n in page_news:
    t = n['time'].strftime("%d/%m %H:%M")
    src = n['display_source'][:20]
    title = n['title'].replace('&','&amp;').replace('<','&lt;').replace('"','&quot;')
    html += f'''
  <div style="display:grid; grid-template-columns: 110px 180px 1fr; padding:6px 0; border-bottom:1px solid #eee; align-items:start;">
    <div style="color:#555;">{t}</div>
    <div style="color:#0066cc; font-weight:600;">{src}</div>
    <div><a href="{n['link']}" target="_blank" style="color:#1a0dab; text-decoration:none;">{title}</a></div>
  </div>
'''

html += '</div>'

st.markdown(html, unsafe_allow_html=True)

st.caption(f"Caricamento cache: {len(all_news)} notizie totali • Ultimo refresh: {time.strftime('%H:%M:%S')}")
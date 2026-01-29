import streamlit as st
import feedparser
from dateutil import parser as dateparser
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
from streamlit_autorefresh import st_autorefresh

# --- CONFIGURAZIONE ---
APP_TITLE = "Notizie RSS – Ieri & Oggi" 
ITEMS_PER_PAGE = 25
MAX_ITEMS_PER_FEED = 40
CACHE_MINUTES = 1 

# Lista con MULTI-TAG: (Nome, URL, Acronimo, [Lista Categorie])
RSS_FEEDS = [
    ("NYT USA",      "https://rss.nytimes.com/services/xml/rss/nyt/US.xml",       "NYT USA",   ["AMERICANI", "USA"]),
    ("NYT World",    "https://rss.nytimes.com/services/xml/rss/nyt/World.xml",    "NYT WRD",   ["AMERICANI", "WORLD"]),
    ("NYT Business", "https://rss.nytimes.com/services/xml/rss/nyt/Business.xml", "NYT BSN",   ["AMERICANI", "ECONOMIA"]),
    ("Google News IT", "https://news.google.it/news/rss",                         "GNEWS",     ["ITALIA"]),
    ("Repubblica",    "https://www.repubblica.it/rss/homepage/rss2.0.xml",         "REP",       ["ITALIA"]),
    ("Il Messaggero", "https://www.ilmessaggero.it/?sez=XML&p=search&args[box]=Home&limit=20&layout=rss", "MESS", ["ITALIA"]),
    ("ANSA Generale", "https://www.ansa.it/sito/ansait_rss.xml",                  "ANSA",      ["WORLD", "ITALIA"]),
    ("ANSA Economia", "https://www.ansa.it/sito/notizie/economia/economia_rss.xml", "ANSA ECO", ["ECONOMIA", "ITALIA"]),
    ("S24 Politica",  "https://www.ilsole24ore.com/rss/italia--politica.xml",      "S24 POL",   ["ITALIA", "POLITICA"]),
    ("S24 USA",       "https://www.ilsole24ore.com/rss/mondo--usa.xml",            "S24 USA",   ["WORLD", "ECONOMIA"]),
    ("Yahoo! Finance",       "https://finance.yahoo.com/news/rss",   "Y!BSN",      ["AMERICANI", "ECONOMIA"]),
]

def fetch_one_rss(feed_tuple):
    display_name, url, short_label, categories = feed_tuple
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
                        'source_label': short_label,
                        'title': entry.title.strip(),
                        'link': entry.get('link', '#'),
                        'categories': categories # Ora è una lista
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

# --- UI SETTINGS ---
st.set_page_config(layout="wide", page_title=APP_TITLE)
refresh_count = st_autorefresh(interval=120000, key="data_refresh")

st.markdown("""
    <style>
    [data-testid="stVerticalBlock"] > div { padding-top: 0rem; padding-bottom: 0rem; }
    hr { margin-top: 2px !important; margin-bottom: 2px !important; }
    .truncate-text { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; display: block; width: 100%; }
    div[data-testid="stRadio"] > label { font-size: 14px; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

if 'seen_links' not in st.session_state:
    st.session_state.seen_links = set()
    st.session_state.first_run = True

st.title(f"🗞️ {APP_TITLE}")
main_col, side_col = st.columns([7.8, 2.2], gap="small")
all_data = load_all_news()

current_links = {n['link'] for n in all_data}
if st.session_state.first_run:
    st.session_state.seen_links.update(current_links)
    st.session_state.first_run = False

new_links = current_links - st.session_state.seen_links

with side_col:
    st.subheader("⚙️ Filtri")
    
    # Estrae tutti i tag unici da tutte le liste di categorie
    all_tags = set()
    for f in RSS_FEEDS:
        for tag in f[3]:
            all_tags.add(tag)
    
    tab_labels = ["TUTTE"] + sorted(list(all_tags))
    selected_category = st.radio("Scegli Argomento:", tab_labels, horizontal=True)

    st.write("---")
    
    # Pulsanti selezione rapida filtrati per categoria
    c_all, c_none = st.columns(2)
    if c_all.button("✅ Tutti", use_container_width=True):
        for _, _, s, cats in RSS_FEEDS:
            if selected_category == "TUTTE" or selected_category in cats:
                st.session_state[f"chk_{s}"] = True
        st.rerun()
    if c_none.button("❌ Nessuno", use_container_width=True):
        for _, _, s, cats in RSS_FEEDS:
            if selected_category == "TUTTE" or selected_category in cats:
                st.session_state[f"chk_{s}"] = False
        st.rerun()

    # Checkbox dinamici (mostra se il tag selezionato è nella lista dei tag dell'RSS)
    active_sources = set()
    for name, _, short, cats in RSS_FEEDS:
        if selected_category == "TUTTE" or selected_category in cats:
            if st.checkbox(name, value=st.session_state.get(f"chk_{short}", True), key=f"chk_{short}"):
                active_sources.add(short)
        else:
            if st.session_state.get(f"chk_{short}", True):
                active_sources.add(short)

with main_col:
    r_search, r_btn_clear, r_btn_refresh = st.columns([4, 1.5, 1])
    search = r_search.text_input("🔍 Cerca nel titolo", key="search_input").lower()
    
    r_btn_clear.markdown('<div style="margin-top:28px;"></div>', unsafe_allow_html=True)
    if r_btn_clear.button("✨ Reset colori", use_container_width=True):
        st.session_state.seen_links.update(current_links)
        st.rerun()

    r_btn_refresh.markdown('<div style="margin-top:28px;"></div>', unsafe_allow_html=True)
    if r_btn_refresh.button("↻", use_container_width=True):
        st.cache_data.clear()
        st.session_state.seen_links.update(current_links)
        st.rerun()

    # LOGICA DI FILTRO FINALE (Verifica se il tag selezionato è contenuto nella lista news['categories'])
    filtered_base = [
        n for n in all_data 
        if (selected_category == "TUTTE" or selected_category in n['categories'])
        and n['source_label'] in active_sources 
        and search in n['title'].lower()
    ]
    
    news_new = [n for n in filtered_base if n['link'] in new_links]
    news_old = [n for n in filtered_base if n['link'] not in new_links]
    final_list = news_new + news_old
    
    # EXPORT TXT
    with side_col:
        st.write("---")
        st.subheader("💾 Esporta")
        if final_list:
            text_content = f"REPORT NEWS [{selected_category}] - {datetime.now().strftime('%d/%m/%Y %H:%M')}\n"
            text_content += "="*50 + "\n"
            for n in final_list:
                status = "[NUOVA] " if n['link'] in new_links else ""
                text_content += f"{status}[{n['time'].strftime('%H:%M')}] {n['source_label']}: {n['title']}\n"
            st.download_button("📥 Scarica TXT", data=text_content, file_name=f"news_{selected_category.lower()}.txt", use_container_width=True)

    total_news = len(final_list)
    pages = max(1, (total_news + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE)
    if 'current_page' not in st.session_state: st.session_state.current_page = 1
    
    p_prev, p_info, p_next = st.columns([1, 2, 1])
    if p_prev.button("◀ Prec"): st.session_state.current_page = max(1, st.session_state.current_page - 1); st.rerun()
    p_info.markdown(f"<p style='text-align:center; font-size:13px;'>Pagina <b>{st.session_state.current_page}</b> di {pages}</p>", unsafe_allow_html=True)
    if p_next.button("Succ ▶"): st.session_state.current_page = min(pages, st.session_state.current_page + 1); st.rerun()

    # TABELLA NEWS
    st.markdown("<hr style='border: 1px solid #333'>", unsafe_allow_html=True)
    h1, h2, h3 = st.columns([0.9, 1.0, 8.1]) 
    h1.markdown("<b style='font-size:11px'>Data/Ora</b>", unsafe_allow_html=True)
    h2.markdown("<b style='font-size:11px'>Fonte</b>", unsafe_allow_html=True)
    h3.markdown("<b style='font-size:11px'>Titolo</b>", unsafe_allow_html=True)
    st.markdown("<hr>", unsafe_allow_html=True)

    start = (st.session_state.current_page - 1) * ITEMS_PER_PAGE
    for n in final_list[start : start + ITEMS_PER_PAGE]:
        ora = n['time'].strftime("%H:%M")
        data = n['time'].strftime("%d/%m")
        is_yellow = n['link'] in new_links
        bg_style = "background-color: #fff9c4; border-radius: 2px;" if is_yellow else ""
        
        r_col1, r_col2, r_col3 = st.columns([0.9, 1.0, 8.1])
        r_col1.markdown(f"<div style='margin-bottom:-18px; font-size:0.85em; color:gray; {bg_style}' class='truncate-text'>{data} <b>{ora}</b></div>", unsafe_allow_html=True)
        r_col2.markdown(f"<div style='margin-bottom:-18px; font-size:0.85em; color:#e63946; font-weight:bold; {bg_style}' class='truncate-text'>{n['source_label']}</div>", unsafe_allow_html=True)
        r_col3.markdown(f"<div style='margin-bottom:-18px; font-size:0.95em; {bg_style}' class='truncate-text'><a href='{n['link']}' target='_blank' style='text-decoration:none; color:#1d3557;'>{n['title']}</a></div>", unsafe_allow_html=True)
        st.markdown("<hr style='opacity:0.2'>", unsafe_allow_html=True)

    st.caption(f"Totale: {total_news} | Nuove: {len(new_links)} | Ciclo: {refresh_count}")
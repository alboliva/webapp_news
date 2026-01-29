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

# Lista aggiornata: (Nome, URL, Acronimo, [Tag], Default_Checked)
RSS_FEEDS = [
    ("New York Times USA",      "https://rss.nytimes.com/services/xml/rss/nyt/US.xml",       "NYT USA",      ["AMERICANI", "USA", "STRANIERI"], True),
    ("New York Times World",    "https://rss.nytimes.com/services/xml/rss/nyt/World.xml",    "NYT WORLD",    ["AMERICANI", "WORLD", "STRANIERI"], True),
    ("New York Times Business", "https://rss.nytimes.com/services/xml/rss/nyt/Business.xml", "NYT BSN",      ["AMERICANI", "ECONOMIA", "STRANIERI"], True),
    ("Google News IT",          "https://news.google.it/news/rss",                          "GNEWS",        ["WORLD", "ITALIA"], True),
    ("Repubblica",              "https://www.repubblica.it/rss/homepage/rss2.0.xml",          "REP",          ["WORLD", "ITALIA"], True),
    ("Il Messaggero",           "https://www.ilmessaggero.it/?sez=XML&p=search&args[box]=Home&limit=20&layout=rss", "IL MSGR", ["WORLD", "ITALIA"], True),
    ("ANSA Generale",           "https://www.ansa.it/sito/ansait_rss.xml",                  "ANSA",         ["WORLD", "ITALIA"], True),
    ("ANSA Economia",           "https://www.ansa.it/sito/notizie/economia/economia_rss.xml", "ANSA ECO",     ["ECONOMIA", "ITALIA"], True),
    ("Il Sole 24 Ore USA",      "https://www.ilsole24ore.com/rss/mondo--usa.xml",            "S24 USA",      ["WORLD", "ECONOMIA"], True),
    ("Washington Post World",   "https://feeds.washingtonpost.com/rss/world",               "WAPO WORLD",   ["AMERICANI", "WORLD", "STRANIERI"], True),
    ("The Guardian",            "https://feeds.washingtonpost.com/rss/business",            "GUARDIAN",     ["INGLESI", "WORLD", "STRANIERI"], True),
    ("Al Jazeera",              "http://www.aljazeera.com/xml/rss/all.xml",                 "ALJAZEERA",    ["ARABI", "WORLD", "STRANIERI"], False),
    ("Hong Kong World",         "https://www.scmp.com/rss/92/feed/",                        "HK_WORLD",     ["CINESI", "WORLD", "STRANIERI"], False),
    ("The Japan Times",         "https://www.japantimes.co.jp/feed/",                       "JAP TIMES",    ["GIAPPONESI", "WORLD", "STRANIERI"], False),
]

def fetch_one_rss(feed_tuple):
    # Spacchettamento a 5 valori (il quinto lo ignoriamo qui perché serve alla UI)
    display_name, url, short_label, categories, _ = feed_tuple
    try:
        feed = feedparser.parse(url, agent='Mozilla/5.0')
        news = []
        cutoff = datetime.now() - timedelta(days=1)
        for entry in feed.entries[:MAX_ITEMS_PER_FEED]:
            date_str = entry.get('published', entry.get('pubDate', None))
            if date_str:
                pub = dateparser.parse(date_str).replace(tzinfo=None)
                if pub >= cutoff:
                    news.append({
                        'time': pub,
                        'source_label': short_label,
                        'title': entry.title.strip(),
                        'link': entry.get('link', '#'),
                        'categories': categories
                    })
        return news
    except: return []

@st.cache_data(ttl=60 * CACHE_MINUTES, show_spinner=False)
def load_all_news():
    all_news = []
    with ThreadPoolExecutor(max_workers=15) as ex:
        futures = [ex.submit(fetch_one_rss, f) for f in RSS_FEEDS]
        for future in as_completed(futures): all_news.extend(future.result())
    all_news.sort(key=lambda x: x['time'], reverse=True)
    return all_news

# --- INTERFACCIA ---
st.set_page_config(layout="wide", page_title=APP_TITLE)
st_autorefresh(interval=60000, key="data_refresh")

if 'seen_links' not in st.session_state:
    st.session_state.seen_links = set()
    st.session_state.first_run = True

# Inizializzazione dei checkbox basata sul valore di default in RSS_FEEDS
for _, _, short, _, default_val in RSS_FEEDS:
    key = f"chk_{short}"
    if key not in st.session_state:
        st.session_state[key] = default_val

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
    
    all_tags = set()
    for f in RSS_FEEDS:
        for tag in f[3]: all_tags.add(tag)
    
    tab_labels = ["TUTTE"] + sorted(list(all_tags))
    selected_category = st.radio("Argomento:", tab_labels, horizontal=True)

    st.write("---")
    
    c_all, c_none = st.columns(2)
    if c_all.button("✅ Tutti", use_container_width=True):
        for _, _, s, cats, _ in RSS_FEEDS:
            if selected_category == "TUTTE" or selected_category in cats:
                st.session_state[f"chk_{s}"] = True
        st.rerun()
    if c_none.button("❌ Nessuno", use_container_width=True):
        for _, _, s, cats, _ in RSS_FEEDS:
            if selected_category == "TUTTE" or selected_category in cats:
                st.session_state[f"chk_{s}"] = False
        st.rerun()

    active_sources = set()
    for name, _, short, cats, _ in RSS_FEEDS:
        key = f"chk_{short}"
        if selected_category == "TUTTE" or selected_category in cats:
            # Il checkbox usa lo stato salvato in session_state
            if st.checkbox(name, key=key):
                active_sources.add(short)
        else:
            # Se è nascosto, lo consideriamo attivo solo se il suo stato è True
            if st.session_state.get(key, False):
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

    filtered_base = [
        n for n in all_data 
        if (selected_category == "TUTTE" or selected_category in n['categories'])
        and n['source_label'] in active_sources 
        and search in n['title'].lower()
    ]
    
    news_new = [n for n in filtered_base if n['link'] in new_links]
    news_old = [n for n in filtered_base if n['link'] not in new_links]
    final_list = news_new + news_old
    
    # EXPORT
    with side_col:
        st.write("---")
        st.subheader("💾 Esporta")
        if final_list:
            text_content = f"REPORT NEWS [{selected_category}] - {datetime.now().strftime('%d/%m/%Y %H:%M')}\n"
            for n in final_list:
                status = "[NUOVA] " if n['link'] in new_links else ""
                text_content += f"{status}[{n['time'].strftime('%H:%M')}] {n['source_label']}: {n['title']}\n"
            st.download_button("📥 Scarica TXT", data=text_content, file_name=f"news_{selected_category.lower()}.txt", use_container_width=True)

    # TABELLA NEWS
    st.markdown("<hr style='border: 1px solid #333'>", unsafe_allow_html=True)
    h1, h2, h3 = st.columns([0.9, 1.0, 8.1]) 
    h1.write("**Data**")
    h2.write("**Fonte**")
    h3.write("**Titolo**")
    
    start = (st.session_state.get('current_page', 1) - 1) * ITEMS_PER_PAGE
    for n in final_list[start : start + ITEMS_PER_PAGE]:
        ora = n['time'].strftime("%H:%M")
        data = n['time'].strftime("%d/%m")
        is_yellow = n['link'] in new_links
        bg = "background-color: #fff9c4;" if is_yellow else ""
        
        c1, c2, c3 = st.columns([0.9, 1.0, 8.1])
        c1.markdown(f"<div style='{bg} font-size:0.85em; color:gray;'>{data} <b>{ora}</b></div>", unsafe_allow_html=True)
        c2.markdown(f"<div style='{bg} font-size:0.85em; color:#e63946; font-weight:bold;'>{n['source_label']}</div>", unsafe_allow_html=True)
        c3.markdown(f"<div style='{bg} font-size:0.95em;'><a href='{n['link']}' target='_blank' style='text-decoration:none; color:#1d3557;'>{n['title']}</a></div>", unsafe_allow_html=True)
        st.markdown("<hr style='margin: 0; opacity: 0.1;'>", unsafe_allow_html=True)

    st.caption(f"News: {len(final_list)} | Nuove: {len(new_links)}")
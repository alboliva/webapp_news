import streamlit as st
import feedparser
from dateutil import parser as dateparser
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
from streamlit_autorefresh import st_autorefresh

# --- CONFIGURAZIONE COSTANTI ---
APP_TITLE = "Notizie RSS – Ieri & Oggi" 
MAX_ITEMS_PER_FEED = 40
CACHE_MINUTES = 2 
INITIAL_DISPLAY = 50 
INCREMENT_DISPLAY = 50 

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
    ("The Guardian",            "https://feeds.theguardian.com/theguardian/world/rss",      "GUARDIAN",     ["INGLESI", "WORLD", "STRANIERI"], True),
    ("Al Jazeera",              "http://www.aljazeera.com/xml/rss/all.xml",                 "ALJAZEERA",    ["ARABI", "WORLD", "STRANIERI"], False),
    ("Hong Kong World",         "https://www.scmp.com/rss/92/feed/",                        "HK_WORLD",     ["CINESI", "WORLD", "STRANIERI"], False),
    ("The Japan Times",         "https://www.japantimes.co.jp/feed/",                       "JAP TIMES",    ["GIAPPONESI", "WORLD", "STRANIERI"], False),
    ("Yahoo! Finance",          "https://finance.yahoo.com/news/rss",                       "Y!BSN",        ["AMERICANI", "ECONOMIA", "STRANIERI"], True),
]

def fetch_one_rss(feed_tuple):
    display_name, url, short_label, categories, _ = feed_tuple
    try:
        agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        feed = feedparser.parse(url, agent=agent)
        news = []
        cutoff = datetime.now() - timedelta(days=1)
        for entry in feed.entries[:MAX_ITEMS_PER_FEED]:
            date_str = entry.get('published', entry.get('pubDate', None))
            if date_str:
                try:
                    pub = dateparser.parse(date_str).replace(tzinfo=None)
                    if pub >= cutoff:
                        news.append({
                            'time': pub,
                            'source_label': short_label,
                            'title': entry.title.strip(),
                            'link': entry.get('link', '#'),
                            'categories': categories
                        })
                except: continue
        return news
    except: return []

@st.cache_data(ttl=60 * CACHE_MINUTES, show_spinner="Sincronizzazione feed...")
def load_all_news():
    all_news = []
    with ThreadPoolExecutor(max_workers=25) as ex:
        futures = [ex.submit(fetch_one_rss, f) for f in RSS_FEEDS]
        for future in as_completed(futures):
            all_news.extend(future.result())
    all_news.sort(key=lambda x: x['time'], reverse=True)
    return all_news

# --- LOGICA CALLBACK ---
def on_category_change():
    """Reset limit e auto-check delle fonti coerenti col radio button."""
    st.session_state.display_limit = INITIAL_DISPLAY
    cat = st.session_state.main_radio_cat
    for _, _, short, cats, _ in RSS_FEEDS:
        if cat == "TUTTE" or cat in cats:
            st.session_state[f"chk_{short}"] = True

# --- INIZIALIZZAZIONE SESSION STATE ---
if 'seen_links' not in st.session_state:
    st.session_state.seen_links = set()
    st.session_state.first_run = True
if 'display_limit' not in st.session_state:
    st.session_state.display_limit = INITIAL_DISPLAY

# Inizializzazione checkbox per ogni feed
for _, _, short, _, default_val in RSS_FEEDS:
    key = f"chk_{short}"
    if key not in st.session_state:
        st.session_state[key] = default_val

# --- INTERFACCIA ---
st.set_page_config(layout="wide", page_title=APP_TITLE)
st_autorefresh(interval=120000, key="data_refresh")

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
    all_tags = sorted(list(set(tag for f in RSS_FEEDS for tag in f[3])))
    
    selected_category = st.radio(
        "Argomento:", 
        ["TUTTE"] + all_tags, 
        horizontal=True, 
        key="main_radio_cat",
        on_change=on_category_change
    )

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
        # Mostriamo il checkbox solo se appartiene alla categoria selezionata
        if selected_category == "TUTTE" or selected_category in cats:
            if st.checkbox(name, key=key):
                active_sources.add(short)
        else:
            # Se è nascosto, lo consideriamo attivo per il filtraggio solo se era True
            if st.session_state.get(key, False):
                active_sources.add(short)

with main_col:
    r_search, r_btn_clear, r_btn_refresh = st.columns([4, 1.5, 1.2])
    search = r_search.text_input("🔍 Cerca...", key="search_input").lower()
    
    if r_btn_clear.button("✨ Reset colori", use_container_width=True):
        st.session_state.seen_links.update(current_links)
        st.rerun()
    if r_btn_refresh.button("↻ Aggiorna", use_container_width=True):
        st.cache_data.clear()
        st.session_state.display_limit = INITIAL_DISPLAY
        st.rerun()

    # Applica i filtri
    filtered = [n for n in all_data if (selected_category == "TUTTE" or selected_category in n['categories']) 
                and n['source_label'] in active_sources and search in n['title'].lower()]
    
    news_new = [n for n in filtered if n['link'] in new_links]
    news_old = [n for n in filtered if n['link'] not in new_links]
    final_list = news_new + news_old

    st.markdown("<hr style='border: 1px solid #333; margin: 10px 0;'>", unsafe_allow_html=True)
    
    visible_list = final_list[:st.session_state.display_limit]
    
    for n in visible_list:
        ora, data = n['time'].strftime("%H:%M"), n['time'].strftime("%d/%m")
        is_new = n['link'] in new_links
        bg = "background-color: #fff9c4;" if is_new else ""
        
        c1, c2, c3 = st.columns([0.8, 1.2, 8.0])
        c1.markdown(f"<div style='{bg} font-size:0.8em; color:gray; line-height:1.1;'>{data}<br><b>{ora}</b></div>", unsafe_allow_html=True)
        c2.markdown(f"<div style='{bg} font-size:0.8em; color:#e63946; font-weight:bold;'>{n['source_label']}</div>", unsafe_allow_html=True)
        c3.markdown(f"<div style='{bg} font-size:0.95em;'><a href='{n['link']}' target='_blank' style='text-decoration:none; color:#1d3557;'>{n['title']}</a></div>", unsafe_allow_html=True)
        st.markdown("<hr style='margin: 0; opacity: 0.1;'>", unsafe_allow_html=True)

    if len(final_list) > st.session_state.display_limit:
        if st.button(f"👇 Mostra altre {INCREMENT_DISPLAY} notizie", use_container_width=True):
            st.session_state.display_limit += INCREMENT_DISPLAY
            st.rerun()

    st.caption(f"News: {len(final_list)} | Visualizzate: {len(visible_list)} | Nuove: {len(new_links)}")

    with side_col:
        st.write("---")
        if final_list:
            text = f"REPORT NEWS - {selected_category}\n" + "="*30 + "\n"
            text += "\n".join([f"[{n['time'].strftime('%H:%M')}] {n['source_label']}: {n['title']}" for n in final_list])
            st.download_button("📥 Scarica Report", data=text, file_name=f"news_{selected_category.lower()}.txt", use_container_width=True)
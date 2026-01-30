import streamlit as st
import feedparser
from dateutil import parser as dateparser
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
from streamlit_autorefresh import st_autorefresh

# --- CONFIGURAZIONE COSTANTI ---
APP_TITLE = "Notizie RSS – Ieri & Oggi" 
MAX_ITEMS_PER_FEED = 40
CACHE_MINUTES = 2 
ITEMS_PER_PAGE = 30 

RSS_FEEDS = [
    ("New York Times USA",      "https://rss.nytimes.com/services/xml/rss/nyt/US.xml",       "NYT USA",      ["AMERICANI", "USA", "STRANIERI"], True),
    ("New York Times World",    "https://rss.nytimes.com/services/xml/rss/nyt/World.xml",    "NYT WORLD",    ["AMERICANI", "WORLD", "STRANIERI"], True),
    ("New York Times Business", "https://rss.nytimes.com/services/xml/rss/nyt/Business.xml", "NYT BSN",      ["AMERICANI", "ECONOMIA", "STRANIERI"], True),
    ("Google News IT",          "https://news.google.it/news/rss",                          "GNEWS",        ["WORLD", "ITALIA"], True),
    ("Repubblica",              "https://www.repubblica.it/rss/homepage/rss2.0.xml",          "REP",          ["WORLD", "ITALIA"], True),
    ("Il Messaggero",           "https://www.ilmessaggero.it/?sez=XML&p=search&args[box]=Home&limit=20&layout=rss", "IL MSGR", ["WORLD", "ITALIA"], True),
    ("CorSera",                 "https://xml2.corriereobjects.it/feed-hp/homepage.xml", "CORR", ["WORLD", "ITALIA"], True),
    ("CorSera (Economia)",      "https://www.corriere.it/dynamic-feed/rss/section/Economia.xml", "CORR ECO", ["ECONOMIA", "ITALIA"], True),
    ("CorSera (Politica)",      "https://www.corriere.it/dynamic-feed/rss/section/Politica.xml", "CORR POLITICA", ["POLITICA", "ITALIA"], True),
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

# --- FUNZIONI CORE ---
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

@st.cache_data(ttl=60 * CACHE_MINUTES, show_spinner="Sincronizzazione...")
def load_all_news():
    all_news = []
    with ThreadPoolExecutor(max_workers=25) as ex:
        futures = [ex.submit(fetch_one_rss, f) for f in RSS_FEEDS]
        for future in as_completed(futures):
            all_news.extend(future.result())
    all_news.sort(key=lambda x: x['time'], reverse=True)
    return all_news

# --- CALLBACKS ---
def on_radio_change():
    st.session_state.current_page = 1
    cat = st.session_state.main_cat

    if cat == "TUTTE":
        for _, _, short, _, _ in RSS_FEEDS:
            st.session_state[f"chk_{short}"] = True
    else:
        for _, _, short, cats, _ in RSS_FEEDS:
            if cat in cats:
                st.session_state[f"chk_{short}"] = True
            # Gli altri rimangono come erano prima (non forziamo False)

def reset_pagination():
    st.session_state.current_page = 1

# --- INIZIALIZZAZIONE ---
if 'seen_links' not in st.session_state: 
    st.session_state.seen_links = set()
if 'first_run' not in st.session_state: 
    st.session_state.first_run = True
if 'current_page' not in st.session_state: 
    st.session_state.current_page = 1

# Checkbox partono dai valori indicati in RSS_FEEDS (ultimo elemento della tupla)
for _, _, short, _, default_val in RSS_FEEDS:
    key = f"chk_{short}"
    if key not in st.session_state:
        st.session_state[key] = default_val

# Imposta categoria iniziale se non esiste
if "main_cat" not in st.session_state:
    st.session_state.main_cat = "TUTTE"

# --- INTERFACCIA ---
st.set_page_config(layout="wide", page_title=APP_TITLE)
st_autorefresh(interval=120000, key="refresh_global")

st.markdown("""
    <style>
    [data-testid="stVerticalBlock"] > div { padding-top: 0rem; padding-bottom: 0rem; }
    .news-row { font-size: 0.92em; line-height: 1.6; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
    button { height: 42px !important; }
    div[data-testid="stRadio"] label { font-size: 13px !important; }
    </style>
    """, unsafe_allow_html=True)

st.title(f"🗞️ {APP_TITLE}")
main_col, side_col = st.columns([8.2, 1.8], gap="small")

all_data = load_all_news()
current_links = {n['link'] for n in all_data}
if st.session_state.first_run:
    st.session_state.seen_links.update(current_links)
    st.session_state.first_run = False
new_links = current_links - st.session_state.seen_links

with side_col:
    st.subheader("⚙️ Fonti")
    
    active_sources = set()
    sel_cat = st.session_state.get("main_cat", "TUTTE")
    
    for name, _, short, cats, _ in RSS_FEEDS:
        if sel_cat == "TUTTE" or sel_cat in cats:
            if st.checkbox(name, key=f"chk_{short}"):
                active_sources.add(short)

            
    # Pulsante download
    if st.button("⬇️ Scarica filtrate", use_container_width=True):
        print (active_sources)
        filtered = [n for n in all_data 
                    if n['source_label'] in active_sources 
                    and st.session_state.get("search_in", "").lower() in n['title'].lower()]
        final_list = [n for n in filtered if n['link'] in new_links] + \
                     [n for n in filtered if n['link'] not in new_links]
                     
        if final_list:
            lines = []
            lines.append(f"Notizie filtrate – {datetime.now().strftime('%Y-%m-%d %H:%M')}")
            lines.append(f"Totale: {len(final_list)}")
            lines.append(f"Categoria: {st.session_state.get('main_cat', 'TUTTE')}")
            lines.append(f"Ricerca: '{st.session_state.get('search_in', '')}'" if st.session_state.get("search_in") else "Nessuna ricerca")
            lines.append("-" * 70)
            
            for n in final_list:
                time_str = n['time'].strftime("%d/%m/%Y %H:%M")
                stato = "NUOVA" if n['link'] in new_links else "letta"
                lines.append(f"[{time_str}] {n['source_label']} – {stato}")
                lines.append(n['title'])
                lines.append(n['link'])
                lines.append("")
            
            content = "\n".join(lines)
            st.download_button(
                label="Download TXT",
                data=content,
                file_name=f"notizie_{datetime.now().strftime('%Y%m%d_%H%M')}.txt",
                mime="text/plain"
            )
        else:
            st.info("Nessuna notizia da scaricare al momento.")

    st.write("---")
    
    # active_sources = set()
    # sel_cat = st.session_state.get("main_cat", "TUTTE")
    
    # for name, _, short, cats, _ in RSS_FEEDS:
    #     if sel_cat == "TUTTE" or sel_cat in cats:
    #         if st.checkbox(name, key=f"chk_{short}"):
    #             active_sources.add(short)

with main_col:
    # 1. CATEGORIE
    all_tags = sorted(list(set(tag for f in RSS_FEEDS for tag in f[3])))
    st.radio(
        "Seleziona Categoria:", 
        ["TUTTE"] + all_tags, 
        horizontal=True, 
        key="main_cat", 
        on_change=on_radio_change,
        label_visibility="collapsed"
    )

    # 2. CONTROLLI
    ctrl_1, ctrl_2, ctrl_3, ctrl_4, ctrl_5, ctrl_6 = st.columns([3.5, 1, 1, 0.8, 1, 0.8])
    
    search = ctrl_1.text_input("🔍 Cerca...", key="search_in", on_change=reset_pagination, label_visibility="collapsed").lower()
    
    if ctrl_2.button("✨ Letto", use_container_width=True):
        st.session_state.seen_links.update(current_links)
        st.rerun()
    if ctrl_3.button("↻ Aggiorna", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    filtered = [n for n in all_data if n['source_label'] in active_sources and search in n['title'].lower()]
    final_list = [n for n in filtered if n['link'] in new_links] + [n for n in filtered if n['link'] not in new_links]
    
    total_results = len(final_list)
    total_pages = max(1, (total_results + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE)

    # Navigazione
    if ctrl_4.button("◀", disabled=st.session_state.current_page == 1, use_container_width=True):
        st.session_state.current_page -= 1
        st.rerun()
    ctrl_5.markdown(f"<p style='text-align:center; margin-top:5px; font-size:0.9em;'>{st.session_state.current_page}/{total_pages}</p>", unsafe_allow_html=True)
    if ctrl_6.button("▶", disabled=st.session_state.current_page == total_pages, use_container_width=True):
        st.session_state.current_page += 1
        st.rerun()

    st.markdown("<hr style='margin: 5px 0; border: 1px solid #444;'>", unsafe_allow_html=True)

    # 3. RENDER NEWS
    start_idx = (st.session_state.current_page - 1) * ITEMS_PER_PAGE
    for n in final_list[start_idx : start_idx + ITEMS_PER_PAGE]:
        time_str, is_new = n['time'].strftime("%d/%m %H:%M"), n['link'] in new_links
        bg = "background-color: #fff9c4;" if is_new else ""
        c1, c2, c3 = st.columns([1.1, 1.0, 7.9])
        c1.markdown(f"<div class='news-row' style='{bg} color:gray;'>{time_str}</div>", unsafe_allow_html=True)
        c2.markdown(f"<div class='news-row' style='{bg} color:#e63946; font-weight:bold;'>{n['source_label']}</div>", unsafe_allow_html=True)
        c3.markdown(f"<div class='news-row' style='{bg}'><a href='{n['link']}' target='_blank' style='text-decoration:none; color:#1d3557;'>{n['title']}</a></div>", unsafe_allow_html=True)
        st.markdown("<hr style='margin: 0; opacity: 0.1;'>", unsafe_allow_html=True)

    st.caption(f"Mostrate {len(final_list[start_idx:start_idx+ITEMS_PER_PAGE])} notizie | Totali: {total_results}")
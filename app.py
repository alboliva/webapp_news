import streamlit as st
import requests
from bs4 import BeautifulSoup
import feedparser
from dateutil import parser as dateparser
from datetime import datetime, timedelta, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

# ─── CONFIG ────────────────────────────────────────
MAX_WORKERS = 8
CACHE_MINUTES = 8
FINVIZ_MAX_ITEMS = 80
RSS_MAX_ITEMS_PER_FEED = 30

# Fonti disponibili (etichetta mostrata : identificatore fonte)
FONTI = {
    "Finviz News":      "Finviz News",
    "Finviz Blogs":     "Finviz Blogs",
    "Google News":      "GNews",
    "Repubblica":       "Rep",
    "Washington Post":  "Wapo",
    "NYT Business":     "NYT BSN",
    "ANSA":             "ANSA",
    "Sole 24 Ore Politica": "S24 Politica",
    # Aggiungi altre se vuoi
}

SELECTED_RSS = {
    "GNews": ("https://news.google.it/news/rss", "GNews"),
    "Rep": ("https://www.repubblica.it/rss/homepage/rss2.0.xml", "Rep"),
    "Wapo": ("https://feeds.washingtonpost.com/rss/business?itid=lk_inline_manual_32", "Wapo"),
    "NYT BSN": ("https://rss.nytimes.com/services/xml/rss/nyt/Business.xml", "NYT BSN"),
    "ANSA": ("https://www.ansa.it/sito/ansait_rss.xml", "ANSA"),
    "S24 Politica": ("https://www.ilsole24ore.com/rss/italia--politica.xml", "S24 Politica"),
}

# ─── FUNZIONI ──────────────────────────────────────

def normalize_time(dt):
    if dt.tzinfo:
        return dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt

def fetch_finviz(v=1, label='Finviz News'):
    try:
        r = requests.get(f'https://finviz.com/news.ashx?v={v}', headers={'User-Agent': 'Mozilla/5.0'}, timeout=6)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, 'html.parser')
        table = soup.find('table', id='news-table')
        if not table: return []

        news, count = [], 0
        current_date = None
        now = datetime.now()
        yesterday = now - timedelta(days=1)

        for tr in table.find_all('tr'):
            if count >= FINVIZ_MAX_ITEMS: break
            tds = tr.find_all('td')
            if len(tds) == 1 and tds[0].get('align') == 'center':
                current_date = tds[0].text.strip()
            elif len(tds) >= 3:
                time_str = tds[0].text.strip()
                a = tds[2].find('a', class_='nn-tab-link') or tds[2].find('a')
                if a:
                    full_str = f"{current_date} {time_str}" if current_date else time_str
                    try:
                        pub = dateparser.parse(full_str, default=now)
                        if pub > now: pub = pub.replace(year=now.year - 1)
                        pub = normalize_time(pub)
                        if pub.date() >= yesterday.date():
                            news.append({
                                'time': pub,
                                'source': label,
                                'title': a.text.strip(),
                                'link': a['href']
                            })
                            count += 1
                    except:
                        pass
        return news
    except:
        return []

def fetch_one_rss(pair):
    url, label = pair
    try:
        feed = feedparser.parse(url, agent='Mozilla/5.0')
        news, count = [], 0
        yesterday = datetime.now() - timedelta(days=1)
        for e in feed.entries:
            if count >= RSS_MAX_ITEMS_PER_FEED: break
            if hasattr(e, 'published'):
                try:
                    pub = normalize_time(dateparser.parse(e.published))
                    if pub.date() >= yesterday.date():
                        news.append({
                            'time': pub,
                            'source': label,
                            'title': e.title.strip(),
                            'link': e.get('link', '#')
                        })
                        count += 1
                except:
                    pass
        return news
    except:
        return []

@st.cache_data(ttl=60 * CACHE_MINUTES, show_spinner=False)
def collect_all_news():
    all_news = []
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
        futures = [
            ex.submit(fetch_finviz, 1, 'Finviz News'),
            ex.submit(fetch_finviz, 2, 'Finviz Blogs'),
        ]
        for label, pair in SELECTED_RSS.items():
            futures.append(ex.submit(fetch_one_rss, pair))

        for f in as_completed(futures):
            all_news.extend(f.result())

    all_news.sort(key=lambda x: x['time'], reverse=True)

    seen = set()
    unique = []
    for n in all_news:
        key = (n['title'][:60], n['link'][:60])
        if key not in seen:
            seen.add(key)
            unique.append(n)
    return unique

# ─── STREAMLIT APP ─────────────────────────────────

st.title("Notizie Veloci - Oggi e Ieri")

# Layout: notizie al centro/sinistra, checkbox a destra fuori dal box
main_col, sidebar_col = st.columns([5, 2])

with main_col:
    # Pulsanti navigazione
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("↑ Torna in cima"):
            st.components.v1.html("""
            <script>
            const box = parent.document.querySelector('#news-scroll-box');
            if (box) box.scrollTop = 0;
            </script>
            """, height=0)
    with col2:
        if st.button("↓ Scendi di un blocco"):
            st.components.v1.html("""
            <script>
            const box = parent.document.querySelector('#news-scroll-box');
            if (box) box.scrollTop += box.clientHeight * 0.8;
            </script>
            """, height=0)
    with col3:
        if st.button("↻ Aggiorna"):
            st.cache_data.clear()
            st.rerun()

    # Ricerca
    search_text = st.text_input("Cerca nel titolo o fonte:", "").strip().lower()

    # Caricamento dati
    with st.spinner("Caricamento notizie..."):
        all_news = collect_all_news()

    # Filtri
    if 'fonti_selezionate' not in st.session_state:
        st.session_state.fonti_selezionate = {k: True for k in FONTI.keys()}

    fonti_attive = {k for k, v in st.session_state.fonti_selezionate.items() if v}
    filtered_by_source = [n for n in all_news if n['source'] in fonti_attive]

    filtered_final = filtered_by_source
    if search_text:
        filtered_final = [
            n for n in filtered_by_source
            if search_text in n['title'].lower() or search_text in n['source'].lower()
        ]

    # Rendering notizie
    st.markdown(f"**Mostrate: {len(filtered_final)}** su {len(all_news)} totali")

    html = '<div id="news-scroll-box" class="scroll-box">'
    html += '<div><strong>Data Ora   Fonte           Titolo</strong></div><hr>'

    for n in filtered_final:
        t = n['time'].strftime("%d/%m %H:%M")
        s = n['source'][:14].ljust(14)
        title_safe = n['title'].replace('&', '&amp;').replace('<', '&lt;').replace('"', '&quot;')
        html += f'<div class="news-item"><span class="time">{t}</span> <span class="source">{s}</span> '
        html += f'<a href="{n["link"]}" target="_blank" class="title-link">{title_safe}</a></div>'

    html += '</div>'

    st.markdown(html, unsafe_allow_html=True)

with sidebar_col:
    st.markdown("**Seleziona fonti**")
    for fonte in FONTI:
        checked = st.checkbox(
            fonte,
            value=st.session_state.fonti_selezionate[fonte],
            key=f"chk_{fonte}"
        )
        st.session_state.fonti_selezionate[fonte] = checked

# Stile
st.markdown("""
<style>
    .scroll-box {
        height: 620px;
        overflow-y: scroll;
        border: 1px solid #ccc;
        padding: 12px;
        background: #f8f9fa;
        font-family: Consolas, monospace;
        font-size: 14px;
    }
    .news-item {
        margin: 10px 0;
        padding-bottom: 8px;
        border-bottom: 1px solid #eee;
    }
    .time { color: #555; }
    .source { color: #0066cc; font-weight: bold; }
    .title-link { color: #1e40af; text-decoration: none; font-size: 15px; }
    .title-link:hover { text-decoration: underline; color: #1e3a8a; }
</style>
""", unsafe_allow_html=True)

# Auto-scroll (opzionale – commenta la riga scroll() per disattivarlo)
st.markdown("""
<script>
const box = parent.document.querySelector('#news-scroll-box');
if (box) {
    let timer;
    function scroll() {
        box.scrollTop += 1;
        if (box.scrollTop + box.clientHeight >= box.scrollHeight - 5) {
            setTimeout(() => { box.scrollTop = 0; }, 5000);
        }
        timer = setTimeout(scroll, 120);
    }
    // scroll();   // ← commenta questa riga per disattivare lo scroll automatico
}
</script>
""", unsafe_allow_html=True)
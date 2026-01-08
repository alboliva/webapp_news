import streamlit as st
from streamlit_autorefresh import st_autorefresh
from datetime import datetime, date, timedelta
import os

# -------------------------------
# CONFIG
REFRESH_INTERVAL_MS = 300000  # 5 minuti
ARCHIVE_DIR = "archive"
st.set_page_config(page_title="Notizie in Sintesi", layout="wide")

# Crea cartella archive se non esiste
if not os.path.exists(ARCHIVE_DIR):
    os.makedirs(ARCHIVE_DIR)

# Mesi e giorni in italiano
MONTHS_IT = ["Gen", "Feb", "Mar", "Apr", "Mag", "Giu", "Lug", "Ago", "Set", "Ott", "Nov", "Dic"]
WEEKDAYS_IT = ["Lun", "Mar", "Mer", "Gio", "Ven", "Sab", "Dom"]

# Formatta data come "07 Gen, 17.45"
def format_update_time(dt_str):
    try:
        dt = datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S")
        return f"{dt.day:02d} {MONTHS_IT[dt.month-1]}, {dt.hour:02d}.{dt.minute:02d}"
    except:
        return dt_str

# -------------------------------
# Funzione per caricare notizie (robusta)
def load_news(file_path):
    if not os.path.exists(file_path):
        return None

    news_list = []
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            lines = [line.rstrip() for line in f.readlines()]
    except Exception as e:
        st.error(f"Errore lettura file {file_path}: {e}")
        return []

    i = 0
    while i < len(lines):
        while i < len(lines) and not lines[i].strip():
            i += 1
        if i >= len(lines):
            break

        title = lines[i].strip()
        i += 1

        while i < len(lines) and not lines[i].strip():
            i += 1
        if i >= len(lines):
            continue
        image_url = lines[i].strip()
        i += 1

        content_lines = []
        while i < len(lines):
            stripped = lines[i].strip()
            if stripped and not stripped.replace("-", "").replace(":", "").replace(" ", "").isdigit():
                content_lines.append(stripped)
                i += 1
            else:
                break
        content = " ".join(content_lines) if content_lines else "Nessun testo"

        while i < len(lines) and not lines[i].strip():
            i += 1
        if i >= len(lines):
            continue
        update_time = lines[i].strip()
        i += 1

        if not title or not image_url or not update_time:
            continue
        if not image_url.startswith(("http://", "https://")):
            continue

        news_list.append({
            "title": title,
            "image_url": image_url,
            "content": content,
            "update_time": update_time,
            "formatted_time": format_update_time(update_time)
        })

    try:
        news_list.sort(key=lambda x: datetime.strptime(x["update_time"], "%Y-%m-%d %H:%M:%S"), reverse=True)
    except:
        pass

    return news_list

# -------------------------------
# DIALOG / MODAL con layout a due colonne
@st.dialog("Notizia completa", width="large")
def show_full_news(item):
    col_img, col_text = st.columns([3, 2])  # 60% immagine, 40% testo

    with col_img:
        st.image(item["image_url"], use_container_width=True)

    with col_text:
        st.markdown(f"### {item['title']}")
        st.caption(f"Ultimo aggiornamento: {item['formatted_time']}")
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown(item["content"])

# -------------------------------
# SIDEBAR: ultimi 7 giorni + calendario
st.sidebar.title("📅 Navigazione")

today = date.today()

# Inizializza selected_date se non esiste
if "selected_date" not in st.session_state:
    st.session_state.selected_date = today

# Ultimi 7 giorni - con rerun per aggiornare subito
for offset in range(7):
    day_date = today - timedelta(days=offset)
    weekday_it = WEEKDAYS_IT[day_date.weekday()]
    day_str = day_date.day
    month_it = MONTHS_IT[day_date.month - 1]
    label = f"{weekday_it} {day_str:02d} {month_it}"
    if offset == 0:
        label += " (oggi)"

    if st.sidebar.button(label, use_container_width=True, key=f"btn_day_{offset}"):
        st.session_state.selected_date = day_date
        st.rerun()  # Forza aggiornamento immediato

# Calendario
st.sidebar.markdown("---")
cal_date = st.sidebar.date_input(
    "Vai a data specifica",
    value=st.session_state.selected_date,
    max_value=today,
    key="cal_input"
)
if cal_date != st.session_state.selected_date:
    st.session_state.selected_date = cal_date
    st.rerun()

# Data selezionata finale
selected_date = st.session_state.selected_date

# -------------------------------
# Caricamento notizie
if selected_date == today:
    file_path = "news.txt"
    st_autorefresh(interval=REFRESH_INTERVAL_MS, key="autorefresh_home")
else:
    file_path = os.path.join(ARCHIVE_DIR, selected_date.strftime("%Y%m%d") + ".txt")

news = load_news(file_path)

date_display = "oggi" if selected_date == today else selected_date.strftime("%d/%m/%Y")

# -------------------------------
# INTERFACCIA PRINCIPALE
st.title("Notizie in Sintesi")

if news is None:
    st.info(f"📂 Nessun file trovato per {date_display}.")
    st.caption(f"Controlla che esista: `{file_path}`")
elif not news:
    st.info(f"📭 Nessuna notizia valida per {date_display}.")
else:
    max_update_formatted = news[0]["formatted_time"]
    st.caption(f"Ultimo aggiornamento: {max_update_formatted} — {date_display}")

    cols = st.columns(3)
    for idx, item in enumerate(news):
        with cols[idx % 3]:
            with st.container(border=True):
                # Immagine con titolo sovrapposto
                st.image(item["image_url"], use_container_width=True)
                st.markdown(
                    f"<div style='position: relative; margin-top: -70px; padding: 8px 12px; background: rgba(0,0,0,0.7); color: white; border-radius: 0 0 8px 8px;'><b>{item['title']}</b></div>",
                    unsafe_allow_html=True
                )

                st.caption(f"Ultimo aggiornamento: {item['formatted_time']}")

                sintesi = item["content"][:280] + ("..." if len(item["content"]) > 280 else "")
                st.markdown(sintesi)

                if st.button("Leggi tutto", key=f"read_{idx}_{selected_date}"):
                    show_full_news(item)

# Footer
st.sidebar.markdown("---")
st.sidebar.caption("Archivio in /archive")
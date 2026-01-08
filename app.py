import streamlit as st
from streamlit_autorefresh import st_autorefresh
from datetime import datetime, date
import os

# -------------------------------
# CONFIG
REFRESH_INTERVAL_MS = 300000  # 5 minuti
ARCHIVE_DIR = "archive"
st.set_page_config(page_title="Notizie in Sintesi", layout="wide")

# Crea cartella archive se non esiste
if not os.path.exists(ARCHIVE_DIR):
    os.makedirs(ARCHIVE_DIR)

# -------------------------------
# Funzione robusta per caricare notizie
def load_news(file_path):
    if not os.path.exists(file_path):
        return None

    news_list = []
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            lines = [line.rstrip() for line in f.readlines()]  # rimuove \n finali
    except Exception as e:
        st.error(f"Errore lettura file {file_path}: {e}")
        return []

    i = 0
    while i < len(lines):
        # Salta righe vuote
        while i < len(lines) and not lines[i].strip():
            i += 1
        if i >= len(lines):
            break

        title = lines[i].strip()
        i += 1

        # URL immagine
        while i < len(lines) and not lines[i].strip():
            i += 1
        if i >= len(lines):
            continue
        image_url = lines[i].strip()
        i += 1

        # Corpo notizia (può essere su più righe fino a trovare la data)
        content_lines = []
        while i < len(lines) and not lines[i].strip().replace("-", "").replace(":", "").replace(" ", "").isdigit():
            if lines[i].strip():
                content_lines.append(lines[i].strip())
            i += 1
        content = " ".join(content_lines) if content_lines else "Nessun testo"

        # Data/ora ultimo aggiornamento
        while i < len(lines) and not lines[i].strip():
            i += 1
        if i >= len(lines):
            continue
        update_time = lines[i].strip()
        i += 1

        # Validazione
        if not title or not image_url or not update_time:
            continue
        if not image_url.startswith(("http://", "https://")):
            continue  # opzionale: salta URL non validi

        news_list.append({
            "title": title,
            "image_url": image_url,
            "content": content,
            "update_time": update_time
        })

    # Ordina per data decrescente
    try:
        news_list.sort(key=lambda x: datetime.strptime(x["update_time"], "%Y-%m-%d %H:%M:%S"), reverse=True)
    except:
        pass

    return news_list

# -------------------------------
# INTERFACCIA
st.title("Notizie in Sintesi")

today = date.today()
selected_date = st.date_input("Seleziona la data", value=today, max_value=today)

# Percorso file
if selected_date == today:
    file_path = "news.txt"
    st_autorefresh(interval=REFRESH_INTERVAL_MS, key="autorefresh_home")
    date_display = "oggi"
else:
    file_path = os.path.join(ARCHIVE_DIR, selected_date.strftime("%Y%m%d") + ".txt")
    date_display = selected_date.strftime("%d/%m/%Y")

news = load_news(file_path)

if news is None:
    st.info(f"📂 Nessun file trovato per {date_display}.")
    st.caption(f"Controlla che esista: `{file_path}`")
elif not news:
    st.info(f"📭 Nessuna notizia valida trovata per {date_display}.")
    st.caption("Possibile problema di formato nel file.")
else:
    max_update = max(n["update_time"] for n in news)
    st.caption(f"Ultimo aggiornamento: {max_update} — {date_display}")

    cols = st.columns(3)
    for idx, item in enumerate(news):
        with cols[idx % 3]:
            with st.container(border=True):
                st.image(item["image_url"], use_column_width=True)
                st.markdown(f"**{item['title']}**")
                st.caption(f"Ultimo aggiornamento: {item['update_time']}")
                sintesi = item["content"][:280] + ("..." if len(item["content"]) > 280 else "")
                st.markdown(sintesi)

st.sidebar.markdown("---")
st.sidebar.info("""
**Come creare news.txt / file archivio**  
- Una notizia ogni blocco  
- Ordine:  
  1. Titolo  
  2. URL immagine (obbligatorio)  
  3. Testo (anche su più righe)  
  4. Data ora: `2026-01-08 12:30:00`  
- Separa le notizie con una o più righe vuote
""")
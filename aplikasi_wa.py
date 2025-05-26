# WhatsApp Formatter dengan Simpan/Muat Draf ke Google Drive
import streamlit as st
from st_quill import st_quill
import json
import re
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaFileUpload
import io
import os

# Inisialisasi kredensial dari secrets
creds_dict = st.secrets["gdrive"]
folder_id = creds_dict["folder_id"]
creds = service_account.Credentials.from_service_account_info(creds_dict)
drive_service = build("drive", "v3", credentials=creds)

# Fungsi bantu

def html_to_whatsapp(html: str) -> str:
    text = html
    text = re.sub(r'<(b|strong)>(.*?)</\1>', r'*\2*', text)
    text = re.sub(r'<(i|em)>(.*?)</\1>', r'_\2_', text)
    text = re.sub(r'<(s|strike)>(.*?)</\1>', r'~\2~', text)
    text = re.sub(r'<code>(.*?)</code>', r"```\1```", text)
    text = re.sub(r'<[^>]+>', '', text)
    return text.strip()

def list_drafts():
    results = drive_service.files().list(q=f"'{folder_id}' in parents and trashed = false",
        spaces='drive', fields='files(id, name)').execute()
    return results.get('files', [])

def save_draft_to_drive(name: str, content: str):
    existing = [f for f in list_drafts() if f['name'] == name + ".json"]
    body = {"name": name + ".json", "parents": [folder_id]}
    media = MediaFileUpload("temp.json", mimetype="application/json")
    with open("temp.json", "w", encoding="utf-8") as f:
        json.dump({"html": content}, f)
    if existing:
        file_id = existing[0]['id']
        drive_service.files().update(fileId=file_id, media_body=media).execute()
    else:
        drive_service.files().create(body=body, media_body=media).execute()
    os.remove("temp.json")

def load_draft_from_drive(file_id: str) -> str:
    request = drive_service.files().get_media(fileId=file_id)
    fh = io.BytesIO()
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    while done is False:
        status, done = downloader.next_chunk()
    fh.seek(0)
    data = json.load(fh)
    return data.get("html", "")

# UI Streamlit
st.set_page_config(layout="wide", page_title="WhatsApp Formatter Drive")
st.title("📄 WhatsApp Formatter dengan Google Drive")

# Sidebar - Draf
with st.sidebar:
    st.header("💾 Manajemen Draf")
    drafts = list_drafts()
    draft_names = [d['name'].replace(".json", "") for d in drafts]
    selected = st.selectbox("Pilih draf untuk dimuat", ["(Baru)"] + draft_names)
    draft_name = st.text_input("Nama Draf", value="" if selected == "(Baru)" else selected)
    load_btn = st.button("📂 Muat Draf")
    save_btn = st.button("💾 Simpan Draf")

# Editor
if 'html' not in st.session_state:
    st.session_state['html'] = ""

editor = st_quill(value=st.session_state['html'], html=True, key="editor")

# Tindakan
if load_btn and selected != "(Baru)":
    file_id = [d['id'] for d in drafts if d['name'] == selected + ".json"]
    if file_id:
        st.session_state['html'] = load_draft_from_drive(file_id[0])
        st.experimental_rerun()

if save_btn and draft_name:
    st.session_state['html'] = editor
    save_draft_to_drive(draft_name, editor)
    st.success(f"Draf '{draft_name}' berhasil disimpan!")

# Output
st.divider()
st.subheader("📱 Hasil Format WhatsApp")
wa_text = html_to_whatsapp(editor)
st.text_area("Teks Siap Kirim:", wa_text, height=200)

st.markdown("""
<script>
document.querySelector('textarea').addEventListener('focus', function(e) {
  navigator.clipboard.writeText(this.value)
})
</script>
""", unsafe_allow_html=True)

st.caption("Teks otomatis tersalin saat diklik ✨")

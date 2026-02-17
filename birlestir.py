import os
import tempfile
from io import BytesIO
import streamlit as st
from docx import Document
from pypdf import PdfMerger, PdfReader, PdfWriter

st.set_page_config(page_title="Belge Birleştirici", page_icon="📎")

# ---------------------------
# SESSION
# ---------------------------
if "processed_pdfs" not in st.session_state:
    st.session_state.processed_pdfs = {}

if "uploader_keys" not in st.session_state:
    st.session_state.uploader_keys = set()

# ---------------------------
# UI
# ---------------------------
st.title("📎 PDF & Word Birleştirici")

if st.button("♻️ Tam Sıfırla"):
    st.session_state.clear()
    st.rerun()

uploaded_files = st.file_uploader(
    "PDF veya Word yükleyin",
    type=["pdf", "docx"],
    accept_multiple_files=True
)

if not uploaded_files:
    st.info("Dosya yükleyin.")
    st.stop()

# ---------------------------
# SADECE AKTİF DOSYALARI AL
# ---------------------------
current_files = []
current_keys = set()

for i, f in enumerate(uploaded_files):
    key = f"{f.name}_{len(f.getbuffer())}_{i}"
    current_files.append({"key": key, "name": f.name, "file": f})
    current_keys.add(key)

# RAM’de kalan eski processed_pdfs → TEMİZLE
st.session_state.processed_pdfs = {
    k: v for k, v in st.session_state.processed_pdfs.items()
    if k in current_keys
}

st.session_state.uploader_keys = current_keys

# ---------------------------
# PDF SAYFA SİL
# ---------------------------
pdfs = [m for m in current_files if m["name"].lower().endswith(".pdf")]

if pdfs:
    st.subheader("PDF Sayfa Sil")

    names = [m["name"] for m in pdfs]
    choice = st.selectbox("PDF seç", ["Seçiniz"] + names)

    if choice != "Seçiniz":
        meta = next(m for m in pdfs if m["name"] == choice)
        f = meta["file"]

        f.seek(0)
        reader = PdfReader(f)
        total = len(reader.pages)

        labels = [f"Sayfa {i+1}" for i in range(total)]
        delete_pages = st.multiselect("Silinecek sayfalar", labels)

        if st.button("Kaydet"):
            writer = PdfWriter()
            for i in range(total):
                if labels[i] not in delete_pages:
                    writer.add_page(reader.pages[i])

            out = BytesIO()
            writer.write(out)
            out.seek(0)

            st.session_state.processed_pdfs[meta["key"]] = out.getvalue()
            st.success("Kaydedildi")

# ---------------------------
# PDF MERGE (KESİN TEMİZ)
# ---------------------------
st.subheader("PDF Birleştir")

if st.button("PDF'leri Birleştir"):

    merger = PdfMerger()

    for meta in current_files:

        if not meta["name"].lower().endswith(".pdf"):
            continue

        key = meta["key"]

        if key in st.session_state.processed_pdfs:
            merger.append(BytesIO(st.session_state.processed_pdfs[key]))
        else:
            f = meta["file"]
            f.seek(0)
            merger.append(f)

    out = BytesIO()
    merger.write(out)
    merger.close()
    out.seek(0)

    st.success("Birleştirildi")
    st.download_button("PDF indir", out, "merged.pdf")

# ---------------------------
# WORD MERGE
# ---------------------------
st.subheader("Word Birleştir")

if st.button("Word Birleştir"):

    merged = Document()
    first = True

    for meta in current_files:

        if not meta["name"].lower().endswith(".docx"):
            continue

        with tempfile.NamedTemporaryFile(delete=False, suffix=".docx") as tmp:
            tmp.write(meta["file"].getbuffer())
            path = tmp.name

        doc = Document(path)

        if not first:
            merged.add_page_break()

        for p in doc.paragraphs:
            merged.add_paragraph(p.text)

        os.remove(path)
        first = False

    out = BytesIO()
    merged.save(out)
    out.seek(0)

    st.success("Word birleştirildi")
    st.download_button("DOCX indir", out, "merged.docx")

st.caption("Artık geçmiş dosyalar merge edilmez.")

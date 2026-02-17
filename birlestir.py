import os
import tempfile
from io import BytesIO
import streamlit as st
from docx import Document
from pypdf import PdfMerger, PdfReader, PdfWriter

# DOCX->PDF (opsiyonel)
try:
    import docx2pdf
    DOCX2PDF_AVAILABLE = True
except Exception:
    DOCX2PDF_AVAILABLE = False


# ---------------------------
# Session başlangıcı
# ---------------------------
if "processed_pdfs" not in st.session_state:
    st.session_state.processed_pdfs = {}

if "uploaded_meta" not in st.session_state:
    st.session_state.uploaded_meta = []

if "file_fingerprint" not in st.session_state:
    st.session_state.file_fingerprint = None


# ---------------------------
# UI
# ---------------------------
st.set_page_config(page_title="Belge Birleştirici", page_icon="📎")
st.title("📎 PDF & Word Birleştirici")

# RESET BUTONU
if st.button("♻️ Tümünü Sıfırla"):
    st.session_state.processed_pdfs = {}
    st.session_state.uploaded_meta = []
    st.session_state.file_fingerprint = None
    st.rerun()

uploaded_files = st.file_uploader(
    "PDF veya Word yükleyin",
    type=["pdf", "docx"],
    accept_multiple_files=True
)

# ---------------------------
# YENİ YÜKLEME KONTROLÜ
# ---------------------------
if uploaded_files:

    # fingerprint → yükleme değişti mi?
    fingerprint = tuple((f.name, len(f.getbuffer())) for f in uploaded_files)

    if fingerprint != st.session_state.file_fingerprint:
        # TAM TEMİZLİK (kritik)
        st.session_state.processed_pdfs = {}
        st.session_state.uploaded_meta = []
        st.session_state.file_fingerprint = fingerprint

    meta = []
    for i, f in enumerate(uploaded_files):
        key = f"{f.name}_{i}_{len(f.getbuffer())}"
        meta.append({"key": key, "name": f.name, "file": f})

    st.session_state.uploaded_meta = meta


if not st.session_state.uploaded_meta:
    st.info("Dosya yükleyin.")
    st.stop()


# ---------------------------
# PDF SAYFA SİLME
# ---------------------------
pdf_meta = [m for m in st.session_state.uploaded_meta if m["name"].lower().endswith(".pdf")]

if pdf_meta:
    st.subheader("PDF Sayfa Sil")

    pdf_names = [m["name"] for m in pdf_meta]
    choice = st.selectbox("PDF seç", ["Seçiniz"] + pdf_names)

    if choice != "Seçiniz":
        meta = next(m for m in pdf_meta if m["name"] == choice)
        f = meta["file"]

        f.seek(0)
        reader = PdfReader(f)
        total_pages = len(reader.pages)

        pages = [f"Sayfa {i+1}" for i in range(total_pages)]
        delete_pages = st.multiselect("Silinecek sayfalar", pages)

        if st.button("Kaydet"):
            writer = PdfWriter()
            for i in range(total_pages):
                if pages[i] not in delete_pages:
                    writer.add_page(reader.pages[i])

            out = BytesIO()
            writer.write(out)
            out.seek(0)

            st.session_state.processed_pdfs[meta["key"]] = out.getvalue()
            st.success("Kaydedildi")

            st.download_button("İndir", out, f"edited_{meta['name']}")


# ---------------------------
# PDF MERGE (SADECE GÜNCEL DOSYALAR)
# ---------------------------
st.subheader("PDF Birleştir")

if st.button("PDF'leri Birleştir"):

    merger = PdfMerger()
    seen = set()  # duplicate engelle

    for meta in st.session_state.uploaded_meta:

        if not meta["name"].lower().endswith(".pdf"):
            continue

        key = meta["key"]
        if key in seen:
            continue
        seen.add(key)

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

    for meta in st.session_state.uploaded_meta:

        if not meta["name"].lower().endswith(".docx"):
            continue

        with tempfile.NamedTemporaryFile(delete=False, suffix=".docx") as tmp:
            tmp.write(meta["file"].getbuffer())
            tmp_path = tmp.name

        doc = Document(tmp_path)

        if not first:
            merged.add_page_break()

        for p in doc.paragraphs:
            merged.add_paragraph(p.text)

        os.remove(tmp_path)
        first = False

    out = BytesIO()
    merged.save(out)
    out.seek(0)

    st.success("Word birleştirildi")
    st.download_button("DOCX indir", out, "merged.docx")


st.caption("Geçmiş dosyalar

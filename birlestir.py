import os
import tempfile
from io import BytesIO
import streamlit as st
from docx import Document
from pypdf import PdfMerger, PdfReader, PdfWriter

st.set_page_config(page_title="Belge Birleştirici", page_icon="📎")

# ---------------------------
# RESET (Cloud için kritik)
# ---------------------------
if st.button("♻️ Tam Sıfırla (Cloud Cache Temizle)"):
    for k in list(st.session_state.keys()):
        del st.session_state[k]
    st.cache_data.clear()
    st.cache_resource.clear()
    st.rerun()

st.title("📎 PDF & Word Birleştirici")

uploaded_files = st.file_uploader(
    "PDF veya Word (.docx) yükleyin",
    type=["pdf", "docx"],
    accept_multiple_files=True
)

if not uploaded_files:
    st.info("Dosya yükleyin.")
    st.stop()

# ---------------------------
# AKTİF DOSYALARI OKU (HER SEFER)
# ---------------------------
active_files = []
for i, f in enumerate(uploaded_files):

    # merged çıktıyı tekrar merge'e sokma
    if f.name.startswith("merged"):
        continue

    active_files.append({
        "name": f.name,
        "bytes": f.getvalue()
    })

# ---------------------------
# PDF SAYFA SİL
# ---------------------------
pdfs = [f for f in active_files if f["name"].lower().endswith(".pdf")]

if pdfs:
    st.subheader("PDF Sayfa Sil")

    names = [f["name"] for f in pdfs]
    choice = st.selectbox("PDF seç", ["Seçiniz"] + names)

    if choice != "Seçiniz":
        pdf = next(f for f in pdfs if f["name"] == choice)

        reader = PdfReader(BytesIO(pdf["bytes"]))
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

            # Güncel PDF’i RAM’de güncelle
            pdf["bytes"] = out.getvalue()
            st.success("Kaydedildi")

# ---------------------------
# PDF MERGE (SADECE AKTİF)
# ---------------------------
st.subheader("PDF Birleştir")

if st.button("PDF'leri Birleştir"):

    merger = PdfMerger()

    for f in active_files:
        if not f["name"].lower().endswith(".pdf"):
            continue
        merger.append(BytesIO(f["bytes"]))

    out = BytesIO()
    merger.write(out)
    merger.close()
    out.seek(0)

    st.success("Birleştirildi (sadece güncel dosyalar)")
    st.download_button("PDF indir", out, "merged.pdf")

# ---------------------------
# WORD MERGE
# ---------------------------
st.subheader("Word Birleştir")

if st.button("Word Birleştir"):

    merged = Document()
    first = True

    for f in active_files:
        if not f["name"].lower().endswith(".docx"):
            continue

        with tempfile.NamedTemporaryFile(delete=False, suffix=".docx") as tmp:
            tmp.write(f["bytes"])
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

    st.success("Word birleştirildi (sadece güncel dosyalar)")
    st.download_button("DOCX indir", out, "merged.docx")

st.caption("Streamlit Cloud: eski dosyalar artık kesinlikle merge edilmez.")

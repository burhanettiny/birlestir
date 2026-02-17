import os
import tempfile
from io import BytesIO
import streamlit as st
from docx import Document
from pypdf import PdfMerger, PdfReader, PdfWriter

# DOCX->PDF (Windows Word COM)
try:
    import docx2pdf
    DOCX2PDF_AVAILABLE = True
except Exception:
    DOCX2PDF_AVAILABLE = False

# ---------------------------
# Session state başlangıcı
# ---------------------------
if "processed_pdfs" not in st.session_state:
    st.session_state.processed_pdfs = {}
if "uploaded_meta" not in st.session_state:
    st.session_state.uploaded_meta = []

# ---------------------------
# Streamlit UI
# ---------------------------
st.set_page_config(page_title="Belge Birleştirici", page_icon="📎", layout="centered")
st.title("📎 PDF & Word Birleştirici")

# Temizleme Butonu
if st.sidebar.button("🗑️ Tüm Listeyi Temizle"):
    st.session_state.uploaded_meta = []
    st.session_state.processed_pdfs = {}
    st.rerun()

uploaded_files = st.file_uploader(
    "PDF veya Word dosyalarını yükleyin",
    type=["pdf", "docx"],
    accept_multiple_files=True
)

# ---------------------------
# Dosya İşleme Mantığı (GÜNCELLENDİ)
# ---------------------------
if uploaded_files:
    current_keys = [m["key"] for m in st.session_state.uploaded_meta]
    
    for f in uploaded_files:
        # Dosya için benzersiz bir anahtar oluştur (İsim + Boyut)
        file_key = f"{f.name}_{f.size}"
        
        # Eğer bu dosya zaten listede yoksa ekle
        if file_key not in current_keys:
            st.session_state.uploaded_meta.append({
                "key": file_key,
                "name": f.name,
                "file": f
            })

if not st.session_state.uploaded_meta:
    st.info("Başlamak için dosya yükleyin.")
    st.stop()

# ---------------------------
# Sıralama ve PDF Yönetimi
# ---------------------------
st.subheader("🗂️ Dosya Listesi ve Sıralama")
choices = [f'{m["name"]} (ID: {i})' for i, m in enumerate(st.session_state.uploaded_meta)]
sorted_choice = st.multiselect(
    "Birleştirme sırasını belirleyin (Sıralamak için listeden seçin):",
    choices,
    default=choices
)

# Seçim sırasına göre meta veriyi al
ordered_indices = [int(c.split("(ID: ")[-1].strip(")")) for c in sorted_choice]
sorted_meta = [st.session_state.uploaded_meta[i] for i in ordered_indices]

# PDF Düzenleme Bölümü
pdf_meta_list = [m for m in sorted_meta if m["name"].lower().endswith(".pdf")]

if pdf_meta_list:
    st.markdown("---")
    st.subheader("📄 PDF Sayfa Yönetimi")
    pdf_to_edit_name = st.selectbox("Düzenlemek istediğiniz PDF'i seçin", ["Seçiniz"] + [m["name"] for m in pdf_meta_list])
    
    if pdf_to_edit_name != "Seçiniz":
        selected_meta = next(m for m in pdf_meta_list if m["name"] == pdf_to_edit_name)
        uploaded_file = selected_meta["file"]
        
        uploaded_file.seek(0)
        reader = PdfReader(uploaded_file)
        total_pages = len(reader.pages)
        
        st.write(f"**{selected_meta['name']}** - Toplam: {total_pages} sayfa")
        delete_pages = st.multiselect("Silinecek sayfalar", [f"Sayfa {i+1}" for i in range(total_pages)])

        if st.button("📌 Değişiklikleri Uygula"):
            writer = PdfWriter()
            for idx in range(total_pages):
                if f"Sayfa {idx+1}" not in delete_pages:
                    writer.add_page(reader.pages[idx])
            
            out_pdf = BytesIO()
            writer.write(out_pdf)
            st.session_state.processed_pdfs[selected_meta["key"]] = out_pdf.getvalue()
            st.success(f"{selected_meta['name']} güncellendi (Birleştirmede bu hali kullanılacak).")

# ---------------------------
# Birleştirme İşlemleri
# ---------------------------
st.markdown("---")
col1, col2 = st.columns(2)

with col1:
    if st.button("🚀 Sadece PDF'leri Birleştir"):
        merger = PdfMerger()
        for m in sorted_meta:
            if m["name"].lower().endswith(".pdf"):
                content = st.session_state.processed_pdfs.get(m["key"], m["file"].getvalue())
                merger.append(BytesIO(content))
        
        out = BytesIO()
        merger.write(out)
        st.download_button("📥 PDF İndir", out.getvalue(), "birlesmis.pdf", "application/pdf")

with col2:
    if st.button("📝 Sadece Word'leri Birleştir"):
        merged_doc = Document()
        for i, m in enumerate([x for x in sorted_meta if x["name"].lower().endswith(".docx")]):
            if i > 0: merged_doc.add_page_break()
            sub_doc = Document(BytesIO(m["file"].getvalue()))
            for p in sub_doc.paragraphs:
                merged_doc.add_paragraph(p.text)
        
        out = BytesIO()
        merged_doc.save(out)
        st.download_button("📥 Word İndir", out.getvalue(), "birlesmis.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document")
        if st.sidebar.button("🗑️ Tüm Verilerimi Temizle ve Çık"):
    st.session_state.clear() # Tüm session_state'i tek seferde boşaltır
    st.rerun()

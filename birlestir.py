import os
import streamlit as st
from io import BytesIO
from pypdf import PdfMerger, PdfReader, PdfWriter
from docx import Document

# ---------------------------
# Session State Yapılandırması
# ---------------------------
# Düzenlenmiş (sayfa silinmiş) halleri saklamak için
if "processed_pdfs" not in st.session_state:
    st.session_state.processed_pdfs = {}

# ---------------------------
# UI Ayarları
# ---------------------------
st.set_page_config(page_title="PDF & Word Birleştirici", layout="centered")
st.title("📎 Belge Birleştirici")

# Yan Menü
if st.sidebar.button("🗑️ Her Şeyi Sıfırla"):
    st.session_state.processed_pdfs = {}
    st.rerun()

# ---------------------------
# 1. DOSYA YÜKLEME (KRİTİK KISIM)
# ---------------------------
uploaded_files = st.file_uploader(
    "Dosyaları seçin (Yeni ekledikleriniz listeye dahil edilir, listeden sildikleriniz çıkar)",
    type=["pdf", "docx"],
    accept_multiple_files=True
)

# Eğer hiç dosya yoksa temizle ve dur
if not uploaded_files:
    st.session_state.processed_pdfs = {} # Dosyalar silinince düzenlemeleri de temizle
    st.info("Lütfen dosya yükleyin.")
    st.stop()

# Dosyaları benzersiz bir anahtarla (isim + boyut) listeye çeviriyoruz
# Bu sayede mükerrer ekleme (duplicate) imkansız hale geliyor.
current_files_meta = []
for f in uploaded_files:
    f_key = f"{f.name}_{f.size}"
    current_files_meta.append({
        "key": f_key,
        "name": f.name,
        "file": f
    })

# ---------------------------
# 2. SIRALAMA
# ---------------------------
st.subheader("🗂️ Dosya Sıralaması")
file_names = [m["name"] for m in current_files_meta]
sorted_names = st.multiselect(
    "Birleştirme sırasını belirleyin (Veya varsayılan bırakın):",
    options=file_names,
    default=file_names
)

# Seçilen isme göre dosyaları eşleştir (Sıralamayı korumak için)
sorted_meta = []
for name in sorted_names:
    for m in current_files_meta:
        if m["name"] == name:
            sorted_meta.append(m)
            break

# ---------------------------
# 3. PDF SAYFA SİLME
# ---------------------------
pdf_files = [m for m in sorted_meta if m["name"].lower().endswith(".pdf")]

if pdf_files:
    st.markdown("---")
    st.subheader("✂️ PDF'den Sayfa Sil")
    selected_pdf_name = st.selectbox("Düzenlenecek PDF'i seçin", ["Seçiniz"] + [m["name"] for m in pdf_files])
    
    if selected_pdf_name != "Seçiniz":
        # Seçilen dosyayı bul
        target = next(m for m in pdf_files if m["name"] == selected_pdf_name)
        target["file"].seek(0)
        reader = PdfReader(target["file"])
        total_pages = len(reader.pages)
        
        st.write(f"📄 **{selected_pdf_name}** ({total_pages} sayfa)")
        to_delete = st.multiselect("Silinecek sayfalar:", [f"Sayfa {i+1}" for i in range(total_pages)])
        
        if st.button("✂️ Sayfaları Sil ve Birleştirmeye Hazırla"):
            writer = PdfWriter()
            for i in range(total_pages):
                if f"Sayfa {i+1}" not in to_delete:
                    writer.add_page(reader.pages[i])
            
            out = BytesIO()
            writer.write(out)
            # Düzenlenmiş halini belleğe (session_state) kaydet
            st.session_state.processed_pdfs[target["key"]] = out.getvalue()
            st.success("Düzenleme kaydedildi! Birleştirme yaparken bu hali kullanılacak.")

# ---------------------------
# 4. BİRLEŞTİRME
# ---------------------------
st.markdown("---")
st.subheader("🚀 İşlemi Tamamla")

c1, c2 = st.columns(2)

with c1:
    if st.button("🚀 PDF'leri Birleştir", use_container_width=True):
        if not pdf_files:
            st.warning("Hiç PDF dosyası yok!")
        else:
            merger = PdfMerger()
            for m in pdf_files:
                # Düzenlenmiş versiyon var mı? Varsa onu kullan, yoksa orijinali.
                data = st.session_state.processed_pdfs.get(m["key"], m["file"].getvalue())
                merger.append(BytesIO(data))
            
            final_pdf = BytesIO()
            merger.write(final_pdf)
            st.download_button("📥 Birleşmiş PDF'i İndir", final_pdf.getvalue(), "birlesmis.pdf")

with c2:
    docx_files = [m for m in sorted_meta if m["name"].lower().endswith(".docx")]
    if st.button("📝 Word'leri Birleştir", use_container_width=True):
        if not docx_files:
            st.warning("Hiç Word dosyası yok!")
        else:
            merged_docx = Document()
            for i, m in enumerate(docx_files):
                if i > 0: merged_docx.add_page_break()
                sub = Document(BytesIO(m["file"].getvalue()))
                for p in sub.paragraphs:
                    merged_docx.add_paragraph(p.text)
            
            final_docx = BytesIO()
            merged_docx.save(final_docx)
            st.download_button("📥 Birleşmiş Word İndir", final_docx.getvalue(), "birlesmis.docx")

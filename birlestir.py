import streamlit as st
from io import BytesIO
from pypdf import PdfMerger, PdfReader, PdfWriter
from docx import Document

# 1. Oturum Ayarları (Sadece düzenlenen PDF hallerini saklamak için)
if "processed_pdfs" not in st.session_state:
    st.session_state.processed_pdfs = {}

st.set_page_config(page_title="PDF & Word Birleştirici", layout="centered")
st.title("📎 Belge Birleştirici")

# Yan Panel - Sıfırlama
if st.sidebar.button("🗑️ Her Şeyi Sıfırla"):
    st.session_state.processed_pdfs = {}
    st.rerun()

# 2. DOSYA YÜKLEME (Tek Kaynak)
# Burada 'uploaded_files' o an kutuda hangi dosyalar varsa sadece onları tutar.
uploaded_files = st.file_uploader(
    "Dosyaları sürükleyin veya seçin",
    type=["pdf", "docx"],
    accept_multiple_files=True
)

if not uploaded_files:
    st.session_state.processed_pdfs = {} # Kutu boşsa hafızayı temizle
    st.info("Lütfen işlem yapmak için dosya yükleyin.")
    st.stop()

# 3. DOSYA KİMLİKLERİNİ OLUŞTUR (Mükerrer eklemeyi bu engeller)
# Dosyaları isim ve boyutuna göre bir sözlükte tutuyoruz
current_meta = []
for f in uploaded_files:
    f_key = f"{f.name}_{f.size}"
    current_meta.append({"key": f_key, "name": f.name, "file": f})

# ---------------------------------------------------------
# 4. SIRALAMA (Sadece kutudaki dosyaları gösterir)
# ---------------------------------------------------------
st.subheader("🗂️ Birleştirme Sırası")
file_names = [m["name"] for m in current_meta]
sorted_names = st.multiselect(
    "Dosya sırasını değiştirmek için seçin/sürükleyin:",
    options=file_names,
    default=file_names
)

# Seçilen sıraya göre dosyaları listele
sorted_meta = []
for name in sorted_names:
    for m in current_meta:
        if m["name"] == name:
            sorted_meta.append(m)
            break

# ---------------------------------------------------------
# 5. PDF SAYFA SİLME
# ---------------------------------------------------------
pdf_files = [m for m in sorted_meta if m["name"].lower().endswith(".pdf")]

if pdf_files:
    st.markdown("---")
    st.subheader("✂️ PDF Düzenle (Sayfa Sil)")
    selected_pdf_name = st.selectbox("Düzenlenecek PDF:", ["Seçiniz"] + [m["name"] for m in pdf_files])
    
    if selected_pdf_name != "Seçiniz":
        target = next(m for m in pdf_files if m["name"] == selected_pdf_name)
        target["file"].seek(0)
        reader = PdfReader(target["file"])
        total_pages = len(reader.pages)
        
        st.write(f"📄 **{selected_pdf_name}** - Toplam {total_pages} sayfa")
        to_delete = st.multiselect("Silinecek sayfalar:", [f"Sayfa {i+1}" for i in range(total_pages)])
        
        if st.button("✂️ Sayfaları Sil ve Kaydet"):
            writer = PdfWriter()
            for i in range(total_pages):
                if f"Sayfa {i+1}" not in to_delete:
                    writer.add_page(reader.pages[i])
            
            buf = BytesIO()
            writer.write(buf)
            st.session_state.processed_pdfs[target["key"]] = buf.getvalue()
            st.success("Sayfalar silindi. Birleştirmede bu hal kullanılacak.")

# ---------------------------------------------------------
# 6. BİRLEŞTİRME VE İNDİRME
# ---------------------------------------------------------
st.markdown("---")
st.subheader("🚀 Birleştir")

col1, col2 = st.columns(2)

with col1:
    if st.button("🚀 PDF'leri Birleştir", use_container_width=True):
        if not pdf_files:
            st.error("Birleştirilecek PDF bulunamadı.")
        else:
            merger = PdfMerger()
            for m in pdf_files:
                # Düzenlenmiş hali varsa onu, yoksa orijinalini al
                data = st.session_state.processed_pdfs.get(m["key"], m["file"].getvalue())
                merger.append(BytesIO(data))
            
            final_pdf = BytesIO()
            merger.write(final_pdf)
            st.download_button("📥 PDF İndir", final_pdf.getvalue(), "birlesmis_dosyalar.pdf")

with col2:
    docx_files = [m for m in sorted_meta if m["name"].lower().endswith(".docx")]
    if st.button("📝 Word'leri Birleştir", use_container_width=True):
        if not docx_files:
            st.error("Birleştirilecek Word bulunamadı.")
        else:
            merged_docx = Document()
            for i, m in enumerate(docx_files):
                if i > 0: merged_docx.add_page_break()
                sub = Document(BytesIO(m["file"].getvalue()))
                for p in sub.paragraphs:
                    merged_docx.add_paragraph(p.text)
            
            final_docx = BytesIO()
            merged_docx.save(final_docx)
            st.download_button("📥 Word İndir", final_docx.getvalue(), "birlesmis_dosyalar.docx")

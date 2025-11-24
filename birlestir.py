import streamlit as st
import sys
import os
import tempfile
from io import BytesIO
from docx import Document

# GitHub'dan alınan pypdf yolunu ekle
sys.path.append("/mount/src/pypdf")
from pypdf import PdfMerger, PdfReader, PdfWriter

# Drag & drop sıralama için
from streamlit_sortable import sortable_items

# docx2pdf'i koşullu import et
try:
    import docx2pdf
    DOCX2PDF_AVAILABLE = True
except ImportError:
    DOCX2PDF_AVAILABLE = False

st.set_page_config(page_title="Belge Birleştirici", page_icon="📎", layout="centered")
st.title("📎 PDF & Word Birleştirici - Streamlit")
st.markdown("Bu uygulama PDF ve Word (DOCX) dosyalarını yükleyip sürükle-bırak yöntemiyle sırasını belirleyerek tek bir dosya haline getirir.")
st.markdown("---")

# --- Dosya Yükleme ---
uploaded_files = st.file_uploader(
    "PDF veya Word dosyalarını yükleyin (çoklu seçim mümkün)",
    type=["pdf", "docx"],
    accept_multiple_files=True
)

if not uploaded_files:
    st.info("Başlamak için PDF veya Word dosyalarını yükleyin.")
    st.markdown("---")
    st.caption("Not: Çok büyük dosyalarda bellek sınırları sorun oluşturabilir. Yerel çalıştırma daha stabil olabilir.")
    st.markdown("""
**Gereksinimler**:
- `pip install streamlit`
- `pip install pypdf`
- `pip install python-docx`
- `pip install streamlit-sortable`
- **DOCX+PDF birleştirme için**: `pip install docx2pdf` (Microsoft Word veya LibreOffice gerekli)

**Çalıştırma**:
```
streamlit run combine.py
```
""")
    st.stop()

# --- Dosya Sıralama ---
file_names = [f.name for f in uploaded_files]
st.subheader("Dosya sırası (sürükleyerek değiştirin)")
sorted_file_names = sortable_items(file_names, key="file_sort")
sorted_files = [uploaded_files[file_names.index(name)] for name in sorted_file_names]
st.markdown("---")

# --- PDF Sayfa Yönetimi ---
pdf_files_in_list = [n for n in file_names if n.lower().endswith('.pdf')]
if pdf_files_in_list:
    st.subheader("📄 PDF Sayfa Yönetimi")
    pdf_manage_name = st.selectbox("Sayfa yönetimi için bir PDF seçin", pdf_files_in_list)

    if pdf_manage_name:
        try:
            pdf_file = uploaded_files[file_names.index(pdf_manage_name)]
            pdf_file.seek(0)
            reader = PdfReader(pdf_file)
            total_pages = len(reader.pages)

            st.write(f"Toplam sayfa: **{total_pages}**")
            page_list = [f"Sayfa {i+1}" for i in range(total_pages)]
            st.write("Sayfaları sürükleyerek yeniden sıralayın veya seçerek silin.")

            reordered = sortable_items(page_list, key=f"sort_pages_{pdf_manage_name}")
            delete_pages = st.multiselect("Silinecek sayfalar", reordered)

            if st.button("📌 Yeni PDF Üret (Sayfa Silme / Taşıma)"):
                writer = PdfWriter()
                for page_name in reordered:
                    idx = int(page_name.split()[1]) - 1
                    if page_name not in delete_pages:
                        writer.add_page(reader.pages[idx])

                out_pdf = BytesIO()
                writer.write(out_pdf)
                out_pdf.seek(0)

                st.success("Yeni PDF oluşturuldu!")
                st.download_button(
                    "📥 Düzenlenmiş PDF'i İndir",
                    out_pdf,
                    f"edited_{pdf_manage_name}",
                    mime="application/pdf",
                )
        except Exception as e:
            st.error(f"PDF Sayfa Yönetimi Hatası: {e}")

st.markdown("---")

# --- PDF Birleştirme ---
pdf_files_to_merge = [file for file in sorted_files if file.name.lower().endswith(".pdf")]
if st.button("🔀 PDF'leri Birleştir", disabled=not pdf_files_to_merge):
    try:
        merger = PdfMerger()
        for file in pdf_files_to_merge:
            file.seek(0)
            merger.append(file)
        out = BytesIO()
        merger.write(out)
        merger.close()
        out.seek(0)

        st.success("PDF başarıyla birleştirildi!")
        st.download_button("📥 Birleşmiş PDF'i İndir", out, "merged.pdf", mime="application/pdf")
    except Exception as e:
        st.error(f"PDF birleştirme hatası: {e}")

# --- Word Birleştirme ---
word_files_to_merge = [file for file in sorted_files if file.name.lower().endswith(".docx")]
if st.button("📝 Word (DOCX) Birleştir", disabled=not word_files_to_merge):
    try:
        merged_doc = Document()
        first = True
        temp_files_to_clean = []

        for file in word_files_to_merge:
            temp_path = tempfile.mktemp(suffix=".docx")
            temp_files_to_clean.append(temp_path)
            file.seek(0)
            with open(temp_path, "wb") as tmp:
                tmp.write(file.getbuffer())

            sub_doc = Document(temp_path)
            if not first:
                merged_doc.add_page_break()
            for p in sub_doc.paragraphs:
                merged_doc.add_paragraph(p.text, style=p.style)
            first = False

        out_docx = BytesIO()
        merged_doc.save(out_docx)
        out_docx.seek(0)

        st.success("Word belgeleri birleştirildi!")
        st.download_button("📥 Birleşmiş Word Belgesini İndir", out_docx, "merged.docx", mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document")

        for path in temp_files_to_clean:
            if os.path.exists(path):
                os.remove(path)
    except Exception as e:
        st.error(f"Word birleştirme hatası: {e}")

# --- DOCX + PDF Tek PDF ---
if DOCX2PDF_AVAILABLE:
    if st.button("📄 DOCX + PDF → Tek PDF Birleştir", disabled=(not pdf_files_to_merge and not word_files_to_merge)):
        try:
            temp_pdf_list = []
            temp_files_to_clean = []
            docx_files_to_convert = [f for f in sorted_files if f.name.lower().endswith(".docx")]

            for file in docx_files_to_convert:
                tmp_docx = tempfile.mktemp(suffix=".docx")
                tmp_pdf = tempfile.mktemp(suffix=".pdf")
                temp_files_to_clean.extend([tmp_docx, tmp_pdf])
                file.seek(0)
                with open(tmp_docx, "wb") as tmp:
                    tmp.write(file.getbuffer())
                docx2pdf.convert(tmp_docx, tmp_pdf)
                temp_pdf_list.append(tmp_pdf)

            merger = PdfMerger()
            pdf_index = 0
            for file in sorted_files:
                if file.name.lower().endswith(".pdf"):
                    file.seek(0)
                    merger.append(file)
                else:
                    merger.append(temp_pdf_list[pdf_index])
                    pdf_index += 1

            out = BytesIO()
            merger.write(out)
            merger.close()
            out.seek(0)

            st.success("DOCX + PDF birlikte tek PDF olarak birleştirildi!")
            st.download_button("📥 Tek PDF Olarak İndir", out, "merged_all.pdf", mime="application/pdf")

            for path in temp_files_to_clean:
                if os.path.exists(path):
                    os.remove(path)
        except Exception as e:
            st.error(f"Birleştirme hatası: {e}")
            st.error("DOCX'ten PDF'e dönüştürme için sisteminizde Microsoft Word veya LibreOffice kurulu olmalıdır.")
else:
    st.warning("⚠️ `docx2pdf` modülü bulunamadı. DOCX + PDF birleştirme devre dışı.")

st.markdown("---")
st.caption("Not: Çok büyük dosyalarda bellek sınırları sorun oluşturabilir. Yerel çalıştırma daha stabil olabilir.")

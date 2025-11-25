import os
import tempfile
from io import BytesIO
import streamlit as st
from docx import Document
from pypdf import PdfMerger, PdfReader, PdfWriter

# DOCX2PDF – Cloud ortamında çalışmadığı için güvenli kontrol
try:
    import docx2pdf
    DOCX2PDF_AVAILABLE = True
except:
    DOCX2PDF_AVAILABLE = False


# --------------------------------------------------------
# Streamlit UI
# --------------------------------------------------------

st.set_page_config(page_title="Belge Birleştirici", page_icon="📎", layout="centered")
st.title("📎 PDF & Word Birleştirici")
st.markdown("PDF ve Word (.docx) dosyalarını birleştirebilirsiniz.")
st.markdown("---")

uploaded_files = st.file_uploader(
    "PDF veya Word dosyalarını yükleyin (çoklu seçim desteklenir)",
    type=["pdf", "docx"],
    accept_multiple_files=True
)

if not uploaded_files:
    st.info("Başlamak için dosya yükleyin.")
    st.stop()


# --------------------------------------------------------
# DOSYA SIRALAMA
# --------------------------------------------------------

file_names = [f.name for f in uploaded_files]

sorted_file_names = st.multiselect(
    "Birleştirme sırası (üstten alta doğru)",
    file_names,
    default=file_names
)

processed_files = st.session_state.processed_files
sorted_files = [processed_files[n] for n in sorted_file_names]
st.markdown("---")


# --------------------------------------------------------
# PDF SAYFA SİLME
# --------------------------------------------------------

pdf_files = [f for f in uploaded_files if f.name.lower().endswith(".pdf")]

if pdf_files:
    st.subheader("📄 PDF Sayfa Silme")

    selected_pdf_name = st.selectbox(
        "Sayfalarını düzenlemek istediğiniz PDF:",
        [f.name for f in pdf_files]
    )

    selected_pdf = pdf_files[[f.name for f in pdf_files].index(selected_pdf_name)]

    try:
        selected_pdf.seek(0)
        reader = PdfReader(selected_pdf)
        total_pages = len(reader.pages)

        page_labels = [f"Sayfa {i+1}" for i in range(total_pages)]
        delete_pages = st.multiselect("Silinecek sayfalar", page_labels)

        if st.button("📌 Yeni PDF Oluştur (Sayfa Silme)"):
            writer = PdfWriter()
            for idx in range(total_pages):
                if page_labels[idx] not in delete_pages:
                    writer.add_page(reader.pages[idx])

            output_pdf = BytesIO()
            writer.write(output_pdf)
            output_pdf.seek(0)

            st.success("Yeni PDF oluşturuldu!")
            st.download_button(
                label="📥 İndir",
                data=output_pdf,
                file_name=f"edited_{selected_pdf_name}",
                mime="application/pdf"
            )

    except Exception as e:
        st.error(f"Hata: {e}")

st.markdown("---")

# --- SİLİNEN PDF'İ BİRLEŞTİRME LİSTESİNE EKLE ---
# uploaded_files yerine processed_files listesi kullanılacak
if "processed_files" not in st.session_state:
    st.session_state.processed_files = {f.name: f for f in uploaded_files}

# bu PDF artık düzenlenmiş halini kullanacak
edited_pdf_data = out_pdf.getvalue()
st.session_state.processed_files[selected_pdf_name] = BytesIO(edited_pdf_data)
st.session_state.processed_files[selected_pdf_name].name = selected_pdf_name


# --------------------------------------------------------
# PDF BİRLEŞTİRME
# --------------------------------------------------------

pdf_files_to_merge = [f for f in sorted_files if f.name.lower().endswith(".pdf")]

if st.button("🔀 PDF'leri Birleştir", disabled=len(pdf_files_to_merge) == 0):
    try:
        merger = PdfMerger()

        for file in pdf_files_to_merge:
            file.seek(0)
            merger.append(file)

        output = BytesIO()
        merger.write(output)
        merger.close()
        output.seek(0)

        st.success("PDF birleştirildi!")
        st.download_button(
            "📥 Birleşmiş PDF'i İndir",
            output,
            "merged.pdf",
            mime="application/pdf"
        )

    except Exception as e:
        st.error(f"PDF birleştirme hatası: {e}")


# --------------------------------------------------------
# WORD (DOCX) BİRLEŞTİRME
# --------------------------------------------------------

word_files_to_merge = [f for f in sorted_files if f.name.lower().endswith(".docx")]

if st.button("📝 Word (DOCX) Birleştir", disabled=len(word_files_to_merge) == 0):
    try:
        merged_doc = Document()
        first = True

        for file in word_files_to_merge:
            # güvenli temp dosyası
            with tempfile.NamedTemporaryFile(delete=False, suffix=".docx") as tmp:
                tmp.write(file.getbuffer())
                tmp_path = tmp.name

            sub_doc = Document(tmp_path)

            if not first:
                merged_doc.add_page_break()

            for p in sub_doc.paragraphs:
                merged_doc.add_paragraph(p.text)   # stil kopyalanmaz – hatasız

            first = False
            os.remove(tmp_path)

        output_docx = BytesIO()
        merged_doc.save(output_docx)
        output_docx.seek(0)

        st.success("Word belgeleri birleştirildi!")
        st.download_button(
            "📥 Birleşmiş DOCX'i İndir",
            output_docx,
            "merged.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )

    except Exception as e:
        st.error(f"Word birleştirme hatası: {e}")


# --------------------------------------------------------
# DOCX + PDF → TEK PDF (Cloud ortamında devre dışı)
# --------------------------------------------------------

if DOCX2PDF_AVAILABLE:
    st.info("DOCX + PDF birleşimi için docx2pdf etkin, ancak Streamlit Cloud’da Word kurulu olmadığı için genelde çalışmaz. Umarım ileride bu hizmeti de verebiliriz")
else:
    st.warning("`docx2pdf` yüklenmediği için DOCX → PDF dönüşümü devre dışı.")

st.markdown("---")
st.caption("Not: Streamlit Cloud bellek sınırlarına sahiptir. Büyük dosyalarda yerel çalıştırma önerilir.")

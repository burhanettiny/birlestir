import os
import tempfile
from io import BytesIO

import streamlit as st
from docx import Document

# Eğer projede local pypdf varsa normal 'from pypdf import ...' çalışır;
# yoksa pypdf (pip install pypdf) yüklenmiş olmalı.
from pypdf import PdfMerger, PdfReader, PdfWriter

# DOCX->PDF (Windows Word COM) kontrollü import
try:
    import docx2pdf
    DOCX2PDF_AVAILABLE = True
except Exception:
    DOCX2PDF_AVAILABLE = False

# ---------------------------
# Session state başlangıcı
# ---------------------------
if "processed_pdfs" not in st.session_state:
    # processed_pdfs: { file_key: bytes_of_edited_pdf }
    st.session_state.processed_pdfs = {}

if "uploaded_meta" not in st.session_state:
    # uploaded_meta: list of dicts {key, name, file (UploadedFile)}
    st.session_state.uploaded_meta = []

# ---------------------------
# Streamlit UI
# ---------------------------
st.set_page_config(
    page_title="Belge Birleştirici",
    page_icon="📎",
    layout="centered"
)

st.title("📎 PDF & Word Birleştirici — Tam Entegre")
st.markdown(
    "PDF ve Word (.docx) dosyalarını yükleyin, PDF'lerde sayfa silme uygulayın; "
    "birleştirmede düzenlenmiş hali kullanılsın."
)
st.markdown("---")

uploaded_files = st.file_uploader(
    "PDF veya Word dosyalarını yükleyin (çoklu seçim desteklenir)",
    type=["pdf", "docx"],
    accept_multiple_files=True
)

# Eğer yeni yükleme yapıldıysa session_state.uploaded_meta güncelle
if uploaded_files:
    meta = []
    for i, f in enumerate(uploaded_files):
        key = f"{f.name}_{i}_{len(f.getbuffer())}"  # benzersiz anahtar
        meta.append({"key": key, "name": f.name, "file": f})
    st.session_state.uploaded_meta = meta

if not st.session_state.uploaded_meta:
    st.info("Başlamak için PDF veya Word dosyalarını yükleyin.")
    st.stop()

# Kullanıcıya sıralama seçeneği sun
choices = [f'{m["name"]} ({i})' for i, m in enumerate(st.session_state.uploaded_meta)]
sorted_choice = st.multiselect(
    "Birleştirme sırası — üstten alta (seçim yapın, varsayılan tüm dosyalar)",
    choices,
    default=choices
)

if not sorted_choice:
    sorted_meta = st.session_state.uploaded_meta.copy()
else:
    ordered_indices = [int(c.split("(")[-1].strip(")")) for c in sorted_choice]
    sorted_meta = [st.session_state.uploaded_meta[i] for i in ordered_indices]

st.markdown("---")

# ---------------------------
# PDF Sayfa Silme / Düzenleme
# ---------------------------
pdf_meta_list = [m for m in st.session_state.uploaded_meta if m["name"].lower().endswith(".pdf")]

if pdf_meta_list:
    st.subheader("📄 PDF Sayfa Yönetimi (silme)")
    pdf_choice_map = {f'{m["name"]} ({i})': m for i, m in enumerate(pdf_meta_list)}
    pdf_choice_display = [f'{m["name"]} ({i})' for i, m in enumerate(pdf_meta_list)]
    selected_pdf_display = st.selectbox("Düzenlemek istediğiniz PDF'i seçin", ["Seçiniz"] + pdf_choice_display)

    if selected_pdf_display != "Seçiniz":
        selected_meta = pdf_choice_map[selected_pdf_display]
        uploaded_file = selected_meta["file"]
        try:
            uploaded_file.seek(0)
            reader = PdfReader(uploaded_file)
            total_pages = len(reader.pages)
            st.write(f"Seçili dosya: **{selected_meta['name']}** — Toplam sayfa: **{total_pages}**")

            page_labels = [f"Sayfa {i+1}" for i in range(total_pages)]
            delete_pages = st.multiselect("Silinecek sayfalar", page_labels)

            if st.button("📌 Düzenlemeyi Uygula ve Kaydet", key=f"save_edit_{selected_meta['key']}"):
                writer = PdfWriter()
                for idx in range(total_pages):
                    if page_labels[idx] in delete_pages:
                        continue
                    writer.add_page(reader.pages[idx])

                out_pdf = BytesIO()
                writer.write(out_pdf)
                out_pdf.seek(0)
                st.session_state.processed_pdfs[selected_meta["key"]] = out_pdf.getvalue()
                st.success("Düzenleme kaydedildi — Bu dosya artık birleştirmede düzenlenmiş haliyle kullanılacak.")

                st.download_button(
                    "📥 Düzenlenmiş PDF'i indir",
                    data=out_pdf,
                    file_name=f"edited_{selected_meta['name']}",
                    mime="application/pdf"
                )
        except Exception as e:
            st.error(f"PDF düzenleme hatası: {e}")

st.markdown("---")

# ---------------------------
# PDF Birleştirme (düzenlenmiş sürümleri kullanır)
# ---------------------------
st.subheader("🔀 PDF'leri Birleştir (düzenlenmiş sürümler dahil)")
pdfs_in_sorted = [m for m in sorted_meta if m["name"].lower().endswith(".pdf")]

if st.button("PDF'leri Birleştir", disabled=len(pdfs_in_sorted) == 0):
    try:
        merger = PdfMerger()
        for meta in pdfs_in_sorted:
            key = meta["key"]
            if key in st.session_state.processed_pdfs:
                fobj = BytesIO(st.session_state.processed_pdfs[key])
                fobj.seek(0)
                merger.append(fobj)
            else:
                f = meta["file"]
                f.seek(0)
                merger.append(f)

        out = BytesIO()
        merger.write(out)
        merger.close()
        out.seek(0)
        st.success("PDF dosyaları (düzenlenmiş sürümler dahil) birleştirildi!")
        st.download_button("📥 Birleşmiş PDF'i İndir", out, "merged.pdf", mime="application/pdf")
    except Exception as e:
        st.error(f"PDF birleştirme hatası: {e}")

st.markdown("---")

# ---------------------------
# Word (DOCX) Birleştirme
# ---------------------------
st.subheader("📝 Word (DOCX) Birleştir")
docx_in_sorted = [m for m in sorted_meta if m["name"].lower().endswith(".docx")]

if st.button("Word (DOCX) Birleştir", disabled=len(docx_in_sorted) == 0):
    try:
        merged_doc = Document()
        first = True
        tmp_paths = []

        for meta in docx_in_sorted:
            f = meta["file"]
            with tempfile.NamedTemporaryFile(delete=False, suffix=".docx") as tmp:
                tmp.write(f.getbuffer())
                tmp_path = tmp.name
                tmp_paths.append(tmp_path)

            sub_doc = Document(tmp_path)
            if not first:
                merged_doc.add_page_break()
            for p in sub_doc.paragraphs:
                merged_doc.add_paragraph(p.text)
            first = False

        # temizle
        for p in tmp_paths:
            try:
                os.remove(p)
            except Exception:
                pass

        out = BytesIO()
        merged_doc.save(out)
        out.seek(0)
        st.success("Word belgeleri birleştirildi!")
        st.download_button(
            "📥 Birleşmiş DOCX'i İndir",
            out,
            "merged.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
    except Exception as e:
        st.error(f"Word birleştirme hatası: {e}")

st.markdown("---")

# ---------------------------
# DOCX + PDF → TEK PDF (DOCX'leri PDF'e çevirme)
# ---------------------------
st.subheader("📄 DOCX + PDF → Tek PDF (opsiyonel)")

if DOCX2PDF_AVAILABLE:
    st.info(
        "docx2pdf yüklü; fakat Streamlit Cloud'da Microsoft Word yüklü olmayabilir. "
        "Lokal makinede çalıştırırken kullanılabilir."
    )
else:
    st.warning("docx2pdf yüklü değil veya ortam desteklemiyor. DOCX→PDF dönüşümü devre dışı.")

if st.button(
    "DOCX + PDF → Tek PDF (sıra bazlı)",
    disabled=(len([m for m in sorted_meta if m["name"].lower().endswith(('.pdf', '.docx'))]) == 0)
):
    try:
        merger = PdfMerger()
        tmp_to_cleanup = []

        for meta in sorted_meta:
            if meta["name"].lower().endswith(".pdf"):
                key = meta["key"]
                if key in st.session_state.processed_pdfs:
                    fobj = BytesIO(st.session_state.processed_pdfs[key])
                    fobj.seek(0)
                    merger.append(fobj)
                else:
                    f = meta["file"]
                    f.seek(0)
                    merger.append(f)
            else:
                if not DOCX2PDF_AVAILABLE:
                    st.error("DOCX→PDF dönüştürme desteklenmiyor (docx2pdf yok). İşlem iptal edildi.")
                    raise RuntimeError("docx2pdf not available")

                with tempfile.NamedTemporaryFile(delete=False, suffix=".docx") as tmp:
                    tmp.write(meta["file"].getbuffer())
                    tmp_docx = tmp.name

                tmp_pdf = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
                tmp_pdf_path = tmp_pdf.name
                tmp_pdf.close()

                tmp_to_cleanup.extend([tmp_docx, tmp_pdf_path])
                docx2pdf.convert(tmp_docx, tmp_pdf_path)

                with open(tmp_pdf_path, "rb") as conv_f:
                    merger.append(conv_f)

        out = BytesIO()
        merger.write(out)
        merger.close()
        out.seek(0)
        st.success("Tüm dosyalar tek PDF hâline getirildi!")
        st.download_button("📥 Hepsini Tek PDF İndir", out, "merged_all.pdf", mime="application/pdf")

        # cleanup
        for p in tmp_to_cleanup:
            try:
                os.remove(p)
            except Exception:
                pass

    except Exception as e:
        st.error(f"DOCX+PDF → PDF dönüşüm/birleştirme hatası: {e}")

st.markdown("---")
st.caption("Not: Streamlit Cloud bellek/süre sınırlamalarına dikkat. Büyük dosyaları yerelde işleyin.")

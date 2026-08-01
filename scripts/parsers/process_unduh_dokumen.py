import os
import json
import re
import docx
from pypdf import PdfReader

def clean_text(text):
    if not text:
        return ""
    text = text.replace('\xa0', ' ').replace('\u200b', '')
    return ' '.join(text.split())

def unwrap_paragraph_lines(lines):
    unwrapped = []
    current_para = ""

    for raw_line in lines:
        line = clean_text(raw_line)
        if not line:
            if current_para:
                unwrapped.append(current_para)
                current_para = ""
            continue

        if not current_para:
            current_para = line
        else:
            if current_para.endswith("-"):
                current_para = current_para[:-1] + line
            elif not re.search(r'[\.:\?!_]$', current_para) or line[0].islower() or line.startswith("di ") or line.startswith("jawab ") or line.startswith("scan)") or line.startswith("diunggah"):
                current_para += " " + line
            else:
                unwrapped.append(current_para)
                current_para = line

    if current_para:
        unwrapped.append(current_para)

    return unwrapped

def iter_block_items(parent):
    if isinstance(parent, docx.document.Document):
        parent_elm = parent.element.body
    else:
        parent_elm = parent._element
    for child in parent_elm.iterchildren():
        if isinstance(child, docx.oxml.text.paragraph.CT_P):
            yield docx.text.paragraph.Paragraph(child, parent)
        elif isinstance(child, docx.oxml.table.CT_Tbl):
            yield docx.table.Table(child, parent)

def process_downloaded_documents():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    raw_unduh_dir = os.path.join(base_dir, "data", "raw", "unduh_dokumen")
    processed_unduh_dir = os.path.join(base_dir, "data", "processed", "unduh_dokumen")
    docx_dir = os.path.join(raw_unduh_dir, "docx")
    pdf_dir = os.path.join(raw_unduh_dir, "pdf")

    print("[+] Processing local downloaded documents (.docx & .pdf) with paragraph unwrapping...")

    parsed_documents = []

    # 1. Process Word .docx files
    if os.path.exists(docx_dir):
        for fname in os.listdir(docx_dir):
            if fname.endswith(".docx"):
                fpath = os.path.join(docx_dir, fname)
                doc = docx.Document(fpath)
                doc_title = fname.replace(".docx", "")

                doc_blocks = []
                for block in iter_block_items(doc):
                    if isinstance(block, docx.text.paragraph.Paragraph):
                        txt = clean_text(block.text)
                        if not txt:
                            continue
                        
                        if any(h_kw in txt.upper() for h_kw in ["IDENTITAS", "PENDIDIKAN FORMAL", "PRESTASI BIDANG", "PENGALAMAN ORGANISASI", "MOTIVASI KULIAH", "RENCANA SETELAH", "PEMETAAN KONDISI", "SURAT PERNYATAAN KOMITMEN", "TAAT ATURAN"]) and len(txt) < 80:
                            doc_blocks.append({
                                "type": "heading",
                                "content": f"###  {txt.upper()}"
                            })
                        elif any(s_kw in txt for s_kw in ["Seluruh informasi", "Bahwa saya", "Menyatakan", "Kota", "Nama Anda"]):
                            doc_blocks.append({
                                "type": "statement",
                                "content": f"_{txt}_"
                            })
                        else:
                            doc_blocks.append({
                                "type": "text",
                                "content": txt
                            })

                    elif isinstance(block, docx.table.Table):
                        rows_data = []
                        for r in block.rows:
                            r_cells = [clean_text(c.text) for c in r.cells]
                            clean_cells = []
                            for cell in r_cells:
                                if not clean_cells or clean_cells[-1] != cell:
                                    clean_cells.append(cell)
                            if any(c for c in clean_cells):
                                rows_data.append(clean_cells)

                        if rows_data:
                            max_cols = max(len(r) for r in rows_data)
                            formatted_rows = []
                            for r_idx, r in enumerate(rows_data):
                                padded_r = r + [""] * (max_cols - len(r))
                                formatted_rows.append("| " + " | ".join(padded_r) + " |")
                                if r_idx == 0:
                                    formatted_rows.append("| " + " | ".join([":---"] * max_cols) + " |")

                            doc_blocks.append({
                                "type": "table",
                                "content": "\n".join(formatted_rows)
                            })

                parsed_documents.append({
                    "filename": fname,
                    "doc_type": "DOCX",
                    "title": doc_title,
                    "blocks": doc_blocks
                })

    # 2. Process PDF files with paragraph unwrapping
    if os.path.exists(pdf_dir):
        for fname in os.listdir(pdf_dir):
            if fname.endswith(".pdf"):
                fpath = os.path.join(pdf_dir, fname)
                reader = PdfReader(fpath)
                doc_title = fname.replace(".pdf", "")

                pdf_lines = []
                for page in reader.pages:
                    raw_p = page.extract_text()
                    pdf_lines.extend(raw_p.split("\n"))

                unwrapped_paragraphs = unwrap_paragraph_lines(pdf_lines)

                doc_blocks = []
                for para in unwrapped_paragraphs:
                    if any(h_kw in para.upper() for h_kw in ["SURAT PERNYATAAN KESANGGUPAN", "CATATAN:"]):
                        doc_blocks.append({
                            "type": "heading",
                            "content": f"###  {para.upper()}"
                        })
                    else:
                        doc_blocks.append({
                            "type": "text",
                            "content": para
                        })

                parsed_documents.append({
                    "filename": fname,
                    "doc_type": "PDF",
                    "title": doc_title,
                    "blocks": doc_blocks
                })

    # Save JSON
    json_path = os.path.join(processed_unduh_dir, "unduh_dokumen_clean.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(parsed_documents, f, indent=2, ensure_ascii=False)

    # Save Markdown Knowledge Base
    md_path = os.path.join(processed_unduh_dir, "unduh_knowledge_base.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("# BASIS DATA DOKUMEN UNDUHAN & FORM ASESMEN DIRI PMB UII TA 2026/2027\n\n")
        f.write("Dokumen ini berisi struktur lengkap teks dan tabel dari seluruh Formulir Asesmen Diri Beasiswa, Surat Pernyataan Komitmen, dan Syarat Kedokteran Mandiri PMB UII yang diunduh secara lokal.\n\n")

        for doc in parsed_documents:
            f.write(f"##  DOKUMEN FORMULIR ({doc['doc_type']}): {doc['filename']}\n\n")
            for b in doc['blocks']:
                f.write(f"{b['content']}\n\n")
            f.write("---\n\n")

    print(f"[+] Successfully processed {len(parsed_documents)} local documents with unwrapped continuous paragraphs.")
    print(f"[+] Output JSON: {json_path}")
    print(f"[+] Output Markdown Knowledge Base: {md_path}")

if __name__ == "__main__":
    process_downloaded_documents()

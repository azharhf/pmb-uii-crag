import os
import io
import json
import re
import sys
import time
import shutil
import fitz
from dotenv import load_dotenv
from google import genai
from google.genai import types

# Configure console encoding for Windows UTF-8 output
sys.stdout.reconfigure(encoding='utf-8')

# Silence MuPDF C-level syntax error logs
try:
    fitz.TOOLS.mupdf_display_errors(False)
except Exception:
    pass

def clean_text_block(text):
    if not text:
        return ""
    # Remove emojis from extracted text
    emojis = [
        "📌", "🎯", "📊", "📝", "🏫", "🏦", "💳", "📄", "📍", "🏢", 
        "⭐", "📖", "🎓", "🏅", "✍️", "📚", "❓", "📞", "💡", "ü", "Ÿ"
    ]
    for emoji in emojis:
        text = text.replace(emoji, "")
    
    # Remove artificial line dividers
    text = re.sub(r'\n\s*---\s*\n', '\n\n', text)
    text = re.sub(r'\n\s*--\s*\n', '\n\n', text)
    text = re.sub(r' +', ' ', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()

def normalize_page_content_headings(raw_content):
    if not raw_content:
        return ""
    lines = raw_content.splitlines()
    normalized_lines = []

    for line in lines:
        stripped = line.strip()
        
        # Remove redundant Halaman headers
        if re.match(r'^#{1,6}\s*Halaman \d+', stripped, re.IGNORECASE):
            continue

        # Shift inner headings so max inner heading is H3 (###)
        if stripped.startswith('# '):
            normalized_lines.append('### ' + stripped[2:].strip())
        elif stripped.startswith('## '):
            normalized_lines.append('#### ' + stripped[3:].strip())
        elif stripped.startswith('### '):
            normalized_lines.append('##### ' + stripped[4:].strip())
        elif stripped.startswith('#### '):
            normalized_lines.append('###### ' + stripped[5:].strip())
        else:
            normalized_lines.append(line)

    return "\n".join(normalized_lines)

def process_brosur_pipeline(force_reprocess=True):
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    env_path = os.path.join(base_dir, ".env")
    load_dotenv(env_path)

    keys_str = os.getenv("GEMINI_API_KEYS", "")
    if not keys_str:
        fallback_key = os.getenv("GEMINI_API_KEY", "")
        keys_list = [fallback_key] if fallback_key else []
    else:
        keys_list = [k.strip() for k in keys_str.split(",") if k.strip()]

    if not keys_list:
        print("[!] No GEMINI_API_KEYS found in .env!")
        return

    print(f"[+] Loaded {len(keys_list)} Gemini API Keys for Automatic Key Rotation.")

    current_key_idx = 0
    client = genai.Client(api_key=keys_list[current_key_idx])
    target_model = "gemini-3.6-flash"

    raw_brosur_dir = os.path.join(base_dir, "data", "raw", "brosur", "pdf")
    processed_brosur_dir = os.path.join(base_dir, "data", "processed", "brosur")
    raw_brosur_md_dir = os.path.join(base_dir, "data", "raw", "brosur")
    os.makedirs(processed_brosur_dir, exist_ok=True)

    checkpoint_path = os.path.join(processed_brosur_dir, "brosur_vision_checkpoint.json")
    checkpoint_data = {}
    
    if force_reprocess and os.path.exists(checkpoint_path):
        print("[+] Force re-process enabled. Resetting previous checkpoint to extract 100% via Gemini Vision API.")
        checkpoint_data = {}
    elif os.path.exists(checkpoint_path):
        try:
            with open(checkpoint_path, "r", encoding="utf-8") as f:
                checkpoint_data = json.load(f)
            print(f"[+] Loaded checkpoint with {len(checkpoint_data)} processed brochure files.")
        except Exception:
            checkpoint_data = {}

    all_pdf_files = sorted([f for f in os.listdir(raw_brosur_dir) if f.endswith(".pdf")])
    print(f"[+] Found {len(all_pdf_files)} Brochure PDF files in raw directory.")

    for fname in all_pdf_files:
        fpath = os.path.join(raw_brosur_dir, fname)
        doc = fitz.open(fpath)
        total_pages = len(doc)

        # Check if already processed in checkpoint
        if fname in checkpoint_data and len(checkpoint_data[fname]) >= total_pages:
            print(f"[SKIP] {fname}: Already fully extracted in checkpoint ({total_pages} pages).")
            continue

        if fname not in checkpoint_data:
            checkpoint_data[fname] = []

        existing_pages = {p["page_number"]: p for p in checkpoint_data[fname]}

        print(f"\n[+] Processing Brochure with Gemini Vision: {fname} ({total_pages} pages)...")

        for p_idx in range(total_pages):
            page_num = p_idx + 1
            if page_num in existing_pages and existing_pages[page_num].get("content"):
                print(f"   -> Page {page_num}/{total_pages} already cached in checkpoint.")
                continue

            page = doc[p_idx]

            # ALWAYS USE GEMINI 3.6 FLASH VISION API FOR ALL PAGES FOR FULL UNCORRUPTED EXTRACTION
            print(f"   -> Extracting Page {page_num}/{total_pages} via Gemini 3.6 Flash Vision API (Key #{current_key_idx+1})...")
            pix = page.get_pixmap(dpi=200)
            img_bytes = pix.tobytes("png")
            image_part = types.Part.from_bytes(data=img_bytes, mime_type="image/png")

            prompt = (
                "Ekstrak SELURUH informasi dan teks yang ada pada gambar halaman brosur PMB Universitas Islam Indonesia (UII) ini "
                "ke dalam format Markdown yang rapi, terstruktur, dan SANGAT LENGKAP tanpa ada informasi yang dipangkas atau dilewati.\n\n"
                "Petunjuk Penformatan:\n"
                "1. Ekstrak semua judul, nama fakultas, nama program studi (D3/D4/S1/S2/S3/Profesi), gelar akademik, durasi studi, "
                "akreditasi (nasional & internasional), syarat pendaftaran, rincian biaya, deskripsi prodi, prospek kerja, fasilitas, dan kontak layanan.\n"
                "2. Format data ke dalam Markdown standar yang sangat rapi (`#`, `##`, `###`, `- **Field**: Nilai`, dan tabel Markdown `| | |`).\n"
                "3. DILARANG MENGGUNAKAN EMOJI DALAM BENTUK APAUPUN.\n"
                "4. DILARANG MENGGUNAKAN GARIS PEMBATAS '---' ATAU '--'.\n"
                "5. Sajikan dalam format Markdown bersih tanpa kalimat pengantar AI."
            )

            success = False
            max_key_rotations = len(keys_list) * 3
            rotations_tried = 0

            while rotations_tried < max_key_rotations and not success:
                try:
                    res = client.models.generate_content(
                        model=target_model,
                        contents=[prompt, image_part]
                    )
                    clean_md = normalize_page_content_headings(clean_text_block(res.text))

                    checkpoint_data[fname] = [p for p in checkpoint_data[fname] if p["page_number"] != page_num]
                    checkpoint_data[fname].append({
                        "page_number": page_num,
                        "content": clean_md
                    })

                    with open(checkpoint_path, "w", encoding="utf-8") as f:
                        json.dump(checkpoint_data, f, indent=2, ensure_ascii=False)

                    print(f"   [SUCCESS] Page {page_num}/{total_pages} extracted via Vision API ({len(clean_md)} chars) [Key #{current_key_idx+1}].")
                    success = True
                    break

                except Exception as e:
                    err_msg = str(e)
                    if "429" in err_msg or "RESOURCE_EXHAUSTED" in err_msg or "quota" in err_msg.lower():
                        old_key_idx = current_key_idx
                        current_key_idx = (current_key_idx + 1) % len(keys_list)
                        rotations_tried += 1
                        print(f"   [KEY ROTATION] Key #{old_key_idx+1} rate-limited. Rotating to Key #{current_key_idx+1}...")
                        client = genai.Client(api_key=keys_list[current_key_idx])
                        time.sleep(0.5)
                    else:
                        print(f"   [!] Vision API error on {fname} P{page_num}: {err_msg}")
                        rotations_tried += 1
                        time.sleep(1.5)

            time.sleep(0.5)

    # Build Master Markdown Knowledge Base
    brochure_titles = {
        "Brosur-UII-170126.pdf": "1. BROSUR UTAMA PMB UNIVERSITAS ISLAM INDONESIA TA 2026/2027",
        "2024-Brosur-FH.pdf": "2. BROSUR FAKULTAS HUKUM (FH UII)",
        "2024-Brosur-FK.pdf": "3. BROSUR FAKULTAS KEDOKTERAN (FK UII)",
        "Brosur FBE 25_26.pdf": "4. BROSUR FAKULTAS BISNIS DAN EKONOMIKA (FBE UII)",
        "Brosur FTI 25_26.pdf": "5. BROSUR FAKULTAS TEKNOLOGI INDUSTRI (FTI UII)",
        "Brosur FIAI 25_26.pdf": "6. BROSUR FAKULTAS ILMU AGAMA ISLAM (FIAI UII)",
        "2024-Brosur-FMIPA-1.pdf": "7. BROSUR FAKULTAS MATEMATIKA DAN ILMU PENGETAHUAN ALAM (FMIPA UII)",
        "2024-Brosur-FTSP-1.pdf": "8. BROSUR FAKULTAS TEKNIK SIPIL DAN PERENCANAAN (FTSP UII)",
        "Brosur-FPSB.pdf": "9. BROSUR FAKULTAS PSIKOLOGI DAN ILMU SOSIAL BUDAYA (FPSB UII)",
        "030226-Brosur-Pasca-sarjana.pdf": "10. BROSUR PROGRAM PASCASARJANA & PROFESI UII"
    }

    markdown_sections = []
    markdown_sections.append("# BASIS DATA KNOWLEDGE BASE BROSUR FAKULTAS & UNIVERSITAS UII TA 2026/2027\n")
    markdown_sections.append("Dokumen ini berisi himpunan data terstruktur resmi dari brosur cetak Penerimaan Mahasiswa Baru (PMB) Universitas Islam Indonesia untuk 8 Fakultas, Program Pascasarjana, dan Informasi Utama Universitas.\n")

    master_json_list = []

    for fname, clean_title in brochure_titles.items():
        if fname in checkpoint_data:
            pages = sorted(checkpoint_data[fname], key=lambda x: x["page_number"])
            markdown_sections.append(f"## {clean_title}\n")

            json_pages = []
            for p in pages:
                clean_c = clean_text_block(p["content"])
                if clean_c:
                    markdown_sections.append(clean_c + "\n\n")
                    json_pages.append({
                        "page_number": p["page_number"],
                        "paragraphs": clean_c.split("\n\n")
                    })

            markdown_sections.append("\n")

            master_json_list.append({
                "filename": fname,
                "title": clean_title,
                "page_count": len(pages),
                "total_chars": sum(len(p["content"]) for p in pages),
                "extraction_status": "SUCCESS",
                "pages": json_pages
            })

    md_path = os.path.join(processed_brosur_dir, "brosur_knowledge_base.md")
    raw_md_path = os.path.join(raw_brosur_md_dir, "brosur_knowledge_base.md")
    final_md_text = clean_text_block("\n".join(markdown_sections)) + "\n"

    # Write to processed directory
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(final_md_text)

    # Also write to raw directory for 100% sync
    with open(raw_md_path, "w", encoding="utf-8") as f:
        f.write(final_md_text)

    json_path = os.path.join(processed_brosur_dir, "brosur_clean.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(master_json_list, f, indent=2, ensure_ascii=False)

    print(f"\n[+] Pipeline Completed Successfully for All {len(all_pdf_files)} Brochure PDFs!")
    print(f"[+] Master Markdown (Processed) saved to: {md_path}")
    print(f"[+] Master Markdown (Raw Sync) saved to: {raw_md_path}")
    print(f"[+] Master JSON saved to: {json_path}")

if __name__ == "__main__":
    process_brosur_pipeline(force_reprocess=True)

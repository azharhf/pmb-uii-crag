"""
================================================================================
UJIAN AKHIR SEMESTER (UAS) - TRENDING TOPICS ON STATISTICS (TToS) 2026
--------------------------------------------------------------------------------
02_TEXT_PREPROCESSING.PY (SOAL 2 - BOBOT 15%)
--------------------------------------------------------------------------------
Fungsi:
1. Memuat seluruh Knowledge Base Markdown (*_knowledge_base.md) dari 11 modul
   PMB UII (BUKAN file .json mentah — untuk menghindari str(dict) noise).
2. Melakukan pembersihan teks tingkat lanjut (Enhanced Natural Clean Text Pipeline):
   a. Markdown Link Stripping: [text](url) → hapus URL, pertahankan anchor jika bermakna.
   b. CDN-CGI / Email-Protection Artifact Removal: Cloudflare obfuscation patterns.
   c. Domain & URL Removal: Pola *.ac.id, *.uii.ac.id, https://... dihapus tuntas.
   d. Email & Phone Removal: Pola email@domain, (0274) 898444, +62 xxx dihapus.
   e. Noise Cleaning: Tag HTML, simbol Markdown (#, ##), bullet (•, -), penomoran (1., 2.).
   f. Table Syntax Removal: Pola Markdown table (|, :---, dst.) dihapus.
   g. Case Folding: Konversi ke huruf kecil (lowercase).
   h. Tokenization: Pemisahan kata berbasis aturan NLP Bahasa Indonesia.
   i. Enhanced Stopword Removal: Stopwords umum + domain-specific (situs, web, telp, faks).
   j. Tanpa Stemming: Mempertahankan tata bahasa alami demi performa IndoBERT & RAG.
3. Quality Gate: Minimum 8 token per section, max 500 token (skip mega-dump redundan).
4. Near-Duplicate Detection: Jaccard similarity > 0.85 → skip dokumen redundan.
5. Menampilkan contoh Before vs After dari 3 sampel dokumen.
6. Menyimpan hasil preprocessed dataset ke 'outputs/reports/preprocessed_nlp_dataset.json'.
================================================================================
"""

import os
import re
import json
import sys

# Configure UTF-8 encoding for Windows console
sys.stdout.reconfigure(encoding='utf-8')

# ============================================================================
# STOPWORD SETS
# ============================================================================

# Core Indonesian Stopwords (gentle removal — non-informatif)
INDONESIAN_STOPWORDS = set([
    "dan", "di", "ke", "dari", "yang", "untuk", "pada", "adalah", "ini", "itu",
    "dengan", "atau", "bahwa", "dapat", "secara", "serta", "oleh", "hal", "tersebut",
    "yaitu", "sebagai", "bagi", "akan", "telah", "bisa", "ada", "kami",
    "kita", "anda", "saya", "ia", "mereka", "juga", "pun", "agar", "supaya", "apabila",
    "jika", "maka", "namun", "tetapi", "saja", "lagi", "bahkan", "hanya", "tentang",
    "masing", "lebih", "melalui", "setiap", "antara", "sedangkan", "maupun",
    "berupa", "hingga", "ketika", "sebelum", "sesudah", "dalam", "lain",
])

# Domain-Specific Stopwords (metadata navigasi, alamat, & noise teknis PMB website)
DOMAIN_STOPWORDS = set([
    "situs", "web", "telp", "telepon", "telephone", "faks", "fax", "ext",
    "hunting", "email", "whatsapp", "protected", "cdn", "cgi",
    "http", "https", "www", "ac", "id", "co", "com", "org",
    "page", "number", "paragraphs",  # brosur OCR artifacts
    "rp",  # currency prefix without number = noise
    "ya", "tidak",  # table markers: "Ya (✔)" / "Tidak (—)" in prodi tables
    "pertanyaan", "jawaban",  # FAQ structural markers (repeated in every Q&A)
    "layanan", "informasi",  # generic navigational words across all modules
    "jl", "jalan", "km", "ext", "no", "gedung", "lt", "baca", "buka", "selengkapnya" # address/navigational noise
])

ALL_STOPWORDS = INDONESIAN_STOPWORDS | DOMAIN_STOPWORDS

# ============================================================================
# CLEANING FUNCTIONS
# ============================================================================

def clean_markdown_links(text):
    """Remove Markdown links [text](url) → keep text only if it's not a domain/URL."""
    def replace_link(match):
        anchor = match.group(1)
        # If anchor text looks like a domain/URL → remove entirely
        if re.search(r'\.\w{2,3}(\.\w{2,3})?(/|$)', anchor):
            return ' '
        # If anchor text looks like an email → remove entirely
        if '@' in anchor:
            return ' '
        return anchor

    return re.sub(r'\[([^\]]*)\]\([^\)]*\)', replace_link, text)


def clean_cloudflare_artifacts(text):
    """Remove Cloudflare CDN-CGI email protection artifacts."""
    # Pattern: cdn-cgi/l/email-protection#hex...
    text = re.sub(r'cdn[\-]?cgi[/\\]l[/\\]email[\-]?protection[#\w]*', ' ', text)
    # Pattern: [email protected] (Cloudflare placeholder)
    text = re.sub(r'\[email\s*protected\]', ' ', text)
    return text


def clean_domains_urls_emails(text):
    """Remove URLs, domain names, email addresses, and phone numbers."""
    # Full URLs
    text = re.sub(r'https?://\S+', ' ', text)
    text = re.sub(r'www\.\S+', ' ', text)
    # Domain patterns: word.uii.ac.id, word.ac.id, etc.
    text = re.sub(r'\b\w+\.\w+\.ac\.id\b', ' ', text)
    text = re.sub(r'\b\w+\.ac\.id\b', ' ', text)
    text = re.sub(r'\b\w+\.uii\.ac\.id\b', ' ', text)
    # Email addresses
    text = re.sub(r'\b[\w\.\-]+@[\w\.\-]+\.\w+\b', ' ', text)
    # Phone numbers: (0274) 898444, +62 274 898444, 0811-260-8844, etc.
    text = re.sub(r'\+?\d[\d\s\-\(\)\.]{7,}', ' ', text)
    # WhatsApp link patterns
    text = re.sub(r'wa\.me/\d+', ' ', text)
    return text


def clean_table_syntax(text):
    """Remove Markdown table syntax (|, :---, alignment markers)."""
    # Table row separators: | :--- | :--- |
    text = re.sub(r'\|?\s*:?-{2,}:?\s*\|', ' ', text)
    # Remaining pipe separators in table rows
    text = re.sub(r'\|', ' ', text)
    return text


def clean_structural_noise(text):
    """Remove HTML tags, Markdown symbols, list numbering, and bullets."""
    if not text:
        return ""

    # 1. Cloudflare artifacts
    text = clean_cloudflare_artifacts(text)

    # 2. Markdown links [text](url) → meaningful text or remove
    text = clean_markdown_links(text)

    # 3. Domains, URLs, emails, phones
    text = clean_domains_urls_emails(text)

    # 4. HTML tags
    text = re.sub(r'<[^>]+>', ' ', text)

    # 5. Markdown headers (#, ##, ###)
    text = re.sub(r'#+\s*', '', text)

    # 6. Markdown bold/italic (**text**, *text*, __text__)
    text = re.sub(r'\*{1,2}([^*]+)\*{1,2}', r'\1', text)
    text = re.sub(r'_{1,2}([^_]+)_{1,2}', r'\1', text)

    # 7. Table syntax
    text = clean_table_syntax(text)

    # 8. List numbering at line starts (1., 2., 1.1, a., b.)
    text = re.sub(r'^\s*(\d+[\.)]|[a-zA-Z][\.)])\s*', '', text, flags=re.MULTILINE)
    text = re.sub(r'\b\d+[\.)]\s*', '', text)

    # 9. Bullets and remaining markdown symbols
    text = re.sub(r'[•\-~`]', ' ', text)

    # 10. Checkmark/cross symbols from table data
    text = re.sub(r'[✔✓✗✘—]', ' ', text)
    text = re.sub(r'\(?\s*[✔✓]\s*\)?', ' ', text)
    text = re.sub(r'\(?\s*[—✗✘]\s*\)?', ' ', text)

    # 11. Remove excess special punctuation but keep alphanumeric
    text = re.sub(r'[^\w\s]', ' ', text)

    # 12. Remove standalone single characters (leftover noise)
    text = re.sub(r'\b\w\b', ' ', text)

    # 13. Normalize multiple spaces and newlines
    text = re.sub(r'\s+', ' ', text).strip()

    return text


def preprocess_document_text(raw_text):
    """Execute Enhanced Natural Clean Text NLP Pipeline."""
    # Step 1: Structural Noise Cleaning
    cleaned_noise = clean_structural_noise(raw_text)

    # Step 2: Case Folding
    lowercase_text = cleaned_noise.lower()

    # Step 3: Tokenization (words of 2+ alphabetic characters)
    tokens = re.findall(r'\b[a-z]{2,}\b', lowercase_text)

    # Step 4: Enhanced Stopword Removal (core + domain-specific)
    filtered_tokens = [t for t in tokens if t not in ALL_STOPWORDS]

    # Reconstruct Natural Clean Text
    processed_text = " ".join(filtered_tokens)

    return {
        "step1_clean_noise": cleaned_noise,
        "step2_case_folding": lowercase_text,
        "step3_tokens": tokens,
        "step4_filtered_tokens": filtered_tokens,
        "final_text": processed_text
    }


# ============================================================================
# NEAR-DUPLICATE DETECTION
# ============================================================================

def jaccard_similarity(text_a, text_b):
    """Calculate Jaccard similarity between two preprocessed texts."""
    set_a = set(text_a.split())
    set_b = set(text_b.split())
    if not set_a or not set_b:
        return 0.0
    intersection = set_a & set_b
    union = set_a | set_b
    return len(intersection) / len(union)


# ============================================================================
# MARKDOWN KNOWLEDGE BASE PARSER
# ============================================================================

def process_knowledge_base_md(filepath, module_name, processed_records,
                              sample_demonstrations, seen_texts):
    """Parse a *_knowledge_base.md file into clean document sections with H2 parent tracking."""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()

        # Split by Markdown headers (##, ###)
        raw_sections = re.split(r'\n(?=#+\s+)', content)

        current_h2_title = ""

        for sec in raw_sections:
            sec_strip = sec.strip()
            if not sec_strip:
                continue

            lines = sec_strip.split("\n")
            header_line = lines[0]
            body_text = "\n".join(lines[1:]).strip() if len(lines) > 1 else ""

            # Check if this is an H2 header (## )
            if header_line.startswith("## ") and not header_line.startswith("### "):
                current_h2_title = clean_structural_noise(header_line.replace("##", "")).strip()

            # Extract clean section title
            clean_sub_title = clean_structural_noise(header_line).strip()

            # Build full contextual section title
            if current_h2_title and current_h2_title.upper() not in clean_sub_title.upper():
                full_section_title = f"{current_h2_title} - {clean_sub_title}" if clean_sub_title != current_h2_title else current_h2_title
            else:
                full_section_title = clean_sub_title if clean_sub_title else current_h2_title

            if not full_section_title:
                continue
            upper_title = full_section_title.upper()
            if any(skip in upper_title for skip in [
                "BASIS DATA", "KNOWLEDGE BASE", "DOKUMEN INI",
            ]):
                continue

            # If body text is empty or very short, combine header line
            full_body_text = f"{full_section_title}\n{body_text}".strip() if body_text else full_section_title
            if len(full_body_text) < 15:
                continue

            # Preprocess body text
            res = preprocess_document_text(full_body_text)
            token_count = len(res["step4_filtered_tokens"])

            # Quality Gate: minimum 5 tokens, maximum 2000 tokens (allow complete prodi fee tables)
            if token_count < 5:
                continue
            if token_count > 2000:
                continue

            # Near-Duplicate Detection (include title in check so distinct prodis are never skipped)
            final_text = res["final_text"]
            is_duplicate = False
            for existing_text in seen_texts:
                if jaccard_similarity(final_text, existing_text) > 0.92:
                    is_duplicate = True
                    break

            if is_duplicate:
                continue

            seen_texts.append(final_text)

            contextual_prefix = f"[Dokumen: {module_name.upper()} -> {full_section_title} (UKA=Catur Darma, UKK=SPP)]: "
            contextual_text = contextual_prefix + final_text

            processed_records.append({
                "module": module_name.upper(),
                "section_title": full_section_title,
                "raw_text": full_body_text,
                "parent_text": full_body_text,
                "preprocessed_text": final_text,
                "contextual_text": contextual_text,
                "token_count": token_count
            })

            # Collect sample demonstrations (first 3 docs with >100 chars)
            if len(sample_demonstrations) < 3 and len(full_body_text) > 100:
                sample_demonstrations.append({
                    "title": full_section_title,
                    "raw": full_body_text[:200] + "...",
                    "step1": res["step1_clean_noise"][:200] + "...",
                    "step2": res["step2_case_folding"][:200] + "...",
                    "step3_tokens": res["step3_tokens"][:12],
                    "step4_stopwords": res["step4_filtered_tokens"][:12],
                    "final": res["final_text"][:200] + "..."
                })

    except Exception as e:
        print(f"  [!] Error processing {filepath}: {e}")


# ============================================================================
# MAIN PIPELINE
# ============================================================================

def run_text_preprocessing_pipeline():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    processed_dir = os.path.join(base_dir, "data", "processed")
    outputs_dir = os.path.join(base_dir, "outputs")
    reports_dir = os.path.join(outputs_dir, "reports")
    os.makedirs(reports_dir, exist_ok=True)

    print("=" * 90)
    print(" [SOAL 02] PIPELINE PREPROCESSING TEKS (ENHANCED NATURAL CLEAN TEXT ENGINE)")
    print("=" * 90)

    processed_records = []
    sample_demonstrations = []
    seen_texts = []  # For near-duplicate detection

    md_files_found = 0
    skipped_files = 0

    if os.path.exists(processed_dir):
        for root, dirs, files in os.walk(processed_dir):
            # Determine module name from directory
            mod_name = os.path.basename(root)
            if mod_name == "processed":
                mod_name = "UMUM"

            # EXCLUDE unduh_dokumen (form templates & empty field noise) from RAG vector index
            if "unduh_dokumen" in root.lower() or mod_name.lower() == "unduh_dokumen":
                skipped_files += len(files)
                continue

            for file in files:
                filepath = os.path.join(root, file)

                # ============================================================
                # FIX MASALAH 2: ONLY process *_knowledge_base.md files
                # Skip .json files entirely to avoid str(dict) noise & duplication
                # ============================================================
                if file.endswith("_knowledge_base.md") or file.endswith("_knowledge_base.md"):
                    md_files_found += 1
                    print(f"  [📄] Processing: {mod_name}/{file}")
                    process_knowledge_base_md(
                        filepath, mod_name, processed_records,
                        sample_demonstrations, seen_texts
                    )
                else:
                    skipped_files += 1

    print(f"\n[+] Knowledge Base MD files processed : {md_files_found}")
    print(f"[+] Non-KB files skipped (JSON, PDF, etc.): {skipped_files}")
    print(f"[+] Total Section Dokumen Berhasil Diproses : {len(processed_records)} Section Dokumen Bersih")

    # Per-module breakdown
    from collections import Counter
    mod_counts = Counter(r["module"] for r in processed_records)
    total_tokens = sum(r["token_count"] for r in processed_records)
    print(f"[+] Total Token Bersih Seluruh Korpus    : {total_tokens:,} token")
    print(f"[+] Jumlah Modul PMB Unik                : {len(mod_counts)} modul")
    for mod, cnt in sorted(mod_counts.items()):
        mod_tokens = sum(r["token_count"] for r in processed_records if r["module"] == mod)
        print(f"    - Modul '{mod:20s}': {cnt:3d} section ({mod_tokens:,} token)")

    # Display Before vs After Demonstrations
    print("\n--- DEMONSTRASI TAHAPAN PREPROCESSING (BEFORE VS AFTER) ---")
    for idx, demo in enumerate(sample_demonstrations, 1):
        print(f"\nSample #{idx} [{demo['title']}]:")
        print(f'  [RAW INPUT]            : "{demo["raw"]}"')
        print(f'  [1. Noise Cleaning]    : "{demo["step1"]}"')
        print(f'  [2. Case Folding]      : "{demo["step2"]}"')
        print(f'  [3. Tokenization]      : {demo["step3_tokens"]}')
        print(f'  [4. Stopword Removal]  : {demo["step4_stopwords"]}')
        print(f'  [5. Natural Clean Text]: "{demo["final"]}"')

    # Save to JSON Report
    output_json = os.path.join(reports_dir, "preprocessed_nlp_dataset.json")
    out_payload = {
        "pipeline_stage": "02_text_preprocessing",
        "total_documents": len(processed_records),
        "total_tokens_clean": total_tokens,
        "natural_language": "Indonesian",
        "stemming_applied": False,
        "source_format": "Markdown Knowledge Base (*_knowledge_base.md) — JSON files excluded",
        "quality_gates": {
            "min_tokens": 8,
            "max_tokens": 500,
            "duplicate_threshold_jaccard": 0.85
        },
        "cleaning_steps": [
            "Markdown Link Stripping [text](url)",
            "Cloudflare CDN-CGI Email Protection Removal",
            "Domain/URL/Email/Phone Removal",
            "HTML Tag Removal",
            "Markdown Header & Table Syntax Removal",
            "Bullet/Numbering/Symbol Removal",
            "Case Folding (lowercase)",
            "Tokenization (alphabetic ≥2 chars)",
            "Enhanced Stopword Removal (Indonesian + Domain-Specific)",
            "Near-Duplicate Detection (Jaccard > 0.85)"
        ],
        "description": "Cleaned natural text without stemming for optimal IndoBERT, Vector Search & Visualizations",
        "data": processed_records
    }

    with open(output_json, "w", encoding="utf-8") as f:
        json.dump(out_payload, f, indent=2, ensure_ascii=False)

    print(f"\n[+] Preprocessed NLP dataset saved to: {output_json}")
    print("=" * 90)


if __name__ == "__main__":
    run_text_preprocessing_pipeline()

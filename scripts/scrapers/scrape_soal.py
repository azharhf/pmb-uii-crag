import os
import json
import re
import requests
from bs4 import BeautifulSoup
from common_utils import remove_site_noise, convert_links_to_markdown, extract_table_with_icons, clean_text

def scrape_soal_page():
    url = "https://pmb.uii.ac.id/soal/"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }

    print(f"[+] Scraping Contoh Soal & Pemetaan Materi Ujian from {url}...")
    resp = requests.get(url, headers=headers, timeout=15)
    resp.encoding = 'utf-8'

    if resp.status_code != 200:
        print(f"[!] Error fetching Soal page: {resp.status_code}")
        return

    soup = BeautifulSoup(resp.text, 'html.parser')
    soup = remove_site_noise(soup)
    soup = convert_links_to_markdown(soup)

    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    soal_dir = os.path.join(base_dir, "data", "processed", "contoh_soal")
    os.makedirs(soal_dir, exist_ok=True)

    content_area = soup.find('main') or soup.find(class_=lambda c: c and 'entry-content' in str(c)) or soup

    # Lead Info Paragraphs
    lead_paragraphs = []
    for p in content_area.find_all(['p', 'h2', 'h3']):
        t = clean_text(p.get_text(" ", strip=True))
        if t and ("Contoh Soal Ujian" in t or "pola seleksi" in t.lower() or "terdiri dari" in t.lower()):
            lead_paragraphs.append(t)

    # Subject Mapping Tables
    mapping_tables = []
    for tbl in content_area.find_all('table'):
        t_rows = extract_table_with_icons(tbl)
        if t_rows:
            mapping_tables.append(t_rows)

    # Extract Accordion Questions per Subject using HTML <li> DOM structure
    accordion_titles = content_area.select('.elementor-tab-title')
    accordion_contents = content_area.select('.elementor-tab-content')

    subjects_data = []

    for idx, title_el in enumerate(accordion_titles):
        subj_name = clean_text(title_el.get_text(" ", strip=True))
        content_el = accordion_contents[idx] if idx < len(accordion_contents) else None

        passages = []
        parsed_questions = []

        if content_el:
            # Extract reading passages if any
            for p in content_el.find_all('p'):
                p_txt = clean_text(p.get_text(" ", strip=True))
                if p_txt and not p_txt.startswith("Contoh") and not p_txt.startswith("Soal"):
                    passages.append(p_txt)

            # Extract <li> question items
            ol_tag = content_el.find('ol')
            if ol_tag:
                li_items = ol_tag.find_all('li')
                for q_idx, li in enumerate(li_items):
                    li_raw = clean_text(li.get_text(" ", strip=True))
                    # Split question stem and options A., B., C., D., E.
                    parts = re.split(r'\s+(?=[A-E]\.\s*)', li_raw)
                    stem = parts[0] if parts else li_raw
                    opts = parts[1:] if len(parts) > 1 else []

                    parsed_questions.append({
                        "q_num": q_idx + 1,
                        "stem": stem,
                        "options": opts
                    })

        subjects_data.append({
            "subject": subj_name,
            "passages": passages,
            "questions": parsed_questions
        })

    # Save JSON
    json_path = os.path.join(soal_dir, "soal_exam.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump({
            "lead_info": lead_paragraphs,
            "mapping_tables": mapping_tables,
            "subjects": subjects_data
        }, f, indent=2, ensure_ascii=False)

    # Save Markdown Knowledge Base
    md_path = os.path.join(soal_dir, "soal_knowledge_base.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("# BASIS DATA CONTOH SOAL UJIAN & PEMETAAN MATERI SELEKSI PMB UII TA 2026/2027\n\n")
        
        f.write("##  KETENTUAN UMUM & ALOKASI JUMLAH SOAL\n\n")
        for lp in lead_paragraphs:
            f.write(f"{lp}\n\n")
        f.write("---\n\n")

        if mapping_tables:
            f.write("##  PEMETAAN MATERI SELEKSI UJIAN PMB UII\n\n")
            for t_rows in mapping_tables:
                for r_idx, r in enumerate(t_rows):
                    f.write("| " + " | ".join(r) + " |\n")
                    if r_idx == 0:
                        f.write("| " + " | ".join([":---"] * len(r)) + " |\n")
                f.write("\n")
            f.write("---\n\n")

        f.write("##  CONTOH SOAL UJIAN PER MATA PELAJARAN SPESIFIK\n\n")
        for subj in subjects_data:
            f.write(f"###  MATERI UJIAN: {subj['subject'].upper()}\n\n")
            
            # Print passages if any
            for pas in subj['passages']:
                f.write(f" **Teks Bacaan**: _{pas}_\n\n")

            # Print formatted questions
            for q in subj['questions']:
                f.write(f"**Soal {q['q_num']}**: {q['stem']}\n")
                for opt in q['options']:
                    f.write(f"  - {opt}\n")
                f.write("\n")

            f.write("---\n\n")

    print(f"[+] Scraped {len(subjects_data)} exam subject accordions cleanly using HTML <li> DOM parser.")
    print(f"[+] Output JSON: {json_path}")
    print(f"[+] Output Markdown Knowledge Base: {md_path}")

if __name__ == "__main__":
    scrape_soal_page()

import os
import json
import requests
from bs4 import BeautifulSoup
from common_utils import remove_site_noise, convert_links_to_markdown, extract_aria_control_tabs, extract_table_with_icons, clean_text

def scrape_beasiswa_page():
    url = "https://pmb.uii.ac.id/beasiswa/"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }

    print(f"[+] Scraping Jalur Beasiswa from {url}...")
    resp = requests.get(url, headers=headers, timeout=15)
    resp.encoding = 'utf-8'

    if resp.status_code != 200:
        print(f"[!] Error fetching Jalur Beasiswa page: {resp.status_code}")
        return

    soup = BeautifulSoup(resp.text, 'html.parser')
    soup = remove_site_noise(soup)
    soup = convert_links_to_markdown(soup)

    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    beasiswa_dir = os.path.join(base_dir, "data", "processed", "jalur_beasiswa")
    os.makedirs(beasiswa_dir, exist_ok=True)

    content_area = soup.find('main') or soup.find(class_=lambda c: c and 'entry-content' in str(c)) or soup

    # Lead Paragraphs
    lead_paragraphs = []
    for p in content_area.find_all(['p', 'h2']):
        t = clean_text(p.get_text(" ", strip=True))
        if t and ("Jalur Beasiswa adalah" in t or "lulusan tahun" in t.lower() or "Terdapat 5 jenis" in t):
            lead_paragraphs.append(t)

    # Extract ARIA-Controls Tabs (.e-n-tabs)
    raw_tabs_dict = extract_aria_control_tabs(content_area)

    # Deduplicate and order tab names
    tab_order = [
        "Sleman Pintar",
        "Afirmasi",
        "Santri",
        "Hafizah Hafiz",
        "Atlet & Seni",
        "KIP",
        "Tabel Pemetaan Mata Pelajaran"
    ]

    beasiswa_by_tabs = {}

    for title, panel_soup in raw_tabs_dict.items():
        # Clean title name
        norm_title = title
        if "Atlet" in title or "Seni" in title:
            norm_title = "Atlet & Seni"
        elif "Pemetaan" in title:
            norm_title = "Tabel Pemetaan Mata Pelajaran"
        elif "Sleman" in title:
            norm_title = "Sleman Pintar"
        elif "Afirmasi" in title:
            norm_title = "Afirmasi"
        elif "Santri" in title:
            norm_title = "Santri"
        elif "Hafizah" in title:
            norm_title = "Hafizah Hafiz"
        elif "KIP" in title:
            norm_title = "KIP Kuliah"

        if norm_title in beasiswa_by_tabs:
            continue

        tab_blocks = []

        for el in panel_soup.find_all(['h2', 'h3', 'h4', 'h5', 'p', 'ul', 'ol', 'table']):
            txt = clean_text(el.get_text(" ", strip=True))
            if not txt:
                continue

            if el.name in ['h2', 'h3', 'h4', 'h5'] and len(txt) < 80:
                tab_blocks.append({
                    "type": "heading",
                    "content": f"###  {txt}"
                })
            elif el.name == 'table':
                t_rows = extract_table_with_icons(el)
                formatted_rows = []
                for r_idx, r in enumerate(t_rows):
                    formatted_rows.append("| " + " | ".join(r) + " |")
                    if r_idx == 0:
                        formatted_rows.append("| " + " | ".join([":---"] * len(r)) + " |")
                if formatted_rows:
                    tab_blocks.append({
                        "type": "table",
                        "content": "\n".join(formatted_rows)
                    })
            elif el.name in ['ul', 'ol']:
                items = [clean_text(li.get_text(" ", strip=True)) for li in el.find_all('li') if clean_text(li.get_text(" ", strip=True))]
                if items:
                    tab_blocks.append({
                        "type": "list",
                        "content": "\n".join([f"- {item}" for item in items])
                    })
            elif len(txt) > 10:
                tab_blocks.append({
                    "type": "text",
                    "content": txt
                })

        if tab_blocks:
            beasiswa_by_tabs[norm_title] = tab_blocks

    # Save JSON
    json_path = os.path.join(beasiswa_dir, "beasiswa_all_tabs.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(beasiswa_by_tabs, f, indent=2, ensure_ascii=False)

    # Save Markdown Knowledge Base
    md_path = os.path.join(beasiswa_dir, "beasiswa_knowledge_base.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("# BASIS DATA JALUR SELEKSI BEASISWA PMB UII TA 2026/2027\n\n")
        
        for lp in lead_paragraphs:
            f.write(f"_{lp}_\n\n")
        f.write("---\n\n")

        for tname, blocks in beasiswa_by_tabs.items():
            f.write(f"# KATEGORI TAB BEASISWA: {tname.upper()}\n\n")
            for b in blocks:
                f.write(f"{b['content']}\n\n")
            f.write("---\n\n")

    print(f"[+] Scraped Jalur Beasiswa cleanly across {len(beasiswa_by_tabs)} unique tabs.")
    print(f"[+] Output JSON: {json_path}")
    print(f"[+] Output Markdown Knowledge Base: {md_path}")

if __name__ == "__main__":
    scrape_beasiswa_page()

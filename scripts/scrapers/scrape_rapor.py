import os
import json
import requests
from bs4 import BeautifulSoup
from common_utils import remove_site_noise, convert_links_to_markdown, extract_aria_control_tabs, extract_table_with_icons, clean_text

def scrape_rapor_page():
    url = "https://pmb.uii.ac.id/rapor/"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }

    print(f"[+] Scraping Jalur Rapor from {url}...")
    resp = requests.get(url, headers=headers, timeout=15)
    resp.encoding = 'utf-8'

    if resp.status_code != 200:
        print(f"[!] Error fetching Jalur Rapor page: {resp.status_code}")
        return

    soup = BeautifulSoup(resp.text, 'html.parser')
    soup = remove_site_noise(soup)
    soup = convert_links_to_markdown(soup)

    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    rapor_dir = os.path.join(base_dir, "data", "processed", "jalur_rapor")
    os.makedirs(rapor_dir, exist_ok=True)

    content_area = soup.find('main') or soup.find(class_=lambda c: c and 'entry-content' in str(c)) or soup

    # Lead Paragraphs
    lead_paragraphs = []
    for p in content_area.find_all(['p', 'h2']):
        t = clean_text(p.get_text(" ", strip=True))
        if t and ("Jalur Rapor adalah" in t or "Terdapat 4 jenis" in t):
            lead_paragraphs.append(t)

    # Extract ARIA-Controls Tabs (.e-n-tabs)
    tabs_dict = extract_aria_control_tabs(content_area)

    rapor_by_tabs = {}

    for tab_title, panel_soup in tabs_dict.items():
        tab_blocks = []

        for el in panel_soup.find_all(['h2', 'h3', 'h4', 'h5', 'p', 'ul', 'ol', 'table']):
            # Skip elements inside a table to prevent raw text duplication
            if el.find_parent('table'):
                continue

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

        rapor_by_tabs[tab_title] = tab_blocks

    # Save JSON
    json_path = os.path.join(rapor_dir, "rapor_all_tabs.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(rapor_by_tabs, f, indent=2, ensure_ascii=False)

    # Save Markdown Knowledge Base
    md_path = os.path.join(rapor_dir, "rapor_knowledge_base.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("# BASIS DATA JALUR SELEKSI RAPOR PMB UII TA 2026/2027\n\n")
        
        for lp in lead_paragraphs:
            f.write(f"_{lp}_\n\n")
        f.write("---\n\n")

        for tname, blocks in rapor_by_tabs.items():
            f.write(f"# KATEGORI TAB JALUR RAPOR: {tname.upper()}\n\n")
            if blocks:
                for b in blocks:
                    f.write(f"{b['content']}\n\n")
            else:
                f.write("_Informasi Jalur Rapor kategori ini tersedia di portal admisi.uii.ac.id._\n\n")
            f.write("---\n\n")

    print(f"[+] Scraped Jalur Rapor cleanly across {len(rapor_by_tabs)} ARIA tabs with timeline tables.")
    print(f"[+] Output JSON: {json_path}")
    print(f"[+] Output Markdown Knowledge Base: {md_path}")

if __name__ == "__main__":
    scrape_rapor_page()

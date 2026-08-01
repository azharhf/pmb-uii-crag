import os
import json
import requests
from bs4 import BeautifulSoup
from common_utils import remove_site_noise, extract_table_with_icons, clean_text

def scrape_prodi_page():
    url = "https://pmb.uii.ac.id/prodi/"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }

    print(f"[+] Scraping Study Programs & Accreditation from {url}...")
    resp = requests.get(url, headers=headers, timeout=15)
    resp.encoding = 'utf-8'

    if resp.status_code != 200:
        print(f"[!] Error fetching page: {resp.status_code}")
        return

    soup = BeautifulSoup(resp.text, 'html.parser')
    soup = remove_site_noise(soup)

    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    prodi_dir = os.path.join(base_dir, "data", "processed", "prodi")
    os.makedirs(prodi_dir, exist_ok=True)

    tables = soup.find_all('table')
    print(f"[+] Found {len(tables)} tables on prodi page.")

    fakultas_data = []

    for i, table in enumerate(tables):
        # Determine preceding faculty heading
        title = f"Fakultas / Kelompok {i+1}"
        curr = table
        for _ in range(8):
            curr = curr.find_previous(['h2', 'h3', 'h4', 'h5', 'p', 'div', 'button', 'a'])
            if curr:
                txt = clean_text(curr.get_text(" ", strip=True))
                if txt and ("Fakultas" in txt or "Program" in txt) and len(txt) < 80:
                    title = txt
                    break

        rows = extract_table_with_icons(table)

        if rows:
            fakultas_data.append({
                "fakultas_name": title,
                "table": rows
            })

    # Output JSON
    json_path = os.path.join(prodi_dir, "prodi_accreditation.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(fakultas_data, f, indent=2, ensure_ascii=False)

    # Output Markdown Knowledge Base
    md_path = os.path.join(prodi_dir, "prodi_knowledge_base.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("# INFORMASI DAFTAR PROGRAM STUDI, JENJANG, & AKREDITASI NASIONAL/INTERNASIONAL UII\n\n")
        f.write("Dokumen ini berisi informasi resmi seluruh Program Studi, Jenjang (D3, D4, S1, S2), Program Reguler / Internasional (IP), RPL, dan Akreditasi BAN-PT & Akreditasi Internasional (Unggul, ACCA, FIBAA, ASIIN, RSC, dll.).\n\n")

        for item in fakultas_data:
            f.write(f"## {item['fakultas_name'].upper()}\n\n")
            for idx, row in enumerate(item['table']):
                f.write("| " + " | ".join(row) + " |\n")
                if idx == 0:
                    f.write("| " + " | ".join([":---"] * len(row)) + " |\n")
            f.write("\n---\n\n")

    print(f"[+] Scraped {len(fakultas_data)} Faculties successfully.")
    print(f"[+] Output JSON: {json_path}")
    print(f"[+] Output Markdown Knowledge Base: {md_path}")

if __name__ == "__main__":
    scrape_prodi_page()

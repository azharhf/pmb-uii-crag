import os
import json
import requests
from bs4 import BeautifulSoup
from common_utils import remove_site_noise, convert_links_to_markdown, clean_text

def scrape_kontak_page():
    url = "https://pmb.uii.ac.id/kontak/"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }

    print(f"[+] Scraping Contacts & Directories from {url}...")
    resp = requests.get(url, headers=headers, timeout=15)
    resp.encoding = 'utf-8'

    if resp.status_code != 200:
        print(f"[!] Error fetching Kontak page: {resp.status_code}")
        return

    soup = BeautifulSoup(resp.text, 'html.parser')
    soup = remove_site_noise(soup)
    soup = convert_links_to_markdown(soup)

    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    kontak_dir = os.path.join(base_dir, "data", "processed", "kontak")
    os.makedirs(kontak_dir, exist_ok=True)

    content_area = soup.find('main') or soup.find(class_=lambda c: c and 'entry-content' in str(c)) or soup

    # Section 1: Layanan Kontak Utama (PMB, CILACS, Beasiswa, Pondok Pesantren)
    primary_services = [
        {
            "name": "Layanan Penerimaan Mahasiswa Baru (PMB)",
            "details": "Gedung KHA Wahid Hasyim, Fakultas Ilmu Agama Islam, Kampus Terpadu Universitas Islam Indonesia, Jl. Kaliurang km. 14,5 Sleman, Yogyakarta 55584.\n- **Jam Buka**: Senin s/d Jumat, 08.00 - 16.00 WIB\n- **Situs Web**: [pmb.uii.ac.id](https://pmb.uii.ac.id)\n- **Email**: admisi@uii.ac.id\n- **WhatsApp**: 0811 260 8844\n- **Telepon**: (0274) 898444 ext. 1234, Faks. (0274) 898459"
        },
        {
            "name": "Pelatihan Bahasa (CILACS - Center for International Languages & Cultural Studies)",
            "details": "Bagi yang belum memiliki sertifikat kemampuan berbahasa Inggris dapat melakukan English Proficiency Test (CEPT, TOEFL ITP, atau TOEFL iBT) di CILACS.\n- **Kantor 1**: Kampus UII Demangan, Jl. Demangan Baru No. 24, Yogyakarta, telp. (0274) 540255\n- **Kantor 2**: Kampus UII Terpadu, Jl. Kaliurang KM. 14,5, Yogyakarta, telp. (0274) 4547153\n- **Situs Web**: [cilacs.uii.ac.id](https://cilacs.uii.ac.id)\n- **Email**: cilacs@uii.ac.id"
        },
        {
            "name": "Informasi Beasiswa (Direktorat Pembinaan Kemahasiswaan)",
            "details": "Gedung GBPH Prabuningrat (Kantor Rektorat UII) Lantai 2, Kampus Terpadu UII, Jl. Kaliurang km. 14,5 Sleman Yogyakarta 55584.\n- **Telepon**: 0274-898444 ext. 1212\n- **Situs Web**: [kemahasiswaan.uii.ac.id](https://kemahasiswaan.uii.ac.id)\n- **Email**: kemahasiswaan@uii.ac.id"
        },
        {
            "name": "Direktorat Pondok Pesantren UII",
            "details": "Jl. Selokan Mataram, Dabag, Condong Catur, Sleman, Yogyakarta 55281.\n- **Telepon**: (0274) 488559"
        }
    ]

    # Section 2: Rektorat & 8 Fakultas Directory
    units_data = []
    current_unit = "Rektorat UII"
    current_entries = []

    for element in content_area.find_all(['h2', 'h3', 'h4', 'h5', 'p', 'div']):
        txt = clean_text(element.get_text(" ", strip=True))
        if not txt:
            continue

        if ("Rektorat" in txt or "Fakultas" in txt) and len(txt) < 60:
            if current_entries:
                units_data.append({
                    "unit": current_unit,
                    "contacts": current_entries
                })
                current_entries = []
            current_unit = txt
            continue

        if any(keyword in txt for keyword in ["Telp:", "Email:", "Situs web:", "Alamat:", "0274", "Gedung"]):
            if txt not in current_entries and len(txt) > 10:
                current_entries.append(txt)

    if current_entries:
        units_data.append({
            "unit": current_unit,
            "contacts": current_entries
        })

    # Save JSON
    json_path = os.path.join(kontak_dir, "kontak_uii.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump({
            "primary_services": primary_services,
            "faculty_directories": units_data
        }, f, indent=2, ensure_ascii=False)

    # Save Markdown Knowledge Base matching Gambar 2
    md_path = os.path.join(kontak_dir, "kontak_knowledge_base.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("# DIREKTORI RESMI KONTAK REKTORAT, FAKULTAS, & LAYANAN PMB UII TA 2026/2027\n\n")
        f.write("Dokumen ini memuat informasi kontak resmi Layanan PMB, CILACS, Beasiswa, Pondok Pesantren, Rektorat, dan seluruh 8 Fakultas di UII.\n\n")

        f.write("##  SECTION 1: LAYANAN KONTAK UTAMA PMB UII\n\n")
        for s in primary_services:
            f.write(f"###  {s['name']}\n")
            f.write(f"{s['details']}\n\n")
        f.write("---\n\n")

        f.write("##  SECTION 2: DIREKTORI REKTORAT & FAKULTAS UII\n\n")
        for u in units_data:
            f.write(f"###  {u['unit'].upper()}\n")
            for c in u['contacts']:
                f.write(f"- {c}\n")
            f.write("\n")
        f.write("---\n\n")

    print(f"[+] Scraped Kontak page cleanly matching Gambar 2 layout.")
    print(f"[+] Output JSON: {json_path}")
    print(f"[+] Output Markdown Knowledge Base: {md_path}")

if __name__ == "__main__":
    scrape_kontak_page()

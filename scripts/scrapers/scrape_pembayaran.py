import os
import json
import requests
from bs4 import BeautifulSoup
from common_utils import remove_site_noise, convert_links_to_markdown, clean_text

def scrape_pembayaran_page():
    url = "https://pmb.uii.ac.id/pembayaran/"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }

    print(f"[+] Scraping Payment Instructions from {url}...")
    resp = requests.get(url, headers=headers, timeout=15)
    resp.encoding = 'utf-8'

    if resp.status_code != 200:
        print(f"[!] Error fetching Payment page: {resp.status_code}")
        return

    soup = BeautifulSoup(resp.text, 'html.parser')
    soup = remove_site_noise(soup)
    soup = convert_links_to_markdown(soup)

    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    pembayaran_dir = os.path.join(base_dir, "data", "processed", "pembayaran")
    os.makedirs(pembayaran_dir, exist_ok=True)

    pdf_dir = os.path.join(pembayaran_dir, "pdf_guides")
    pdf_bsn_path = os.path.join(pdf_dir, "Petunjuk-Pembayaran-Bank-Syariah-Nasional-BSN.pdf")
    pdf_bca_path = os.path.join(pdf_dir, "Panduan-Transfer-VA-UII-BCA-Syariah.pdf")

    main = soup.find(id='main') or soup

    top_con = None
    for con in main.find_all('div', class_=lambda c: c and 'e-con' in str(c)):
        if len(con.find_all(['ol', 'ul'])) > 10:
            top_con = con
            break

    if not top_con:
        top_con = main

    bank_blocks = []
    current_bank = "Bank Mandiri"
    current_method = "Petunjuk Pembayaran"

    known_banks = [
        "Bank Mandiri",
        "BSI (Bank Syariah Indonesia)",
        "BSI",
        "Bank Syariah Nasional",
        "Bank BCA Syariah",
        "Bank BPD DIY",
        "Bank BPD DIY Syariah",
        "Bank Bukopin",
        "Bank Muamalat"
    ]

    for el in top_con.find_all(['ul', 'ol', 'p', 'strong', 'h2', 'h3', 'h4', 'h5']):
        txt = clean_text(el.get_text(" ", strip=True))
        if not txt:
            continue

        is_bank_header = False
        for kb in known_banks:
            if txt == kb or (len(txt) < 35 and kb in txt and not any(w in txt for w in ["Pilih", "Login", "Masukkan", "Untuk", "Informasi", "Datang", "Melalui"])):
                current_bank = kb
                current_method = "Petunjuk Pembayaran"
                is_bank_header = True
                break

        if is_bank_header:
            continue

        if any(m in txt for m in ["VIA", "MELALUI", "PETUNJUK", "BAYAR/BELI", "PENDIDIKAN"]) and len(txt) < 70 and el.name not in ['ol']:
            if not any(stop_w in txt for stop_w in ["Informasi", "Selalu", "Peta"]):
                current_method = txt
                continue

        if el.name in ['ol', 'ul']:
            steps = [clean_text(li.get_text(" ", strip=True)) for li in el.find_all('li') if clean_text(li.get_text(" ", strip=True))]
            if steps and len(steps[0]) > 5:
                if any(steps[0] == kb for kb in known_banks):
                    continue

                bank_blocks.append({
                    "bank": current_bank,
                    "method": current_method,
                    "steps": steps
                })

    # PDF Guides Info matching Gambar 3
    pdf_guides_info = [
        {
            "bank": "Bank Syariah Nasional (BSN)",
            "method": "Petunjuk Pembayaran PDF",
            "pdf_link": f"[Petunjuk Pembayaran BSN PDF]({pdf_bsn_path.replace(os.sep, '/')})",
            "note": "Panduan lengkap pembayaran melalui Bank Syariah Nasional terlampir pada tautan dokumen PDF di atas."
        },
        {
            "bank": "Bank BCA Syariah",
            "method": "Panduan Transfer Virtual Account (VA) PDF",
            "pdf_link": f"[Panduan Transfer VA BCA Syariah PDF]({pdf_bca_path.replace(os.sep, '/')})",
            "note": "Panduan lengkap pembayaran melalui Bank BCA Syariah terlampir pada tautan dokumen PDF di atas."
        }
    ]

    # Save JSON
    json_path = os.path.join(pembayaran_dir, "pembayaran_bank.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump({
            "bank_steps": bank_blocks,
            "pdf_guides": pdf_guides_info
        }, f, indent=2, ensure_ascii=False)

    # Group steps strictly by bank
    bank_grouped = {}
    for item in bank_blocks:
        bname = item["bank"]
        if "BSI" in bname:
            bname = "BSI (Bank Syariah Indonesia)"
        elif "BPD" in bname:
            bname = "Bank BPD DIY"
        elif "Bukopin" in bname:
            bname = "Bank KB Bukopin"
        
        if bname not in bank_grouped:
            bank_grouped[bname] = []
        bank_grouped[bname].append(item)

    # Save Markdown Knowledge Base matching Gambar 3 layout
    md_path = os.path.join(pembayaran_dir, "pembayaran_knowledge_base.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("# BASIS DATA PETUNJUK TATA CARA PEMBAYARAN PMB UII TA 2026/2027\n\n")
        f.write("Dokumen resmi ini berisi langkah-langkah tata cara pembayaran biaya formulir & registrasi UII melalui Bank Mandiri, BSI, Bank Muamalat, BSN, BCA Syariah, BPD DIY, dan KB Bukopin.\n\n")

        # 1. Bank Mandiri
        if "Bank Mandiri" in bank_grouped:
            f.write("##  1. BANK MANDIRI\n\n")
            for m in bank_grouped["Bank Mandiri"]:
                f.write(f"###  {m['method']}\n")
                for idx, step in enumerate(m['steps']):
                    f.write(f"{idx+1}. {step}\n")
                f.write("\n")
            f.write("---\n\n")

        # 2. BSI
        if "BSI (Bank Syariah Indonesia)" in bank_grouped:
            f.write("##  2. BSI (BANK SYARIAH INDONESIA)\n\n")
            for m in bank_grouped["BSI (Bank Syariah Indonesia)"]:
                f.write(f"###  {m['method']}\n")
                for idx, step in enumerate(m['steps']):
                    f.write(f"{idx+1}. {step}\n")
                f.write("\n")
            f.write("---\n\n")

        # 3. Bank Muamalat
        if "Bank Muamalat" in bank_grouped:
            f.write("##  3. BANK MUAMALAT\n\n")
            for m in bank_grouped["Bank Muamalat"]:
                f.write(f"###  {m['method']}\n")
                for idx, step in enumerate(m['steps']):
                    f.write(f"{idx+1}. {step}\n")
                f.write("\n")
            f.write("---\n\n")

        # 4. Bank Syariah Nasional (BSN) PDF
        f.write("##  4. BANK SYARIAH NASIONAL (BSN)\n\n")
        f.write("###  PETUNJUK PEMBAYARAN BSN PDF\n")
        f.write(f"-  Dokumen Resmi: {pdf_guides_info[0]['pdf_link']}\n")
        f.write(f"- {pdf_guides_info[0]['note']}\n\n---\n\n")

        # 5. Bank BCA Syariah PDF
        f.write("##  5. BANK BCA SYARIAH\n\n")
        f.write("###  PANDUAN TRANSFER VIRTUAL ACCOUNT (VA) BCA SYARIAH PDF\n")
        f.write(f"-  Dokumen Resmi: {pdf_guides_info[1]['pdf_link']}\n")
        f.write(f"- {pdf_guides_info[1]['note']}\n\n---\n\n")

        # 6. Bank BPD DIY
        if "Bank BPD DIY" in bank_grouped:
            f.write("##  6. BANK BPD DIY\n\n")
            for m in bank_grouped["Bank BPD DIY"]:
                f.write(f"###  {m['method']}\n")
                for idx, step in enumerate(m['steps']):
                    f.write(f"{idx+1}. {step}\n")
                f.write("\n")
            f.write("---\n\n")

        # 7. Bank KB Bukopin
        if "Bank KB Bukopin" in bank_grouped:
            f.write("##  7. BANK KB BUKOPIN\n\n")
            for m in bank_grouped["Bank KB Bukopin"]:
                f.write(f"###  {m['method']}\n")
                for idx, step in enumerate(m['steps']):
                    f.write(f"{idx+1}. {step}\n")
                f.write("\n")
            f.write("---\n\n")

    print(f"[+] Scraped Payment Instructions cleanly matching Gambar 3 layout with exact bank DOM isolation.")
    print(f"[+] Output JSON: {json_path}")
    print(f"[+] Output Markdown Knowledge Base: {md_path}")

if __name__ == "__main__":
    scrape_pembayaran_page()

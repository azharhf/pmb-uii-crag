import os
import json
import re
import requests

def scrape_biaya_page():
    """
    Scraper Resmi Biaya PMB UII (100% Dynamic & Official API Pipeline)
    Mengambil data Uang Kuliah Awal (UKA) dan Uang Kuliah Kuartal (UKK) untuk
    seluruh Program Studi di UII secara langsung dari API Backend Server UII.
    """
    url_page = "https://pmb.uii.ac.id/biaya/"
    base_uka = "https://pmb.uii.ac.id/programstudi/uka.php?prodi="
    base_ukk = "https://pmb.uii.ac.id/programstudi/ukk.php?prodi2="

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    print("[+] Scraping Tuition Fees (UKA & UKK) from Official UII API...")
    resp = requests.get(url_page, headers=headers)
    html = resp.text

    prodi_names = re.findall(r"uka\.php\?prodi=([^'\"]+)", html)
    unique_prodis = []
    for p in prodi_names:
        p_clean = p.strip()
        if p_clean and p_clean not in unique_prodis:
            unique_prodis.append(p_clean)

    print(f"[+] Found {len(unique_prodis)} official study programs.")

    all_prodi_data = []

    for prodi in unique_prodis:
        try:
            # Try fetching with retry on timeout
            for attempt in range(2):
                try:
                    uka_resp = requests.get(base_uka + prodi, headers=headers, timeout=15).json()
                    ukk_resp = requests.get(base_ukk + prodi, headers=headers, timeout=15).json()
                    break
                except Exception:
                    if attempt == 1:
                        raise

            if "error" not in uka_resp and "error" not in ukk_resp:
                all_prodi_data.append({
                    "prodi_name": prodi,
                    "jenjang": ukk_resp.get("jenjang", "S1"),
                    "uka_rankings": {
                        "Peringkat 1": float(uka_resp.get("rank1", 0)),
                        "Peringkat 2": float(uka_resp.get("rank2", 0)),
                        "Peringkat 3": float(uka_resp.get("rank3", 0)),
                        "Peringkat 4": float(uka_resp.get("rank4", 0)),
                        "Peringkat 5": float(uka_resp.get("rank5", 0)),
                        "Peringkat 6": float(uka_resp.get("rank6", 0))
                    },
                    "cost_per_quarter": float(ukk_resp.get("cost_per_quarter", 0)),
                    "total_biaya_estimasi": float(ukk_resp.get("total_biaya", 0)),
                    "currency": ukk_resp.get("currency", "IDR")
                })
        except Exception as e:
            print(f"[!] Error fetching {prodi}: {e}")

    # Output to data/biaya/
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    biaya_dir = os.path.join(base_dir, "data", "processed", "biaya")
    os.makedirs(biaya_dir, exist_ok=True)

    json_path = os.path.join(biaya_dir, "biaya_pmb_clean.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(all_prodi_data, f, indent=2, ensure_ascii=False)

    md_path = os.path.join(biaya_dir, "biaya_pmb_knowledge_base.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("# BASIS DATA RESMI BIAYA KULIAH SELURUH PROGRAM STUDI UII (PMB TA 2026/2027)\n\n")
        f.write("Dokumen resmi ini diekstrak secara otomatis murni dari API Backend Resmi PMB UII (https://pmb.uii.ac.id/programstudi/uka.php & ukk.php).\n\n")

        for item in all_prodi_data:
            f.write(f"## PROGRAM STUDI: {item['prodi_name'].upper()} ({item['jenjang']})\n\n")
            f.write("### 1. Uang Kuliah Awal (UKA)\n")
            f.write("| Peringkat Seleksi | Nominal UKA (Rp) |\n")
            f.write("| :--- | :--- |\n")
            for rank, val in item['uka_rankings'].items():
                f.write(f"| {rank} | Rp {val:,.0f} |\n".replace(",", "."))
            f.write("\n")

            f.write("### 2. Uang Kuliah Kuartal (UKK)\n")
            f.write(f"- **Nominal per Kuartal**: Rp {item['cost_per_quarter']:,.0f}\n".replace(",", "."))
            f.write(f"- **Estimasi Total UKK (4 Tahun)**: Rp {item['total_biaya_estimasi']:,.0f}\n\n".replace(",", "."))
            f.write("---\n\n")

    print(f"[+] Scraped {len(all_prodi_data)} prodi tuition fees successfully.")
    print(f"[+] Output JSON: {json_path}")
    print(f"[+] Output Markdown Knowledge Base: {md_path}")

if __name__ == "__main__":
    scrape_biaya_page()

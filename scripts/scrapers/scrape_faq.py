import os
import json
import requests
from bs4 import BeautifulSoup
from common_utils import remove_site_noise, convert_links_to_markdown, extract_eael_tabs, clean_text

def scrape_faq_page():
    url = "https://pmb.uii.ac.id/faq/"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }

    print(f"[+] Scraping PMB UII FAQ from {url}...")
    resp = requests.get(url, headers=headers, timeout=15)
    resp.encoding = 'utf-8'

    if resp.status_code != 200:
        print(f"[!] Error fetching FAQ page: {resp.status_code}")
        return

    soup = BeautifulSoup(resp.text, 'html.parser')
    soup = remove_site_noise(soup)
    soup = convert_links_to_markdown(soup)

    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    faq_dir = os.path.join(base_dir, "data", "processed", "faq")
    os.makedirs(faq_dir, exist_ok=True)

    content_area = soup.find('main') or soup.find(class_=lambda c: c and 'entry-content' in str(c)) or soup

    # Lead Intro Paragraph
    lead_text = ""
    lead_p = content_area.find(['p', 'h2'])
    if lead_p:
        lead_text = clean_text(lead_p.get_text(" ", strip=True))

    # Extract EAEL Tabs (.eael-advance-tabs)
    eael_tabs_dict = extract_eael_tabs(content_area)

    faq_by_tabs = {}

    for tab_title, panel_soup in eael_tabs_dict.items():
        qa_pairs = []

        # Find accordion headers inside panel
        acc_headers = panel_soup.select('.eael-accordion-header, .elementor-tab-title')
        acc_contents = panel_soup.select('.eael-accordion-content, .elementor-tab-content')

        if len(acc_headers) > 0 and len(acc_contents) >= len(acc_headers):
            for i, h_el in enumerate(acc_headers):
                q_text = clean_text(h_el.get_text(" ", strip=True))
                a_text = clean_text(acc_contents[i].get_text(" ", strip=True)) if i < len(acc_contents) else ""
                if q_text:
                    qa_pairs.append({
                        "question": q_text,
                        "answer": a_text
                    })
        else:
            # Fallback paragraph parser inside panel
            raw_text = clean_text(panel_soup.get_text(" ", strip=True))
            if raw_text:
                qa_pairs.append({
                    "question": f"Informasi {tab_title}",
                    "answer": raw_text
                })

        faq_by_tabs[tab_title] = qa_pairs

    # Save JSON
    json_path = os.path.join(faq_dir, "faq_all_tabs.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(faq_by_tabs, f, indent=2, ensure_ascii=False)

    # Save Markdown Knowledge Base
    md_path = os.path.join(faq_dir, "faq_knowledge_base.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("# BASIS DATA FAQ (PERTANYAAN SERING DITANYAKAN) PMB UII TA 2026/2027\n\n")
        if lead_text:
            f.write(f"_{lead_text}_\n\n---\n\n")

        for tname, items in faq_by_tabs.items():
            f.write(f"# KATEGORI TAB FAQ: {tname.upper()}\n\n")
            if items:
                for item in items:
                    f.write(f"###  Pertanyaan: {item['question']}\n")
                    f.write(f" **Jawaban**: {item['answer'] if item['answer'] else 'Informasi lengkap dapat diakses via portal admisi.uii.ac.id.'}\n\n")
            else:
                f.write("_Informasi FAQ kategori ini tersedia di portal admisi.uii.ac.id._\n\n")
            f.write("---\n\n")

    total_qa = sum(len(v) for v in faq_by_tabs.values())
    print(f"[+] Scraped {total_qa} FAQ Q&A pairs across {len(faq_by_tabs)} EAEL tabs.")
    print(f"[+] Output JSON: {json_path}")
    print(f"[+] Output Markdown Knowledge Base: {md_path}")

if __name__ == "__main__":
    scrape_faq_page()

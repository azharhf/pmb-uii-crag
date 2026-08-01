import os
import sys

scrapers_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(scrapers_dir)

from scrape_biaya import scrape_biaya_page
from scrape_prodi import scrape_prodi_page
from scrape_faq import scrape_faq_page
from scrape_pembayaran import scrape_pembayaran_page
from scrape_kontak import scrape_kontak_page
from scrape_rapor import scrape_rapor_page
from scrape_tes import scrape_tes_page
from scrape_beasiswa import scrape_beasiswa_page
from scrape_soal import scrape_soal_page

def run_all():
    print("==========================================================")
    print("[+] MASTER SCRAPER RUNNER - ALL PMB UII KNOWLEDGE MODULES")
    print("==========================================================")

    print("\n---> MODULE 1: Tuition Fees (UKA & UKK API)")
    scrape_biaya_page()

    print("\n---> MODULE 2: Study Programs & Accreditation")
    scrape_prodi_page()

    print("\n---> MODULE 3: FAQ Across All Tabs")
    scrape_faq_page()

    print("\n---> MODULE 4: Bank Payment Instructions")
    scrape_pembayaran_page()

    print("\n---> MODULE 5: Contacts & Directory")
    scrape_kontak_page()

    print("\n---> MODULE 6: Jalur Rapor (All 4 Tabs)")
    scrape_rapor_page()

    print("\n---> MODULE 7: Jalur Tes (CBT - All 3 Tabs)")
    scrape_tes_page()

    print("\n---> MODULE 8: Jalur Beasiswa (All 6 Tabs)")
    scrape_beasiswa_page()

    print("\n---> MODULE 9: Contoh Soal & Pemetaan Materi")
    scrape_soal_page()

    print("\n==========================================================")
    print("[+] ALL 9 MODULE SCRAPERS COMPLETED SUCCESSFULLY!")
    print("==========================================================")

if __name__ == "__main__":
    run_all()

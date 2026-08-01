import os
import requests
import glob
from dotenv import load_dotenv

# Load environment variables
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(base_dir, ".env"))

url = os.getenv("SUPABASE_URL", "https://idrhzigiaewgtqexfgbj.supabase.co").rstrip("/")
service_key = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_ANON_KEY")

if not service_key:
    print("[!] Service key missing in .env")
    exit(1)

headers = {
    "Authorization": f"Bearer {service_key}",
    "apiKey": service_key
}

bucket_name = "pmb-documents"

# Ensure bucket exists
print(f"[+] Verifying bucket '{bucket_name}'...")
res_bucket = requests.get(f"{url}/storage/v1/bucket/{bucket_name}", headers=headers)
if res_bucket.status_code != 200:
    print(f"[+] Bucket '{bucket_name}' not found. Creating public bucket...")
    create_res = requests.post(
        f"{url}/storage/v1/bucket",
        headers={**headers, "Content-Type": "application/json"},
        json={"id": bucket_name, "name": bucket_name, "public": True}
    )
    print("    Create result:", create_res.status_code, create_res.text)

print(f"\n[+] Uploading all PDF, DOCX, and MD files to Supabase Storage '{bucket_name}'...\n")

uploaded_count = 0

# 1. Upload Master MD Files
md_files = glob.glob(os.path.join(base_dir, "data", "processed", "**", "*.md"), recursive=True)
for fp in md_files:
    fname = os.path.basename(fp)
    storage_path = f"master_md/{fname}"
    with open(fp, "rb") as f:
        file_data = f.read()
    up_res = requests.post(
        f"{url}/storage/v1/object/{bucket_name}/{storage_path}",
        headers={**headers, "Content-Type": "text/markdown", "x-upsert": "true"},
        data=file_data
    )
    public_cdn_url = f"{url}/storage/v1/object/public/{bucket_name}/{storage_path}"
    print(f"  [MD] {fname} ({up_res.status_code}) -> {public_cdn_url}")
    uploaded_count += 1

# 2. Upload PDF Brochures
pdf_files = glob.glob(os.path.join(base_dir, "data", "raw", "brosur", "pdf", "*.pdf"))
for fp in pdf_files:
    fname = os.path.basename(fp)
    storage_path = f"pdf/{fname}"
    with open(fp, "rb") as f:
        file_data = f.read()
    up_res = requests.post(
        f"{url}/storage/v1/object/{bucket_name}/{storage_path}",
        headers={**headers, "Content-Type": "application/pdf", "x-upsert": "true"},
        data=file_data
    )
    public_cdn_url = f"{url}/storage/v1/object/public/{bucket_name}/{storage_path}"
    print(f"  [PDF] {fname} ({up_res.status_code}) -> {public_cdn_url}")
    uploaded_count += 1

# 3. Upload Unduh Dokumen (PDF & DOCX)
unduh_files = glob.glob(os.path.join(base_dir, "data", "raw", "unduh_dokumen", "**", "*.*"), recursive=True)
for fp in unduh_files:
    if fp.lower().endswith((".pdf", ".docx", ".doc")):
        fname = os.path.basename(fp)
        rel_dir = os.path.relpath(os.path.dirname(fp), os.path.join(base_dir, "data", "raw", "unduh_dokumen")).replace("\\", "/")
        storage_path = f"unduh/{rel_dir}/{fname}".replace("//", "/")
        content_type = "application/pdf" if fname.lower().endswith(".pdf") else "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        with open(fp, "rb") as f:
            file_data = f.read()
        up_res = requests.post(
            f"{url}/storage/v1/object/{bucket_name}/{storage_path}",
            headers={**headers, "Content-Type": content_type, "x-upsert": "true"},
            data=file_data
        )
        public_cdn_url = f"{url}/storage/v1/object/public/{bucket_name}/{storage_path}"
        print(f"  [UNDUH] {fname} ({up_res.status_code}) -> {public_cdn_url}")
        uploaded_count += 1

print(f"\n[SUCCESS] Total {uploaded_count} files uploaded to Supabase Storage bucket '{bucket_name}'!")

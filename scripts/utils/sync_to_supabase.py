import os
import json
import sys
import time
import numpy as np
from dotenv import load_dotenv

sys.stdout.reconfigure(encoding='utf-8')

# Load environment variables securely from root .env
base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
env_path = os.path.join(base_dir, ".env")
load_dotenv(env_path)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_ANON_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("[!] Error: SUPABASE_URL and SUPABASE_ANON_KEY environment variables must be defined in .env")
    sys.exit(1)

try:
    from supabase import create_client, Client
    supabase_client: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
except ImportError:
    print("[!] Error: supabase-py library not installed. Install via `pip install supabase`")
    sys.exit(1)


def extract_indobert_vectors(texts):
    """Generates 768-dimensional dense vector embeddings using IndoBERT Base P1 Transformer."""
    import torch
    from transformers import AutoTokenizer, AutoModel

    model_name = "indobenchmark/indobert-base-p1"
    print(f"[+] Loading IndoBERT Model: '{model_name}'...")
    
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModel.from_pretrained(model_name)
    model.eval()

    embeddings = []
    with torch.no_grad():
        for i, text in enumerate(texts):
            inputs = tokenizer(text[:512], return_tensors="pt", truncation=True, max_length=128, padding=True)
            outputs = model(**inputs)
            emb = outputs.last_hidden_state.mean(dim=1).squeeze().numpy()
            embeddings.append(emb)
            if (i + 1) % 50 == 0 or (i + 1) == len(texts):
                print(f"    - Vectorized {i + 1}/{len(texts)} chunks...")

    return np.array(embeddings)


def run_supabase_sync():
    """Reads 603 dataset sections, vectorizes them with IndoBERT, and upserts to Supabase pmb_sections table."""
    dataset_json_path = os.path.join(base_dir, "outputs", "reports", "preprocessed_nlp_dataset.json")

    if not os.path.exists(dataset_json_path):
        print(f"[!] Preprocessed dataset file not found at: {dataset_json_path}")
        return

    with open(dataset_json_path, "r", encoding="utf-8") as f:
        dataset_info = json.load(f)

    sections = dataset_info.get("data", [])
    print(f"[+] Loaded {len(sections)} sections from {dataset_json_path}")

    texts = [s.get("contextual_text", s.get("preprocessed_text", "")).strip() for s in sections]
    embeddings = extract_indobert_vectors(texts)

    payloads = []
    for idx, (sec, emb) in enumerate(zip(sections, embeddings)):
        doc_id = sec.get("doc_id", f"DOC-{idx+1:03d}")
        module = sec.get("module", "UNKNOWN")
        section_title = sec.get("section_title", "Untitled Section")
        raw_text = sec.get("raw_text", "") or sec.get("preprocessed_text", "")
        preprocessed_text = sec.get("preprocessed_text", "")
        vector_list = [round(float(v), 6) for v in emb]

        payloads.append({
            "doc_id": doc_id,
            "module": module,
            "section_title": section_title,
            "raw_text": raw_text,
            "preprocessed_text": preprocessed_text,
            "embedding": vector_list
        })

    print(f"\n[+] Upserting {len(payloads)} vector records to Supabase 'pmb_sections' table...")
    batch_size = 50
    for i in range(0, len(payloads), batch_size):
        batch = payloads[i:i + batch_size]
        try:
            res = supabase_client.table("pmb_sections").upsert(batch, on_conflict="doc_id").execute()
            print(f"    - Upserted batch {i + 1} to {min(i + batch_size, len(payloads))} successfully.")
        except Exception as e:
            print(f"    [!] Error upserting batch {i}: {e}")

    print("\n[+] Supabase vector sync completed successfully!")


if __name__ == "__main__":
    run_supabase_sync()

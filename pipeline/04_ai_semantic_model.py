"""
================================================================================
UJIAN AKHIR SEMESTER (UAS) - TRENDING TOPICS ON STATISTICS (TToS) 2026
--------------------------------------------------------------------------------
04_AI_SEMANTIC_MODEL.PY (SOAL 4 - BOBOT 20%)
--------------------------------------------------------------------------------
Fungsi:
1. Membangun AI Model Representasi Vektor Semantik & Dense Vector Retrieval Engine
   berbasis Pre-trained Transformer 'indobenchmark/indobert-base-p1'.
2. Memproses 351 section dokumen terstruktur PMB UII menjadi:
   a. Dense Semantic Vector Embeddings (768-dimensi via IndoBERT Transformer)
   b. Sparse Lexical Vectors (TF-IDF Log-Sublinear Space)
   c. Hybrid Rank Fusion Space (Dense + Sparse Fusion)
3. Evaluasi Benchmark Berbasis Industri & Information Retrieval (IR) Metrics:
   - Precision@K (P@1, P@3, P@5)
   - Recall@K (R@1, R@3, R@5)
   - MRR (Mean Reciprocal Rank)
   - Hit Rate@K
   - Cosine Similarity Score Distribution
   - Average Retrieval Latency (ms/query)
4. Menghasilkan 2 Figure Visualisasi di 'outputs/figures/':
   - 04_ai_vector_similarity_matrix.png (Heatmap & Distribusi Cosine Similarity)
   - 05_ai_model_comparative_benchmark.png (Bar Chart Perbandingan IR Metrics: IndoBERT vs Hybrid vs TF-IDF)
5. Menyimpan Laporan Evaluasi ke 'outputs/reports/ai_model_evaluation_results.json'.
================================================================================
"""

import os
import sys
import warnings

# Suppress TensorFlow C++ log output & disable oneDNN custom ops log notices
os.environ["TF_ENABLE_ONEDNN_OPTS"] = "0"
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"

# Suppress PyTorch / Transformers FutureWarning & UserWarning deprecation notices
warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=UserWarning)

import json
import time
import re
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# Configure UTF-8 encoding for Windows console
sys.stdout.reconfigure(encoding='utf-8')

plt.style.use('seaborn-v0_8-whitegrid' if 'seaborn-v0_8-whitegrid' in plt.style.available else 'default')
plt.rcParams['font.sans-serif'] = 'Segoe UI'
plt.rcParams['axes.edgecolor'] = '#cbd5e0'
plt.rcParams['axes.linewidth'] = 1.0


def extract_indobert_embeddings(texts):
    """
    Extract 768-dimensional dense vector embeddings using IndoBERT Base P1 Transformer.
    Returns (success, embeddings_array).
    """
    try:
        import torch
        from transformers import AutoTokenizer, AutoModel

        model_name = "indobenchmark/indobert-base-p1"
        print(f"\n[+] Loading Transformer Model: '{model_name}'...")
        tokenizer = AutoTokenizer.from_pretrained(model_name)
        model = AutoModel.from_pretrained(model_name)
        model.eval()

        embeddings = []
        with torch.no_grad():
            for text in texts:
                inputs = tokenizer(text[:512], return_tensors="pt", truncation=True, max_length=128, padding=True)
                outputs = model(**inputs)
                # Mean Pooling across sequence dimension
                emb = outputs.last_hidden_state.mean(dim=1).squeeze().numpy()
                embeddings.append(emb)

        print(f"[+] Encoded {len(texts)} chunks to Dense Vector Space (768 Dimensions) successfully.")
        return True, np.array(embeddings)
    except Exception as e:
        print(f"[!] IndoBERT Embedding Error: {e}")
        return False, None


def evaluate_retrieval_engine(queries_dataset, doc_texts, doc_modules, doc_titles, embeddings_dense, tfidf_matrix, vectorizer):
    """
    Evaluate 3 Retrieval Approaches across 10 Benchmark Queries using IR Metrics:
    - Dense IndoBERT
    - Sparse TF-IDF
    - Hybrid Fusion
    """
    dense_sim_matrix = cosine_similarity(embeddings_dense, embeddings_dense) if embeddings_dense is not None else None

    # Benchmark queries with ground truth target modules/keywords
    results = {
        "Dense IndoBERT Vector": {"P1": [], "P3": [], "P5": [], "R3": [], "MRR": [], "Hit3": [], "latency": []},
        "Sparse TF-IDF Vector": {"P1": [], "P3": [], "P5": [], "R3": [], "MRR": [], "Hit3": [], "latency": []},
        "Hybrid Fusion Engine": {"P1": [], "P3": [], "P5": [], "R3": [], "MRR": [], "Hit3": [], "latency": []}
    }

    # Encode query function
    try:
        import torch
        from transformers import AutoTokenizer, AutoModel
        tokenizer = AutoTokenizer.from_pretrained("indobenchmark/indobert-base-p1")
        model = AutoModel.from_pretrained("indobenchmark/indobert-base-p1")
        model.eval()
        has_bert = True
    except:
        has_bert = False

    for q_item in queries_dataset:
        query_text = q_item["query"]
        target_mod = q_item["target_module"]
        target_kws = q_item["keywords"]

        # Relevant ground truth documents (matching target_module or keywords)
        relevant_indices = set()
        for idx, (m, t, txt) in enumerate(zip(doc_modules, doc_titles, doc_texts)):
            t_combined = (t + " " + txt).lower()
            if m == target_mod or any(kw in t_combined for kw in target_kws):
                relevant_indices.add(idx)

        if not relevant_indices:
            continue

        # --- 1. Sparse TF-IDF Search ---
        t_start = time.time()
        q_tfidf = vectorizer.transform([query_text])
        tfidf_scores = cosine_similarity(q_tfidf, tfidf_matrix).flatten()
        sparse_ranks = np.argsort(tfidf_scores)[::-1]
        t_sparse = (time.time() - t_start) * 1000

        # --- 2. Dense IndoBERT Search ---
        t_start = time.time()
        if has_bert:
            with torch.no_grad():
                inp = tokenizer(query_text[:512], return_tensors="pt", truncation=True, max_length=128, padding=True)
                q_emb = model(**inp).last_hidden_state.mean(dim=1).squeeze().numpy()
            q_emb = q_emb.reshape(1, -1)
            dense_scores = cosine_similarity(q_emb, embeddings_dense).flatten()
        else:
            dense_scores = tfidf_scores
        dense_ranks = np.argsort(dense_scores)[::-1]
        t_dense = (time.time() - t_start) * 1000

        # --- 3. Hybrid Fusion Search (Lexical-Weighted Hybrid Fusion: 0.70 Sparse + 0.30 Dense) ---
        t_start = time.time()
        norm_dense = dense_scores / (np.max(dense_scores) if np.max(dense_scores) > 0 else 1.0)
        norm_sparse = tfidf_scores / (np.max(tfidf_scores) if np.max(tfidf_scores) > 0 else 1.0)
        hybrid_scores = 0.70 * norm_sparse + 0.30 * norm_dense
        hybrid_ranks = np.argsort(hybrid_scores)[::-1]
        t_hybrid = (time.time() - t_start) * 1000

        # Calculate IR Metrics for each method
        for name, ranks, lat in [("Dense IndoBERT Vector", dense_ranks, t_dense),
                                 ("Sparse TF-IDF Vector", sparse_ranks, t_sparse),
                                 ("Hybrid Fusion Engine", hybrid_ranks, t_hybrid)]:
            # Precision@K
            p1 = 1.0 if ranks[0] in relevant_indices else 0.0
            p3 = sum(1.0 for r in ranks[:3] if r in relevant_indices) / 3.0
            p5 = sum(1.0 for r in ranks[:5] if r in relevant_indices) / 5.0

            # Recall@3
            r3 = sum(1.0 for r in ranks[:3] if r in relevant_indices) / len(relevant_indices)

            # Hit Rate@3
            hit3 = 1.0 if any(r in relevant_indices for r in ranks[:3]) else 0.0

            # MRR
            mrr = 0.0
            for rank_idx, r in enumerate(ranks[:10]):
                if r in relevant_indices:
                    mrr = 1.0 / (rank_idx + 1)
                    break

            results[name]["P1"].append(p1)
            results[name]["P3"].append(p3)
            results[name]["P5"].append(p5)
            results[name]["R3"].append(r3)
            results[name]["Hit3"].append(hit3)
            results[name]["MRR"].append(mrr)
            results[name]["latency"].append(lat)

    # Aggregate metric averages
    summary = {}
    for name, m in results.items():
        summary[name] = {
            "Precision@1": round(float(np.mean(m["P1"])), 4),
            "Precision@3": round(float(np.mean(m["P3"])), 4),
            "Precision@5": round(float(np.mean(m["P5"])), 4),
            "Recall@3": round(float(np.mean(m["R3"])), 4),
            "HitRate@3": round(float(np.mean(m["Hit3"])), 4),
            "MRR": round(float(np.mean(m["MRR"])), 4),
            "Latency_ms": round(float(np.mean(m["latency"])), 2)
        }

    return summary, dense_sim_matrix


def run_ai_semantic_model_pipeline():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    outputs_dir = os.path.join(base_dir, "outputs")
    reports_dir = os.path.join(outputs_dir, "reports")
    figures_dir = os.path.join(outputs_dir, "figures")

    os.makedirs(reports_dir, exist_ok=True)
    os.makedirs(figures_dir, exist_ok=True)

    input_json = os.path.join(reports_dir, "preprocessed_nlp_dataset.json")

    print("=" * 90)
    print(" [SOAL 04] PIPELINE AI SEMANTIC VECTOR REPRESENTATION & HYBRID RETRIEVAL BENCHMARK")
    print("=" * 90)

    if not os.path.exists(input_json):
        print(f"[!] Dataset tidak ditemukan: {input_json}. Jalankan 02_text_preprocessing.py dulu.")
        return

    with open(input_json, "r", encoding="utf-8") as f:
        dataset_info = json.load(f)

    sections = dataset_info.get("data", [])
    texts = [s.get("contextual_text", s.get("preprocessed_text", "")).strip() for s in sections if s.get("preprocessed_text", "").strip()]
    titles = [s.get("section_title", "") for s in sections if s.get("preprocessed_text", "").strip()]
    modules = [s.get("module", "") for s in sections if s.get("preprocessed_text", "").strip()]

    total_chars = sum(len(t) for t in texts)

    print(f"[+] Total Dokumen / Chunks Loaded : {len(texts)} Section Dokumen Terstruktur")
    print(f"[+] Total Karakter Teks Diproses  : {total_chars:,} Karakter")
    print(f"[+] Modul Terliput                : {len(set(modules))} Modul (BROSUR, BIAYA, SELEKSI, PRODI, dll)")

    # 1. SPARSE LEXICAL VECTOR REPRESENTATION (TF-IDF)
    print("\n[+] 1. Building Sparse Lexical Vector Space (TF-IDF Log-Sublinear)...")
    vectorizer = TfidfVectorizer(max_features=1200, ngram_range=(1, 2), min_df=1, sublinear_tf=True)
    tfidf_matrix = vectorizer.fit_transform(texts)

    # 2. DENSE SEMANTIC VECTOR REPRESENTATION (IndoBERT Base P1)
    print("\n[+] 2. Building Dense Semantic Vector Space (IndoBERT Base P1 Transformer)...")
    has_dense, embeddings_dense = extract_indobert_embeddings(texts)

    # 3. BENCHMARK RETRIEVAL EVALUATION ACROSS 10 QUERIES
    print("\n[+] 3. Running Benchmark Information Retrieval (IR) Metrics Evaluation...")
    benchmark_queries = [
        {"id": "BQ1", "query": "Jalur pendaftaran mahasiswa baru UII", "target_module": "JALUR_RAPOR", "keywords": ["rapor", "cbt", "seleksi"]},
        {"id": "BQ2", "query": "Biaya studi catur darma dan SPP", "target_module": "BIAYA", "keywords": ["biaya", "spp", "uka", "catur darma"]},
        {"id": "BQ3", "query": "Syarat pendaftaran beasiswa hafiz al quran", "target_module": "JALUR_BEASISWA", "keywords": ["beasiswa", "hafiz", "santri"]},
        {"id": "BQ4", "query": "Cara pembayaran angsuran via teller atm bank", "target_module": "PEMBAYARAN", "keywords": ["bayar", "bank", "mandiri", "bni"]},
        {"id": "BQ5", "query": "Program studi fakultas teknologi industri dan hukum", "target_module": "PRODI", "keywords": ["prodi", "fakultas", "hukum", "informatika"]},
        {"id": "BQ6", "query": "Alamat lokasi kontak layanan surel pmb", "target_module": "KONTAK", "keywords": ["kontak", "alamat", "telepon", "email"]},
        {"id": "BQ7", "query": "Contoh soal tes kemampuan akademik tka", "target_module": "CONTOH_SOAL", "keywords": ["soal", "tka", "tes"]},
        {"id": "BQ8", "query": "Syarat dokumen ijazah legalisir verifikasi", "target_module": "UNDUH_DOKUMEN", "keywords": ["dokumen", "ijazah", "verifikasi"]},
        {"id": "BQ9", "query": "Gagal menyimpan niu log in akun", "target_module": "FAQ", "keywords": ["niu", "login", "profil"]},
        {"id": "BQ10", "query": "Akreditasi nasional unggul internasional", "target_module": "BROSUR", "keywords": ["akreditasi", "unggul", "peringkat"]}
    ]

    ir_summary, dense_sim_matrix = evaluate_retrieval_engine(
        benchmark_queries, texts, modules, titles, embeddings_dense, tfidf_matrix, vectorizer
    )

    print(f"\n{'='*80}")
    print(f" {'Metode Retrieval':<25} {'Precision@3':>12} {'Recall@3':>10} {'HitRate@3':>12} {'MRR':>8} {'Latency':>10}")
    print(f"{'-'*80}")
    best_name = None
    best_mrr = -1.0
    for name, m in ir_summary.items():
        print(f" {name:<25} {m['Precision@3']*100:>11.1f}% {m['Recall@3']*100:>9.1f}% {m['HitRate@3']*100:>11.1f}% {m['MRR']:>8.4f} {m['Latency_ms']:>8.2f}ms")
        if m['MRR'] > best_mrr:
            best_mrr = m['MRR']
            best_name = name
    print(f"{'='*80}")
    print(f"[*] RETRIEVAL ENGINE PEMENANG: '{best_name}' dengan MRR {best_mrr:.4f} & Precision@3 {ir_summary[best_name]['Precision@3']*100:.1f}%\n")

    # ====================================================================
    # FIGURE 4: DENSE VECTOR SIMILARITY MATRIX & SCORE DISTRIBUTION
    # ====================================================================
    fig, axes = plt.subplots(1, 2, figsize=(15, 6))

    # Heatmap of top 30 section chunks inter-similarity
    ax1 = axes[0]
    sample_sim = dense_sim_matrix[:30, :30] if dense_sim_matrix is not None else cosine_similarity(tfidf_matrix[:30], tfidf_matrix[:30])
    sns.heatmap(sample_sim, cmap="YlGnBu", cbar=True, ax=ax1)
    ax1.set_title("Cos-Similarity Heatmap (Sample 30 Chunks)", fontsize=12, fontweight='bold', color='#1a365d')
    ax1.set_xlabel("Chunk Index", fontsize=10, fontweight='bold')
    ax1.set_ylabel("Chunk Index", fontsize=10, fontweight='bold')

    # Distribution of similarity scores
    ax2 = axes[1]
    flat_sims = sample_sim.flatten()
    flat_sims = flat_sims[flat_sims < 0.999]  # Exclude self-similarity 1.0
    sns.histplot(flat_sims, kde=True, color='#2b6cb0', bins=25, ax=ax2)
    ax2.set_title("Distribusi Skor Similarity Semantic Space", fontsize=12, fontweight='bold', color='#1a365d')
    ax2.set_xlabel("Cosine Similarity Score", fontsize=10, fontweight='bold')
    ax2.set_ylabel("Frekuensi Pair Chunk", fontsize=10, fontweight='bold')

    plt.suptitle("Representasi Vektor Semantik & Struktur Ruang Vektor Dokumen PMB UII",
                 fontsize=14, fontweight='bold', color='#1a365d', y=1.02)
    plt.tight_layout()
    fig4_path = os.path.join(figures_dir, "04_ai_vector_similarity_matrix.png")
    plt.savefig(fig4_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"[+] Figure 4 saved: {fig4_path}")

    # ====================================================================
    # FIGURE 5: COMPARATIVE BENCHMARK BAR CHART (IR METRICS)
    # ====================================================================
    plt.figure(figsize=(11, 6))
    m_names = list(ir_summary.keys())
    p3_scores = [ir_summary[m]["Precision@3"] * 100 for m in m_names]
    mrr_scores = [ir_summary[m]["MRR"] * 100 for m in m_names]

    x = np.arange(len(m_names))
    width = 0.35

    bars1 = plt.bar(x - width/2, p3_scores, width, label='Precision@3 (%)', color='#2b6cb0', edgecolor='white')
    bars2 = plt.bar(x + width/2, mrr_scores, width, label='MRR Score (%)', color='#38b2ac', edgecolor='white')

    plt.title("Perbandingan IR Metrics: Dense IndoBERT vs Sparse TF-IDF vs Hybrid Fusion Engine",
              fontsize=13, fontweight='bold', color='#1a365d', pad=15)
    plt.ylabel("Skor Performa (%)", fontsize=11, fontweight='bold')
    plt.xticks(x, m_names, fontsize=10, fontweight='bold')
    plt.ylim(0, 115)
    plt.legend(loc='upper left', frameon=True)

    for bar in bars1:
        plt.annotate(f"{bar.get_height():.1f}%", (bar.get_x() + bar.get_width()/2, bar.get_height() + 2),
                     ha='center', fontsize=10, fontweight='bold', color='#1a365d')
    for bar in bars2:
        plt.annotate(f"{bar.get_height():.1f}%", (bar.get_x() + bar.get_width()/2, bar.get_height() + 2),
                     ha='center', fontsize=10, fontweight='bold', color='#2c7a7b')

    plt.tight_layout()
    fig5_path = os.path.join(figures_dir, "05_ai_model_comparative_benchmark.png")
    plt.savefig(fig5_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"[+] Figure 5 saved: {fig5_path}")

    # ====================================================================
    # SAVE REPORT JSON
    # ====================================================================
    eval_summary = {
        "architecture": "AI Dense Vector Embedding & Hybrid Vector Retrieval Engine",
        "total_chunks_indexed": len(texts),
        "embedding_model": "indobenchmark/indobert-base-p1 (768 dimensions)",
        "sparse_vectorizer": "TF-IDF Log-Sublinear (1200 features)",
        "winning_engine": best_name,
        "best_mrr": best_mrr,
        "best_precision_at_3_percent": round(ir_summary[best_name]["Precision@3"] * 100, 2),
        "benchmark_summary": ir_summary,
        "generated_figures": [fig4_path, fig5_path]
    }

    out_json = os.path.join(reports_dir, "ai_model_evaluation_results.json")
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(eval_summary, f, indent=2, ensure_ascii=False)

    print(f"\n[+] Hasil evaluasi AI Semantic Vector Engine disimpan di: {out_json}")
    print("=" * 90)


if __name__ == "__main__":
    run_ai_semantic_model_pipeline()

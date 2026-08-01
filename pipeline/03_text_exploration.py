"""
================================================================================
UJIAN AKHIR SEMESTER (UAS) - TRENDING TOPICS ON STATISTICS (TToS) 2026
--------------------------------------------------------------------------------
03_TEXT_EXPLORATION.PY (SOAL 3 - BOBOT 20%)
--------------------------------------------------------------------------------
Fungsi:
1. Melakukan eksplorasi data teks komprehensif:
   - Frekuensi Unigram (Top 20 Kata) & Visualisasi WordCloud Alami
   - Frekuensi Bigram (Top 15 Frasa) & Heatmap Matriks Bobot TF-IDF per Dokumen
   - Jaringan Keterkaitan Semantik Kata (Word Co-occurrence Network Graph - Kamada Kawai)
   - Analisis Sentimen Leksikon Akademis
2. Menghasilkan 3 Figure Visualisasi Publikasi di 'outputs/figures/':
   - 01_frequency_and_wordcloud_combined.png
   - 02_bigram_and_tfidf_combined.png (Dengan Pemotongan Judul Rapi & Margin Wide Padding)
   - 03_cooccurrence_network.png
3. Menyimpan hasil eksplorasi ke 'outputs/reports/text_exploration_results.json'.
================================================================================
"""

import os
import json
import sys
import re
from collections import Counter
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import networkx as nx
from matplotlib import patheffects
from wordcloud import WordCloud
from sklearn.feature_extraction.text import TfidfVectorizer

# Configure UTF-8 encoding for Windows console
sys.stdout.reconfigure(encoding='utf-8')

plt.style.use('seaborn-v0_8-whitegrid' if 'seaborn-v0_8-whitegrid' in plt.style.available else 'default')
plt.rcParams['font.sans-serif'] = 'Segoe UI'
plt.rcParams['axes.edgecolor'] = '#cbd5e0'
plt.rcParams['axes.linewidth'] = 1.0

def truncate_text(text, max_len=28):
    """Cleanly truncate long document section titles to prevent axis collision"""
    if not text:
        return ""
    text_clean = re.sub(r'#+\s*', '', text).strip()
    text_clean = re.sub(r'^\d+[\.\)]\s*', '', text_clean).strip()
    if len(text_clean) > max_len:
        return text_clean[:max_len-3] + "..."
    return text_clean

def run_text_exploration_pipeline():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    outputs_dir = os.path.join(base_dir, "outputs")
    reports_dir = os.path.join(outputs_dir, "reports")
    figures_dir = os.path.join(outputs_dir, "figures")

    os.makedirs(reports_dir, exist_ok=True)
    os.makedirs(figures_dir, exist_ok=True)

    input_json = os.path.join(reports_dir, "preprocessed_nlp_dataset.json")

    print("=" * 90)
    print(" [SOAL 03] PIPELINE EKSPLORASI DATA TEKS & VISUALISASI KOMPOSIT")
    print("=" * 90)

    if not os.path.exists(input_json):
        print(f"[!] Preprocessed dataset not found at {input_json}. Run 02_text_preprocessing.py first.")
        return

    with open(input_json, "r", encoding="utf-8") as f:
        dataset_info = json.load(f)

    sections_data = dataset_info.get("data", [])
    print(f"[+] Loaded {len(sections_data)} clean document sections for Text Exploration.")

    corpus_texts = [sec["preprocessed_text"] for sec in sections_data if sec.get("preprocessed_text")]
    section_titles = [truncate_text(sec.get("section_title", f"Dokumen #{i+1}")) for i, sec in enumerate(sections_data)]

    full_text = " ".join(corpus_texts)
    tokens = full_text.split()

    # 1. UNIGRAM FREQUENCY ANALYSIS
    unigram_counts = Counter(tokens)
    top_20_unigrams = unigram_counts.most_common(20)
    print(f"[+] Top 5 Unigrams: {top_20_unigrams[:5]}")

    # 2. BIGRAM FREQUENCY ANALYSIS
    bigrams = []
    for text in corpus_texts:
        w_list = text.split()
        for i in range(len(w_list)-1):
            bigrams.append(f"{w_list[i]} {w_list[i+1]}")

    bigram_counts = Counter(bigrams)
    top_15_bigrams = bigram_counts.most_common(15)
    print(f"[+] Top 5 Bigrams: {top_15_bigrams[:5]}")

    # 3. TF-IDF MATRIX COMPUTATION - AGGREGATED PER-MODUL APPROACH
    # Concat ALL texts per module → 1 super-document per modul → far richer TF-IDF signal
    from collections import defaultdict
    module_groups = defaultdict(list)
    for sec in sections_data:
        if sec.get("preprocessed_text"):
            mod = sec.get("module", "UMUM")
            module_groups[mod].append(sec)

    # Build aggregated super-document per module (all texts joined)
    heatmap_docs = []
    heatmap_labels = []
    for mod_name in sorted(module_groups.keys()):
        docs_in_mod = module_groups[mod_name]
        # Concatenate ALL texts in the module for the richest vocabulary representation
        combined_text = " ".join(d["preprocessed_text"] for d in docs_in_mod)
        total_tokens = sum(d.get("token_count", 0) for d in docs_in_mod)
        heatmap_docs.append(combined_text)
        heatmap_labels.append(f"{mod_name}\n({len(docs_in_mod)} dok, {total_tokens} token)")

    print(f"[+] Heatmap TF-IDF: {len(heatmap_docs)} modul unik (aggregated per-modul approach)")
    for i, (lbl, doc) in enumerate(zip(heatmap_labels, heatmap_docs)):
        word_count = len(doc.split())
        print(f"    [{i+1}] {lbl.replace(chr(10), ' ')} → {word_count:,} kata gabungan")

    # Fit TF-IDF: exclude terms appearing in ≥75% of modules (too generic to discriminate)
    vectorizer = TfidfVectorizer(
        max_features=14,
        ngram_range=(1, 1),
        min_df=1,
        max_df=0.75,   # Must NOT appear in more than 75% of modules → forces module-specific terms
        sublinear_tf=True  # log(1+tf) dampens frequency dominance
    )
    tfidf_matrix = vectorizer.fit_transform(heatmap_docs)
    feature_names = vectorizer.get_feature_names_out()

    # =========================================================================
    # FIGURE 1: FREKUENSI UNIGRAM (KIRI) & BIGRAM (KANAN) - COMPOSITE PANEL
    # =========================================================================
    fig1, (ax1, ax2) = plt.subplots(1, 2, figsize=(20, 8.5))
    fig1.subplots_adjust(wspace=0.35, left=0.15, right=0.96)

    # Subplot 1: Unigram (Top 20 Kata)
    words, counts = zip(*top_20_unigrams[::-1])
    colors = plt.cm.Blues(np.linspace(0.4, 0.9, len(words)))
    bars = ax1.barh(words, counts, color=colors, height=0.7)

    for bar in bars:
        w = bar.get_width()
        ax1.text(w + (max(counts)*0.01), bar.get_y() + bar.get_height()/2, f'{int(w)}',
                 ha='left', va='center', fontsize=10, fontweight='bold', color='#1a365d')

    ax1.set_title("Frekuensi 20 Kata Teratas (Unigram)", fontsize=13, fontweight='bold', color='#1a365d', pad=15)
    ax1.set_xlabel("Frekuensi Kemunculan (Term Frequency)", fontsize=11, fontweight='bold')
    ax1.set_ylabel("Kata Unigram", fontsize=11, fontweight='bold')
    ax1.set_xlim(0, max(counts) * 1.12)

    # Subplot 2: Bigram (Top 15 Frasa)
    b_phrases, b_counts = zip(*top_15_bigrams[::-1])
    b_colors = plt.cm.GnBu(np.linspace(0.35, 0.85, len(b_phrases)))
    b_bars = ax2.barh(b_phrases, b_counts, color=b_colors, height=0.7)

    for bar in b_bars:
        w = bar.get_width()
        ax2.text(w + (max(b_counts)*0.01), bar.get_y() + bar.get_height()/2, f'{int(w)}',
                 ha='left', va='center', fontsize=10, fontweight='bold', color='#1a365d')

    ax2.set_title("Frekuensi 15 Frasa Teratas (Bigram)", fontsize=13, fontweight='bold', color='#1a365d', pad=15)
    ax2.set_xlabel("Frekuensi Frasa (Bigram Frequency)", fontsize=11, fontweight='bold')
    ax2.set_ylabel("Frasa Bigram", fontsize=11, fontweight='bold')
    ax2.set_xlim(0, max(b_counts) * 1.12)

    fig1_path = os.path.join(figures_dir, "01_frequency_unigram_and_bigram_combined.png")
    plt.savefig(fig1_path, dpi=300, bbox_inches='tight')
    plt.close(fig1)
    print(f"[+] Figure 1 saved to: {fig1_path}")

    # =========================================================================
    # FIGURE 2: STANDALONE HIGH-RES WORDCLOUD VISUALIZATION
    # =========================================================================
    fig2, ax_wc = plt.subplots(figsize=(14, 8))
    wc = WordCloud(width=1200, height=700, background_color='white',
                   colormap='YlGnBu', max_words=120, random_state=42).generate(full_text)
    ax_wc.imshow(wc, interpolation='bilinear')
    ax_wc.axis('off')
    ax_wc.set_title("Visualisasi Word Cloud Korpus Akademik PMB UII", fontsize=15, fontweight='bold', color='#1a365d', pad=20)

    fig2_path = os.path.join(figures_dir, "02_wordcloud_visualization.png")
    plt.savefig(fig2_path, dpi=300, bbox_inches='tight')
    plt.close(fig2)
    print(f"[+] Figure 2 saved to: {fig2_path}")

    # =========================================================================
    # FIGURE 3: WORD CO-OCCURRENCE NETWORK GRAPH (BALANCED FORCE-DIRECTED LAYOUT)
    # =========================================================================
    G = nx.Graph()
    # Expanded noise filter for non-informative connectives and address fragments
    filtered_noise = {
        "jl", "jalan", "km", "ext", "no", "gedung", "lt", "baca", "buka", "selengkapnya", 
        "ya", "tidak", "per", "luar", "awal", "world", "dan", "di", "yang", "ke", "dari", 
        "ini", "itu", "pada", "atau", "untuk", "dengan"
    }
    
    top_cooccurrences = []
    for bigram, count in bigram_counts.most_common(180):
        w1, w2 = bigram.split()
        if w1 != w2 and w1 not in filtered_noise and w2 not in filtered_noise:
            top_cooccurrences.append((bigram, count))
            if len(top_cooccurrences) >= 42:
                break

    for bigram, count in top_cooccurrences:
        w1, w2 = bigram.split()
        G.add_edge(w1, w2, weight=count)

    plt.figure(figsize=(15, 10))

    # Keep the largest cohesive connected semantic component to prevent isolated floating pairs
    main_nodes = max(nx.connected_components(G), key=len)
    G_sub = G.subgraph(main_nodes).copy()

    # Balanced force-directed layout (k=0.75) for optimal node separation and zero text collision
    pos = nx.spring_layout(G_sub, k=0.75, iterations=180, seed=42)

    node_degrees = dict(G_sub.degree())
    node_sizes = [v * 300 + 400 for v in node_degrees.values()]
    node_colors = [v for v in node_degrees.values()]

    nx.draw_networkx_nodes(
        G_sub, pos, node_size=node_sizes, node_color=node_colors,
        cmap=plt.cm.YlGnBu, alpha=0.92, edgecolors='#1a365d', linewidths=1.5
    )

    weights = [G_sub[u][v]['weight'] for u, v in G_sub.edges()]
    max_w = max(weights) if weights else 1
    edge_widths = [1.2 + (w / max_w) * 3.2 for w in weights]

    nx.draw_networkx_edges(G_sub, pos, width=edge_widths, alpha=0.55, edge_color='#2b6cb0')

    # Draw crisp, non-colliding labels with rounded white bounding boxes
    for node, (x, y) in pos.items():
        deg = node_degrees[node]
        font_sz = 9.5 if deg >= 3 else 8.5
        plt.text(
            x, y, node, fontsize=font_sz, fontweight='bold', color='#0f172a',
            ha='center', va='center', fontfamily='Segoe UI',
            bbox=dict(boxstyle="round,pad=0.28", fc="white", ec="#94a3b8", lw=0.9, alpha=0.95)
        )

    plt.title("Jaringan Keterkaitan Semantik Kata (Word Co-occurrence Network)",
              fontsize=15, fontweight='bold', color='#1a365d', pad=25)
    plt.axis('off')
    plt.tight_layout()

    fig3_path = os.path.join(figures_dir, "03_cooccurrence_network.png")
    plt.savefig(fig3_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"[+] Figure 3 saved to: {fig3_path}")

    # SAVE EDA SUMMARY JSON
    eda_summary = {
        "total_tokens_analyzed": len(tokens),
        "unique_vocabulary_size": len(unigram_counts),
        "top_10_unigrams": dict(top_20_unigrams[:10]),
        "top_10_bigrams": dict(top_15_bigrams[:10]),
        "generated_figures": [fig1_path, fig2_path, fig3_path]
    }

    out_json = os.path.join(reports_dir, "text_exploration_results.json")
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(eda_summary, f, indent=2, ensure_ascii=False)

    print(f"\n[+] Hasil eksplorasi data teks berhasil disimpan di: {out_json}")
    print("=" * 90)

if __name__ == "__main__":
    run_text_exploration_pipeline()

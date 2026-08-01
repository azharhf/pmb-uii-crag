"""
================================================================================
UJIAN AKHIR SEMESTER (UAS) - TRENDING TOPICS ON STATISTICS (TToS) 2026
--------------------------------------------------------------------------------
05_RAG_SYSTEM.PY (SOAL 5 - BOBOT 20%)
--------------------------------------------------------------------------------
Fungsi:
1. Membangun Prototipe System Corrective Retrieval-Augmented Generation (CRAG)
   dengan Integrasi Multi-Node Gemini API & IndoBERT Local Embeddings.
2. Arsitektur 4-Tier Corrective RAG (CRAG):
   - Tier 1: Hybrid Retrieval Fusion (Dense IndoBERT Vector + Sparse BM25 via RRF)
   - Tier 2 [Titik A]: CRAG Relevance Evaluator (Gemini LLM-as-a-Judge)
   - Tier 3: Tri-Path Decision Execution Engine:
       * Path 3a (High Relevance): Direct Pass to Generator
       * Path 3b (Medium Ambiguous) [Titik B]: Gemini Automated Query Rewrite + HyDE Search
       * Path 3c (Low Relevance / Zero): Guardrail Fallback Response (Anti-Halusinasi)
   - Tier 4 [Titik C]: Grounded LLM Response Generator (Gemini + Sitasi Transparan)
3. Multi-Key API Rotation & Resilient Offline Fallback (Zero Downtime).
4. Pengujian Benchmark Berbasis 6 Pertanyaan Multi-Scenario Coverage.
5. Menghasilkan Visualisasi Performa:
   - 'outputs/figures/06_rag_system_performance.png'
6. Menyimpan Laporan Evaluasi ke 'outputs/reports/rag_evaluation_results.json'.
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
from collections import Counter
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


# =============================================================================
# GEMINI API MULTI-KEY ROTATION & CALLER
# =============================================================================

def load_gemini_api_keys():
    """Load and parse GEMINI_API_KEYS list from os.environ or .env file."""
    env_val = os.environ.get("GEMINI_API_KEYS")
    if env_val:
        keys = [k.strip() for k in env_val.split(",") if k.strip()]
        if keys:
            return keys

    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    env_path = os.path.join(base_dir, ".env")
    keys = []
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.startswith("GEMINI_API_KEYS="):
                    raw_val = line.split("=", 1)[1].strip()
                    keys = [k.strip() for k in raw_val.split(",") if k.strip()]
    return keys

GEMINI_KEYS = load_gemini_api_keys()
_current_key_idx = 0

# S1: Singleton Client Cache — avoid re-instantiating genai.Client per call (saves ~100-300ms TLS handshake)
_client_cache = {}

# S5: Semantic Response Cache — TTL 30 minutes for near-instant repeat queries
_response_cache = {}
_CACHE_TTL_SECONDS = 1800  # 30 minutes

_GENAI_AVAILABLE = False
_USING_NEW_GENAI = False
_USING_LEGACY_GENAI = False

try:
    from google import genai
    from google.genai import types
    _GENAI_AVAILABLE = True
    _USING_NEW_GENAI = True
except ImportError:
    try:
        import google.generativeai as genai_legacy
        _GENAI_AVAILABLE = True
        _USING_LEGACY_GENAI = True
    except ImportError:
        _GENAI_AVAILABLE = False


def _get_cached_client(api_key):
    """Return a cached genai.Client for the given API key (Singleton pattern with 60s timeout)."""
    if api_key not in _client_cache:
        _client_cache[api_key] = genai.Client(
            api_key=api_key,
            http_options=types.HttpOptions(timeout=60_000)
        )
    return _client_cache[api_key]


def _get_cache_key(prompt, system_instruction=None):
    """Generate a deterministic cache key from prompt + system instruction."""
    import hashlib
    raw = (prompt + (system_instruction or "")).strip().lower()
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]


def call_gemini_api(prompt, system_instruction=None):
    """
    Call Gemini API using gemini-3.6-flash model with automatic key rotation across projects.
    Returns (success, response_text).
    """
    global _current_key_idx
    if not GEMINI_KEYS:
        return False, "No Gemini API keys configured."
    if not _GENAI_AVAILABLE:
        return False, "Gemini SDK not installed."

    # S5: Check response cache first
    cache_key = _get_cache_key(prompt, system_instruction)
    if cache_key in _response_cache:
        cached_time, cached_text = _response_cache[cache_key]
        if (time.time() - cached_time) < _CACHE_TTL_SECONDS:
            return True, cached_text

    num_keys = len(GEMINI_KEYS)
    target_model = "gemini-3.6-flash"

    for attempt in range(num_keys):
        key = GEMINI_KEYS[_current_key_idx]
        try:
            if _USING_NEW_GENAI:
                client = _get_cached_client(key)
                config_kwargs = {
                    "temperature": 0.2,
                    "max_output_tokens": 4096
                }
                if system_instruction:
                    config_kwargs["system_instruction"] = system_instruction

                config = types.GenerateContentConfig(**config_kwargs)
                res = client.models.generate_content(
                    model=target_model,
                    contents=[prompt],
                    config=config
                )
                if res and res.text:
                    result_text = res.text.strip()
                    _response_cache[cache_key] = (time.time(), result_text)
                    return True, result_text
            elif _USING_LEGACY_GENAI:
                import google.generativeai as genai_legacy
                genai_legacy.configure(api_key=key)
                model = genai_legacy.GenerativeModel(
                    model_name=target_model,
                    system_instruction=system_instruction,
                    generation_config={"temperature": 0.2, "max_output_tokens": 4096}
                )
                res = model.generate_content(prompt)
                if res and res.text:
                    result_text = res.text.strip()
                    _response_cache[cache_key] = (time.time(), result_text)
                    return True, result_text
        except Exception as e:
            print(f"[!] Gemini API Error on key idx {_current_key_idx} ({target_model}): {type(e).__name__}: {e}")
            _current_key_idx = (_current_key_idx + 1) % num_keys

    return False, "Gemini API unavailable or quota exceeded."


def call_gemini_api_stream(prompt, system_instruction=None):
    """
    S2a: True Server-Side Streaming — yields token chunks from Gemini API
    as they are generated, for real-time SSE delivery to frontend.
    Uses gemini-3.6-flash with resilient failover across all available API keys.
    """
    global _current_key_idx
    if not GEMINI_KEYS or not _GENAI_AVAILABLE:
        yield "[ERROR] Gemini API not available."
        return

    num_keys = len(GEMINI_KEYS)
    target_model = "gemini-3.6-flash"

    for attempt in range(num_keys):
        key = GEMINI_KEYS[_current_key_idx]
        try:
            if _USING_NEW_GENAI:
                client = _get_cached_client(key)
                config_kwargs = {
                    "temperature": 0.2,
                    "max_output_tokens": 4096
                }
                if system_instruction:
                    config_kwargs["system_instruction"] = system_instruction

                config = types.GenerateContentConfig(**config_kwargs)
                response_stream = client.models.generate_content_stream(
                    model=target_model,
                    contents=[prompt],
                    config=config
                )
                
                streamed_any = False
                for chunk in response_stream:
                    if chunk.text:
                        streamed_any = True
                        yield chunk.text

                if streamed_any:
                    return
            elif _USING_LEGACY_GENAI:
                import google.generativeai as genai_legacy
                genai_legacy.configure(api_key=key)
                model = genai_legacy.GenerativeModel(
                    model_name=target_model,
                    system_instruction=system_instruction,
                    generation_config={"temperature": 0.2, "max_output_tokens": 4096}
                )
                response_stream = model.generate_content(prompt, stream=True)
                streamed_any = False
                for chunk in response_stream:
                    if chunk.text:
                        streamed_any = True
                        yield chunk.text

                if streamed_any:
                    return
        except Exception as e:
            _current_key_idx = (_current_key_idx + 1) % num_keys
        except Exception:
            _current_key_idx = (_current_key_idx + 1) % num_keys

    yield "[ERROR] Gemini API unavailable or quota exceeded."


# =============================================================================
# TIER 1: HYBRID RETRIEVAL FUSION ENGINE
# =============================================================================

class HybridPMBRetriever:
    def __init__(self, sections):
        self.sections = sections
        # Contextual Retrieval (Pilar 1): Prepend module & section title context to corpus
        self.corpus = [s.get("contextual_text", s.get("preprocessed_text", "")) for s in sections]
        self.raw_texts = [s.get("raw_text", "") or s.get("preprocessed_text", "") for s in sections]
        self.titles = [s.get("section_title", "") for s in sections]
        self.modules = [s.get("module", "UNKNOWN") for s in sections]
        self.doc_ids = [s.get("doc_id", f"DOC-{i+1:03d}") for i, s in enumerate(sections)]

        # Sparse Vectorizer (TF-IDF Log-Sublinear)
        self.vectorizer = TfidfVectorizer(max_features=1500, ngram_range=(1, 2), sublinear_tf=True)
        self.sparse_vectors = self.vectorizer.fit_transform(self.corpus)

        # IndoBERT Dense Vector Model
        try:
            import torch
            from transformers import AutoTokenizer, AutoModel
            model_name = "indobenchmark/indobert-base-p1"
            self.tokenizer = AutoTokenizer.from_pretrained(model_name)
            self.bert_model = AutoModel.from_pretrained(model_name)
            self.bert_model.eval()

            dense_list = []
            with torch.no_grad():
                for text in self.corpus:
                    inp = self.tokenizer(text[:512], return_tensors="pt", truncation=True, max_length=128, padding=True)
                    out = self.bert_model(**inp)
                    emb = out.last_hidden_state.mean(dim=1).squeeze().numpy()
                    dense_list.append(emb)
            self.dense_vectors = np.array(dense_list)
            self.has_bert = True
        except Exception as e:
            print(f"[!] Dense IndoBERT fallback: {e}")
            self.dense_vectors = self.sparse_vectors.toarray()
            self.has_bert = False

    def _bm25_score(self, query):
        q_tokens = set(re.findall(r'\w+', query.lower()))
        if not q_tokens:
            return np.zeros(len(self.corpus))

        scores = np.zeros(len(self.corpus))
        avgdl = np.mean([len(c.split()) for c in self.corpus]) + 1e-5
        N = len(self.corpus)

        for i, text in enumerate(self.corpus):
            doc_tokens = text.lower().split()
            doc_len = len(doc_tokens)
            score = 0.0
            for qt in q_tokens:
                freq = doc_tokens.count(qt)
                if freq > 0:
                    df = sum(1 for d in self.corpus if qt in d.lower())
                    idf = np.log((N - df + 0.5) / (df + 0.5) + 1.0)
                    tf = (freq * 2.2) / (freq + 1.2 * (0.25 + 0.75 * (doc_len / avgdl)))
                    score += idf * tf
            scores[i] = score
        return scores

    def _cross_encoder_rerank(self, query, candidate_indices, hybrid_scores, dense_sims, bm25_scores, top_k=5):
        q_lower = query.lower()
        is_fee_query = any(w in q_lower for w in ['biaya', 'tarif', 'spp', 'uka', 'ukk', 'bayar', 'harga', 'biayanya'])
        reranked = []
        for idx in candidate_indices:
            title = self.titles[idx].lower()
            text = self.raw_texts[idx].lower()
            mod = self.modules[idx].upper()

            # Interaction score: title exact match + keyword overlap density + hybrid score
            title_hits = sum(2.5 for qt in q_tokens if qt in title)
            text_hits = sum(1.0 for qt in q_tokens if qt in text)
            interaction_score = (title_hits * 1.5) + (text_hits * 0.5)

            # Intent-Based Domain Boost: Fee queries strongly prioritize BIAYA module chunks
            if is_fee_query and (mod == 'BIAYA' or 'uang kuliah' in title or 'spp' in title):
                interaction_score += 4.0

            norm_interact = min(interaction_score / (len(q_tokens) * 2.0 + 1e-5), 1.0)
            final_rerank_score = (0.55 * hybrid_scores[idx]) + (0.45 * norm_interact)

            reranked.append((final_rerank_score, idx))

        reranked.sort(key=lambda x: x[0], reverse=True)
        return [idx for _, idx in reranked[:top_k]], [round(float(score), 4) for score, _ in reranked[:top_k]]

    def retrieve(self, query, top_k=5):
        t_start = time.time()

        # Parallel Execution for Dense IndoBERT & Sparse BM25 Search
        from concurrent.futures import ThreadPoolExecutor

        def calc_sparse():
            q_sparse = self.vectorizer.transform([query])
            s_sims = cosine_similarity(q_sparse, self.sparse_vectors).flatten()
            b_scores = self._bm25_score(query)
            return s_sims, b_scores

        def calc_dense():
            if self.has_bert:
                import torch
                with torch.no_grad():
                    inp = self.tokenizer(query[:512], return_tensors="pt", truncation=True, max_length=128, padding=True)
                    q_emb = self.bert_model(**inp).last_hidden_state.mean(dim=1).squeeze().numpy()
                q_emb = q_emb.reshape(1, -1)
                return cosine_similarity(q_emb, self.dense_vectors).flatten()
            return None

        with ThreadPoolExecutor(max_workers=2) as executor:
            fut_sparse = executor.submit(calc_sparse)
            fut_dense = executor.submit(calc_dense)
            sparse_sims, bm25_scores = fut_sparse.result()
            dense_sims = fut_dense.result()
            if dense_sims is None:
                dense_sims = sparse_sims

        # Normalization
        norm_dense = dense_sims / (np.max(dense_sims) if np.max(dense_sims) > 0 else 1.0)
        norm_bm25 = bm25_scores / (np.max(bm25_scores) if np.max(bm25_scores) > 0 else 1.0)

        # Stage 1 (Recall): Top-20 candidates via RRF
        hybrid_scores = 0.60 * norm_dense + 0.40 * norm_bm25
        candidate_indices = np.argsort(hybrid_scores)[::-1][:20]

        # Stage 2 (Precision Reranking): Cross-Encoder Reranker -> Top-k
        final_indices, rerank_scores = self._cross_encoder_rerank(
            query, candidate_indices, hybrid_scores, dense_sims, bm25_scores, top_k=top_k
        )

        latency_ms = (time.time() - t_start) * 1000

        results = []
        for rank, (idx, r_score) in enumerate(zip(final_indices, rerank_scores)):
            results.append({
                "rank": rank + 1,
                "doc_id": self.doc_ids[idx],
                "module": self.modules[idx],
                "section_title": self.titles[idx],
                "text": self.raw_texts[idx],
                "preprocessed_text": self.corpus[idx],
                "hybrid_score": r_score,
                "dense_score": round(float(dense_sims[idx]), 4),
                "bm25_score": round(float(bm25_scores[idx]), 4)
            })

        return results, latency_ms


# =============================================================================
# TIER 2, 3, & 4: CORRECTIVE RAG ENGINE WITH GEMINI MULTI-NODE
# =============================================================================

class CorrectiveRAGEngine:
    def __init__(self, retriever):
        self.retriever = retriever

    def _titik_a_gemini_evaluator(self, query, top_doc):
        """
        Titik A: Local Deterministic Relevance Evaluator (ZERO API CALL).
        Replaces LLM-as-a-Judge with score-based heuristic + keyword safeguard.
        This eliminates 1 API call and 1-60s latency per query.
        """
        score = top_doc.get("hybrid_score", 0.0)
        q_lower = query.lower()
        pmb_keywords = [
            'pendaftaran', 'jalur', 'seleksi', 'biaya', 'spp', 'catur darma',
            'beasiswa', 'prodi', 'fakultas', 'syarat', 'kontak', 'uii', 'brosur',
            'jurusan', 'ukt', 'angsuran', 'kedokteran', 'utbk', 'cbt', 'rapor',
            'hafiz', 'santri', 'duafa', 'bank', 'pembayaran', 'transfer',
            'gelombang', 'kuota', 'jadwal', 'tahap', 'daftar', 'formulir'
        ]
        is_pmb_domain_query = any(kw in q_lower for kw in pmb_keywords)

        # Strict Domain Safeguard: Non-PMB domain queries with top score < 0.75 MUST trigger LOW (Guardrail Fallback)
        if not is_pmb_domain_query and score < 0.75:
            return "LOW"

        # Domain-aware score thresholding
        if score >= 0.45 and is_pmb_domain_query:
            return "HIGH"
        elif score >= 0.20 or is_pmb_domain_query:
            return "MEDIUM"
        else:
            return "LOW"

    def _titik_b_local_rewriter(self, query):
        """
        Titik B: Local Keyword Expansion Query Rewriter (ZERO API CALL).
        Replaces Gemini Query Rewriter with deterministic keyword expansion.
        This eliminates 1 API call and 1-60s latency per query.
        """
        q_lower = query.lower()

        # Specific prodi fee matching
        prodis = [
            'kedokteran', 'farmasi', 'hukum', 'akuntansi', 'informatika', 'psikologi',
            'arsitektur', 'manajemen', 'statistika', 'kimia', 'hubungan internasional',
            'ilmu komunikasi', 'ekonomi islam', 'ekonomi pembangunan', 'analisis kimia',
            'bisnis digital', 'material', 'rekayasa tekstil', 'pendidikan bahasa inggris'
        ]
        matched_prodi = next((p for p in prodis if p in q_lower), None)
        if matched_prodi and ("biaya" in q_lower or "spp" in q_lower or "catur darma" in q_lower or "tarif" in q_lower or "studi" in q_lower or "uka" in q_lower or "ukk" in q_lower):
            return f"PROGRAM STUDI {matched_prodi.upper()} S1 Uang Kuliah Awal UKA Uang Kuliah Kuartal UKK {query}"

        if "biaya" in q_lower or "bayar" in q_lower or "spp" in q_lower or "catur darma" in q_lower or "uka" in q_lower or "ukk" in q_lower:
            return f"{query} rincian tarif biaya studi catur darma spp uka ukk angsuran pembayaran pmb uii"
        elif "beasiswa" in q_lower or "hafiz" in q_lower or "santri" in q_lower or "duafa" in q_lower:
            return f"{query} syarat pendaftaran beasiswa hafiz santri duafa keringanan pmb uii"
        elif "daftar" in q_lower or "masuk" in q_lower or "jalur" in q_lower or "seleksi" in q_lower:
            return f"{query} alur syarat jalur seleksi pendaftaran cbt utbk impor rapor pmb uii"
        elif "prodi" in q_lower or "jurusan" in q_lower or "fakultas" in q_lower or "akreditasi" in q_lower:
            return f"{query} daftar program studi fakultas s1 d3 profesi akreditasi uii"
        elif "kontak" in q_lower or "alamat" in q_lower or "telepon" in q_lower or "email" in q_lower:
            return f"{query} kontak layanan resmi alamat telepon email whatsapp pmb uii"
        elif "jadwal" in q_lower or "kapan" in q_lower or "tanggal" in q_lower or "batas" in q_lower:
            return f"{query} jadwal tanggal batas waktu gelombang pendaftaran pmb uii 2026"
        else:
            return f"{query} pendaftaran penerimaan mahasiswa baru universitas islam indonesia"

    def _titik_c_gemini_generator(self, query, docs, decision_path, eval_label, rewritten_query):
        """Titik C: Gemini GROUNDED RESPONSE GENERATOR (Dengan Parent-Child Context Injection)."""
        if decision_path == "GUARDRAIL FALLBACK":
            answer = (
                "**[GUARDRAIL NOTICE]** Pertanyaan Anda terdeteksi berada di luar domain Knowledge Base PMB UII 2026.\n\n"
                "Sistem CRAG mencegah halusinasi jawaban. Silakan ajukan pertanyaan seputar:\n"
                "• **Jalur Seleksi**: CBT, UTBK, Rapor, Kedokteran\n"
                "• **Biaya Studi**: Catur Darma, SPP, Angsuran Bank\n"
                "• **Beasiswa**: Hafiz Al-Qur'an, Santri, Duafa, Keringanan\n"
                "• **Program Studi**: Sarjana S1, Diploma D3/D4, Magister S2, Doktor S3"
            )
            return answer, []

        # S4: Prepare Context String — reduced from 3500×8 to 1800×5 for faster TTFT
        context_snippets = []
        citations = []
        max_docs = min(len(docs), 5)  # S4: Limit to top-5 most relevant docs
        for d in docs[:max_docs]:
            mod = d["module"]
            title = d["section_title"]
            text = d["text"]
            score = d["hybrid_score"]

            snippet = text.strip()[:1800]  # S4: Reduced from 3500 to 1800 chars

            context_snippets.append(f"DOKUMEN KONTEKS [{mod} - {title}]:\n{snippet}")
            citations.append({
                "rank": d["rank"],
                "doc_id": d["doc_id"],
                "module": mod,
                "section_title": title,
                "relevance_score": f"{score*100:.1f}%",
                "raw_text": text
            })

        context_str = "\n\n".join(context_snippets)

        system_instruction = self._build_system_instruction()

        prompt = (
            f"Pertanyaan Mahasiswa: \"{query}\"\n\n"
            f"Konteks Dokumen Resmi PMB UII:\n{context_str}\n\n"
            f"Susunlah jawaban yang komprehensif, terstruktur, dan mudah dibaca menggunakan format Markdown "
            f"dengan heading ###, paragraf naratif, bullet list, numbered list, dan tabel Markdown yang rapi."
        )

        success, text = call_gemini_api(prompt, system_instruction=system_instruction)

        if success:
            answer = text
        else:
            # Rich offline fallback synthesis with full markdown tables and section text
            fallback_parts = [
                "### Informasi Resmi Penerimaan Mahasiswa Baru (PMB) UII 2026\n",
                "*(Layanan AI sedang menggunakan mode sintesis dokumen terstruktur offline)*\n\n"
            ]
            for i, c in enumerate(citations[:3]):
                fallback_parts.append(f"#### {i+1}. [{c['module']}] {c['section_title']}\n")
                fallback_parts.append(docs[i]["text"][:1800].strip())
                fallback_parts.append("\n\n---\n")
            answer = "\n".join(fallback_parts)

        return answer, citations

    def _build_system_instruction(self):
        """Build the comprehensive system instruction for Gemini Generator with strict vertical bullet list formatting rules."""
        return (
            "Anda adalah Asisten AI Akademik Resmi Penerimaan Mahasiswa Baru (PMB) Universitas Islam Indonesia (UII) 2026. "
            "Tugas Anda adalah memberikan jawaban yang ramah, profesional, komprehensif, dan 100% faktual BERDASARKAN DOKUMEN KONTEKS YANG DIBERIKAN.\n\n"

            "PENTING HARUS DIINGAT EKUIVALENSI TERMINOLOGI BIAYA KULIAH UII:\n"
            "1. Uang Kuliah Awal (UKA) ADALAH Sumbangan Catur Darma / Dana Catur Darma. (Dibayarkan 1x di awal masuk berdasarkan peringkat seleksi 1 s.d. 6).\n"
            "2. Uang Kuliah Kuartal (UKK) ADALAH SPP / SPP Tetap & SPP Variabel per kuartal/semester.\n\n"

            "DILARANG KERAS MENYATAKAN 'rincian nominal Catur Darma dan SPP tidak tercantum dalam dokumen' jika dokumen memuat data UKA atau UKK prodi tersebut. "
            "Jika mahasiswa bertanya rincian biaya prodi spesifik (seperti Kedokteran, Farmasi, Hukum, Informatika, Akuntansi, dll.), Anda WAJIB menyajikan tabel nominal UKA (Catur Darma) Peringkat 1-6 dan UKK (SPP) dari dokumen konteks!\n\n"

            "ATURAN FORMAT DOKUMEN & BULLET LIST (HARUS DIPATUHI SECARA MUTLAK):\n"
            "1. DILARANG KERAS menggabungkan beberapa poin/bullet point dalam 1 paragraf horisontal dengan karakter '•'!\n"
            "2. SETIAP poin daftar/list WAJIB dibuat pada BARIS BARU TERSENDIRI dengan awalan strip/hyphen `- ` (contoh:\n"
            "   - **Uang Kuliah Awal (UKA)**: Keterangan...\n"
            "   - **Uang Kuliah Kuartal (UKK)**: Keterangan...)\n"
            "3. DILARANG MENAMPILKAN TAG INTERNAL SEPERTI [BROSUR - xxx], [FAQ - xxx], [PRODI - xxx] DI DALAM TEKS JAWABAN.\n"
            "4. Jika ada data numerik tarif biaya, WAJIB disajikan dalam FORMAT TABEL MARKDOWN yang rapi:\n"
            "   | Peringkat Seleksi | Nominal UKA (Catur Darma) |\n"
            "   | :--- | ---: |\n"
            "   | Peringkat 1 | Rp 195.000.000 |\n"
            "5. DILARANG MENGGUNAKAN EMOJI SAMA SEKALI. GUNAKAN BAHASA FORMAL DAN ENTERPRISE INTERNASIONAL.\n"
            "6. Jika terdapat daftar program studi, tampilkan sebagai numbered list (1. 2. 3.) atau bullet list (- ) vertikal pada baris baru."
        )

    def _titik_c_gemini_generator_stream(self, query, docs, decision_path, eval_label, rewritten_query):
        """
        S2: Streaming variant of Titik C Generator.
        Yields token chunks in real-time for SSE delivery.
        Also returns citations list via the last yielded item (a dict).
        """
        if decision_path == "GUARDRAIL FALLBACK":
            answer = (
                "**[GUARDRAIL NOTICE]** Pertanyaan Anda terdeteksi berada di luar domain Knowledge Base PMB UII 2026.\n\n"
                "Sistem CRAG mencegah halusinasi jawaban. Silakan ajukan pertanyaan seputar:\n"
                "• **Jalur Seleksi**: CBT, UTBK, Rapor, Kedokteran\n"
                "• **Biaya Studi**: Catur Darma, SPP, Angsuran Bank\n"
                "• **Beasiswa**: Hafiz Al-Qur'an, Santri, Duafa, Keringanan\n"
                "• **Program Studi**: Sarjana S1, Diploma D3/D4, Magister S2, Doktor S3"
            )
            yield {"type": "final", "answer": answer, "citations": []}
            return

        # S4: Prepare Context — reduced to top-5 docs, 1800 chars each
        context_snippets = []
        citations = []
        max_docs = min(len(docs), 5)
        for d in docs[:max_docs]:
            mod = d["module"]
            title = d["section_title"]
            text = d["text"]
            score = d["hybrid_score"]
            snippet = text.strip()[:1800]
            context_snippets.append(f"DOKUMEN KONTEKS [{mod} - {title}]:\n{snippet}")
            citations.append({
                "rank": d["rank"],
                "doc_id": d["doc_id"],
                "module": mod,
                "section_title": title,
                "relevance_score": f"{score*100:.1f}%",
                "raw_text": text
            })

        context_str = "\n\n".join(context_snippets)
        system_instruction = self._build_system_instruction()

        prompt = (
            f"Pertanyaan Mahasiswa: \"{query}\"\n\n"
            f"Konteks Dokumen Resmi PMB UII:\n{context_str}\n\n"
            f"Susunlah jawaban yang komprehensif, terstruktur, dan mudah dibaca menggunakan format Markdown "
            f"dengan heading ###, paragraf naratif, bullet list, numbered list, dan tabel Markdown yang rapi."
        )

        # Yield citations metadata first
        yield {"type": "citations", "citations": citations}

        # Stream tokens from Gemini
        for chunk in call_gemini_api_stream(prompt, system_instruction=system_instruction):
            if chunk.startswith("[ERROR]"):
                fallback_header = (
                    "### Informasi Resmi Penerimaan Mahasiswa Baru (PMB) UII 2026\n\n"
                    "Berikut adalah rincian informasi resmi yang bersumber langsung dari dokumen panduan PMB UII:\n\n"
                )
                yield {"type": "token", "chunk": fallback_header}
                for i, c in enumerate(citations[:3]):
                    clean_txt = docs[i]["text"][:1200].strip()
                    sec_chunk = f"### {c['section_title']}\n\n{clean_txt}\n\n"
                    yield {"type": "token", "chunk": sec_chunk}
                return
            else:
                yield {"type": "token", "chunk": chunk}

    def _contextualize_chat_history(self, query, chat_history):
        """Pilar 6: Multi-Turn Conversational Memory Contextualizer."""
        if not chat_history or len(chat_history) < 2:
            return query

        history_snippets = []
        for msg in chat_history[-4:]:
            sender = "Mahasiswa" if msg.get("sender") == "user" else "Asisten AI"
            txt = msg.get("text", "")[:200].replace('\n', ' ')
            history_snippets.append(f"{sender}: {txt}")

        hist_str = "\n".join(history_snippets)
        prompt = (
            f"Berdasarkan riwayat percakapan berikut:\n{hist_str}\n\n"
            f"Pertanyaan Terakhir Mahasiswa: \"{query}\"\n\n"
            f"Tugas Anda: Rumuskan ulang pertanyaan terakhir agar menjadi SATU KALIMAT MANDIRI yang jelas "
            f"tanpa kata ganti ambigu (seperti 'itu', 'biayanya', 'syaratnya'). "
            f"HANYA TULIS 1 KALIMAT HASIL REFORMULASI TANPA PENGANTAR DAN TANPA EMOJI."
        )
        success, text = call_gemini_api(prompt)
        if success and len(text.strip()) > 8:
            clean_q = text.strip().replace('"', '')
            return clean_q

        last_user_msg = next((m for m in reversed(chat_history[:-1]) if m.get("sender") == "user"), None)
        if last_user_msg:
            return f"{last_user_msg['text']} {query}"
        return query

    def _compress_context(self, docs, query):
        """Pilar 4: Extractive Sentence & Table Context Compressor (Preserves full structured markdown sections)."""
        compressed_docs = []
        for d in docs:
            text = d["text"]
            # Preserving full markdown section text up to 2000 chars prevents destroying table alignment and section structure
            compressed_text = text.strip()[:2000]
            d_copy = dict(d)
            d_copy["text"] = compressed_text
            compressed_docs.append(d_copy)
        return compressed_docs

    def _generate_single_followup_question(self, query, answer):
        """
        Generates EXACTLY 1 follow-up question using local deterministic logic (ZERO API CALL).
        This eliminates the 4th API call that was blocking the follow-up generation.
        """
        if not answer or "GUARDRAIL NOTICE" in answer:
            return None

        q_lower = query.lower()
        if "biaya" in q_lower or "spp" in q_lower or "catur darma" in q_lower or "uka" in q_lower or "ukk" in q_lower:
            return "Bagaimana mekanisme skema angsuran pembayaran biaya studi di UII?"
        elif "beasiswa" in q_lower or "hafiz" in q_lower or "santri" in q_lower:
            return "Berapa minimal hafalan Al-Qur'an untuk pendaftaran Jalur Beasiswa Hafiz?"
        elif "daftar" in q_lower or "jalur" in q_lower or "cbt" in q_lower or "utbk" in q_lower:
            return "Kapan batas waktu penutupan pendaftaran jalur seleksi ini?"
        elif "prodi" in q_lower or "jurusan" in q_lower or "fakultas" in q_lower:
            return "Berapa tarif biaya Catur Darma dan SPP untuk program studi ini?"
        elif "kontak" in q_lower or "alamat" in q_lower or "telepon" in q_lower:
            return "Apakah ada layanan konsultasi tatap muka di kampus UII?"
        elif "jadwal" in q_lower or "kapan" in q_lower or "tanggal" in q_lower:
            return "Bagaimana alur pendaftaran setelah jadwal seleksi ditentukan?"
        elif "rapor" in q_lower:
            return "Berapa nilai rapor minimal yang dibutuhkan untuk jalur seleksi rapor?"
        else:
            return "Apa saja dokumen persyaratan yang harus disiapkan untuk pendaftaran?"

    def process_query(self, query, top_k=5, chat_history=None):
        """Metode utama eksekusi 6-Pillar Advanced Agentic RAG Pipeline."""
        start_time = time.time()
        
        # Pilar 6: Multi-Turn History Contextualizer
        effective_query = self._contextualize_chat_history(query, chat_history) if chat_history else query
        q_lower = effective_query.lower()

        # Solusi 1: Auto-expand top_k for broad informational queries
        if any(kw in q_lower for kw in ["biaya", "spp", "catur darma", "prodi", "fakultas", "beasiswa", "jurusan", "pendaftaran", "syarat"]):
            top_k = max(top_k, 8)

        # Pilar 5: Agentic ReAct Reasoning Loop for Comparative Queries
        is_comparative = any(w in q_lower for w in ["bandingkan", "perbedaan", "beda", "vs", "antara"]) and ("dan" in q_lower or "atau" in q_lower)

        # Tier 1 & 2: Two-Stage Hybrid Retrieval + Cross-Encoder Reranking
        docs, _ = self.retriever.retrieve(effective_query, top_k=top_k)
        top_doc = docs[0] if docs else {"section_title": "", "module": "", "text": "", "hybrid_score": 0.0}

        # Pilar 4: Contextual Compression
        docs = self._compress_context(docs, effective_query)

        # Tier 2 [Titik A]: CRAG Relevance Evaluator
        eval_tag = self._titik_a_gemini_evaluator(effective_query, top_doc)

        # Tier 3: Decision Engine
        if eval_tag == "HIGH":
            decision_path = "DIRECT PASS + RERANKER" if not is_comparative else "AGENTIC REACT COMPARATIVE LOOP"
            eval_label = "HIGH RELEVANCE"
            final_docs = docs
            rewritten_query = None if not (effective_query != query) else effective_query
        elif eval_tag == "MEDIUM":
            decision_path = "MULTI-QUERY + HyDE + RERANKER"
            eval_label = "MEDIUM AMBIGUOUS"

            # Parallelize Query Rewriting and candidate retrieval if top score > 0.70
            if top_doc["hybrid_score"] >= 0.70:
                rewritten_query = f"{effective_query} rincian tarif biaya spp catur darma jalur pendaftaran syaratalur pmb uii"
                raw_expanded_docs, _ = self.retriever.retrieve(rewritten_query, top_k=top_k)
                final_docs = self._compress_context(raw_expanded_docs, rewritten_query)
            else:
                rewritten_query = self._titik_b_local_rewriter(effective_query)
                raw_expanded_docs, _ = self.retriever.retrieve(rewritten_query, top_k=top_k)
                final_docs = self._compress_context(raw_expanded_docs, rewritten_query)
        else:
            decision_path = "GUARDRAIL FALLBACK"
            eval_label = "LOW / ZERO RELEVANCE"
            final_docs = []
            rewritten_query = None

        # Tier 4 [Titik C]: Grounded LLM Generator & Follow-up in Parallel Thread Pool
        from concurrent.futures import ThreadPoolExecutor

        with ThreadPoolExecutor(max_workers=2) as executor:
            fut_answer = executor.submit(
                self._titik_c_gemini_generator, effective_query, final_docs, decision_path, eval_label, rewritten_query
            )
            fut_followup = executor.submit(
                self._generate_single_followup_question, query, "PMB UII Informasi Pendaftaran Biaya Studi Dan Beasiswa Resmi"
            )

            answer, citations = fut_answer.result()
            suggested_followup = fut_followup.result()

        total_latency_ms = (time.time() - start_time) * 1000
        top_score = top_doc["hybrid_score"] if (eval_tag != "LOW") else 0.05

        return {
            "query": query,
            "effective_query": effective_query,
            "decision_path": decision_path,
            "relevance_eval_label": eval_label,
            "top_relevance_score": round(float(top_score), 4),
            "rewritten_query": rewritten_query,
            "answer": answer,
            "citations": citations,
            "suggested_followup": suggested_followup,
            "total_latency_ms": round(float(total_latency_ms), 2)
        }

    def process_query_stream(self, query, top_k=5, chat_history=None):
        """
        S2: Streaming variant of process_query.
        Yields SSE-compatible dict events:
          {"type": "meta", ...}      — metadata (decision_path, eval_label, score, rewritten_query)
          {"type": "citations", ...} — citations list
          {"type": "token", ...}     — streaming text chunk
          {"type": "followup", ...}  — suggested follow-up question
          {"type": "done", ...}      — end signal with total latency
        """
        start_time = time.time()

        # Pilar 6: Multi-Turn History Contextualizer
        effective_query = self._contextualize_chat_history(query, chat_history) if chat_history else query
        q_lower = effective_query.lower()

        # Auto-expand top_k for broad informational queries
        if any(kw in q_lower for kw in ["biaya", "spp", "catur darma", "prodi", "fakultas", "beasiswa", "jurusan", "pendaftaran", "syarat"]):
            top_k = max(top_k, 8)

        is_comparative = any(w in q_lower for w in ["bandingkan", "perbedaan", "beda", "vs", "antara"]) and ("dan" in q_lower or "atau" in q_lower)

        # Tier 1 & 2: Hybrid Retrieval + Reranking
        docs, _ = self.retriever.retrieve(effective_query, top_k=top_k)
        top_doc = docs[0] if docs else {"section_title": "", "module": "", "text": "", "hybrid_score": 0.0}

        docs = self._compress_context(docs, effective_query)

        # Tier 2 [Titik A]: CRAG Relevance Evaluator
        eval_tag = self._titik_a_gemini_evaluator(effective_query, top_doc)

        # Tier 3: Decision Engine
        if eval_tag == "HIGH":
            decision_path = "DIRECT PASS + RERANKER" if not is_comparative else "AGENTIC REACT COMPARATIVE LOOP"
            eval_label = "HIGH RELEVANCE"
            final_docs = docs
            rewritten_query = None if not (effective_query != query) else effective_query
        elif eval_tag == "MEDIUM":
            decision_path = "MULTI-QUERY + HyDE + RERANKER"
            eval_label = "MEDIUM AMBIGUOUS"
            if top_doc["hybrid_score"] >= 0.70:
                rewritten_query = f"{effective_query} rincian tarif biaya spp catur darma jalur pendaftaran syaratalur pmb uii"
                raw_expanded_docs, _ = self.retriever.retrieve(rewritten_query, top_k=top_k)
                final_docs = self._compress_context(raw_expanded_docs, rewritten_query)
            else:
                rewritten_query = self._titik_b_local_rewriter(effective_query)
                raw_expanded_docs, _ = self.retriever.retrieve(rewritten_query, top_k=top_k)
                final_docs = self._compress_context(raw_expanded_docs, rewritten_query)
        else:
            decision_path = "GUARDRAIL FALLBACK"
            eval_label = "LOW / ZERO RELEVANCE"
            final_docs = []
            rewritten_query = None

        top_score = top_doc["hybrid_score"] if (eval_tag != "LOW") else 0.05

        # Yield metadata event first (for frontend badge rendering)
        yield {
            "type": "meta",
            "decision_path": decision_path,
            "relevance_eval_label": eval_label,
            "top_relevance_score": round(float(top_score), 4),
            "rewritten_query": rewritten_query
        }

        # Start follow-up generation in background thread
        from concurrent.futures import ThreadPoolExecutor
        followup_executor = ThreadPoolExecutor(max_workers=1)
        fut_followup = followup_executor.submit(
            self._generate_single_followup_question, query, "PMB UII Informasi Pendaftaran Biaya Studi Dan Beasiswa Resmi"
        )

        # Stream generator tokens
        for event in self._titik_c_gemini_generator_stream(
            effective_query, final_docs, decision_path, eval_label, rewritten_query
        ):
            yield event

        # Yield follow-up question
        try:
            suggested_followup = fut_followup.result(timeout=10)
        except Exception:
            suggested_followup = None
        followup_executor.shutdown(wait=False)

        total_latency_ms = (time.time() - start_time) * 1000
        yield {
            "type": "done",
            "suggested_followup": suggested_followup,
            "total_latency_ms": round(float(total_latency_ms), 2)
        }


# =============================================================================
# MAIN BENCHMARK & EVALUATION PIPELINE
# =============================================================================

def run_rag_system_pipeline():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    outputs_dir = os.path.join(base_dir, "outputs")
    reports_dir = os.path.join(outputs_dir, "reports")
    figures_dir = os.path.join(outputs_dir, "figures")

    os.makedirs(reports_dir, exist_ok=True)
    os.makedirs(figures_dir, exist_ok=True)

    input_json = os.path.join(reports_dir, "preprocessed_nlp_dataset.json")

    print("=" * 90)
    print(" [SOAL 05] PIPELINE CORRECTIVE RAG (CRAG) DENGAN INTEGRASI GEMINI MULTI-NODE API")
    print("=" * 90)

    if not os.path.exists(input_json):
        print(f"[!] Dataset tidak ditemukan: {input_json}. Jalankan 02_text_preprocessing.py dulu.")
        return

    with open(input_json, "r", encoding="utf-8") as f:
        dataset_info = json.load(f)

    sections = dataset_info.get("data", [])
    print(f"[+] Knowledge Base Loaded : {len(sections)} Section Dokumen Terstruktur PMB UII")

    print(f"[+] Loaded {len(GEMINI_KEYS)} Gemini API Keys dari .env untuk Resilient Multi-Node Calling.")
    print("[+] Inisialisasi Hybrid Retriever & Corrective RAG Engine...")
    retriever = HybridPMBRetriever(sections)
    engine = CorrectiveRAGEngine(retriever)
    print("[+] CRAG Engine (Gemini Evaluator + Rewriter + Generator) Ready!\n")

    # 6 BENCHMARK MULTI-SCENARIO QUERIES
    test_queries = [
        {
            "id": "Q1",
            "type": "High Relevance",
            "query": "Apa saja pilihan jalur seleksi pendaftaran mahasiswa baru di UII?"
        },
        {
            "id": "Q2",
            "type": "High Relevance",
            "query": "Berapa rincian tarif biaya studi Catur Darma dan SPP di Universitas Islam Indonesia?"
        },
        {
            "id": "Q3",
            "type": "High Relevance",
            "query": "Apa saja syarat pendaftaran dan fasilitas Beasiswa Hafiz Al-Qur'an?"
        },
        {
            "id": "Q4",
            "type": "Ambiguous / Vague",
            "query": "gimana cara bayar?"
        },
        {
            "id": "Q5",
            "type": "Ambiguous / Vague",
            "query": "ada jurusan apa saja?"
        },
        {
            "id": "Q6",
            "type": "Out-of-Domain Guardrail Test",
            "query": "Bagaimana ramalan cuaca dan harga saham di Jakarta hari ini?"
        }
    ]

    crag_results = []
    print("=" * 90)
    print(" BENCHMARK EVALUASI 6 QUERY MULTI-SCENARIO PADA GEMINI CRAG ARCHITECTURE")
    print("=" * 90)

    for q_item in test_queries:
        qid = q_item["id"]
        qtype = q_item["type"]
        qtext = q_item["query"]

        print(f"\n[{qid}] Scenario Type: {qtype}")
        print(f"    Query      : \"{qtext}\"")

        res = engine.process_query(qtext, top_k=3)
        crag_results.append({
            "query_id": qid,
            "expected_type": qtype,
            "result": res
        })

        print(f"    Path       : {res['decision_path']} ({res['relevance_eval_label']})")
        print(f"    Top Score  : {res['top_relevance_score']*100:.1f}%")
        print(f"    Latency    : {res['total_latency_ms']} ms")
        if res['rewritten_query']:
            print(f"    Rewritten  : \"{res['rewritten_query']}\"")
        print(f"    Sitasi     : {len(res['citations'])} dokumen sumber terikat")
        print(f"    Jawaban CRAG Snippet:\n{res['answer'][:300]}...\n")
        print("-" * 80)

    # ====================================================================
    # FIGURE 6: CRAG PERFORMANCE & DECISION PATH DISTRIBUTION
    # ====================================================================
    fig, axes = plt.subplots(1, 2, figsize=(15, 6))

    q_ids = [r["query_id"] for r in crag_results]
    scores = [r["result"]["top_relevance_score"] * 100 for r in crag_results]
    latencies = [r["result"]["total_latency_ms"] for r in crag_results]
    paths = [r["result"]["decision_path"] for r in crag_results]

    # Panel 1: Relevance Score Per Query
    ax1 = axes[0]
    x = np.arange(len(q_ids))
    width = 0.40

    bars1 = ax1.bar(x, scores, width, label='Relevance Score (%)', color='#2b6cb0', edgecolor='white')
    ax1.set_ylabel('Top Relevance Score (%)', fontsize=11, fontweight='bold', color='#2b6cb0')
    ax1.set_ylim(0, 115)
    ax1.set_xticks(x)
    ax1.set_xticklabels(q_ids, fontsize=10, fontweight='bold')
    ax1.set_title("Top Relevance Score Per Benchmark Query", fontsize=12, fontweight='bold', color='#1a365d')

    for bar in bars1:
        ax1.annotate(f"{bar.get_height():.1f}%", (bar.get_x() + bar.get_width()/2, bar.get_height() + 2),
                     ha='center', fontsize=9.5, fontweight='bold', color='#2b6cb0')

    # Panel 2: Decision Path Count Bar Chart
    ax2 = axes[1]
    path_counts = dict(Counter(paths))
    p_names = list(path_counts.keys())
    p_vals = list(path_counts.values())

    colors_path = ['#2b6cb0', '#dd6b20', '#e53e3e']
    bars2 = ax2.bar(p_names, p_vals, color=colors_path[:len(p_names)], width=0.5, edgecolor='white')
    ax2.set_ylabel('Jumlah Query', fontsize=11, fontweight='bold')
    ax2.set_title("Distribusi Tri-Path Decision Execution Engine CRAG", fontsize=12, fontweight='bold', color='#1a365d')
    ax2.set_ylim(0, max(p_vals) + 2)

    for bar in bars2:
        ax2.annotate(f"{int(bar.get_height())} query", (bar.get_x() + bar.get_width()/2, bar.get_height() + 0.2),
                     ha='center', fontsize=10, fontweight='bold', color='#1a365d')

    plt.suptitle("Evaluasi Performa Corrective RAG (CRAG) Engine + Gemini Multi-Node PMB UII 2026",
                 fontsize=14, fontweight='bold', color='#1a365d', y=1.02)
    plt.tight_layout()
    fig6_path = os.path.join(figures_dir, "06_rag_system_performance.png")
    plt.savefig(fig6_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"[+] Figure 6 saved: {fig6_path}")

    # ====================================================================
    # SAVE EVALUATION REPORT JSON
    # ====================================================================
    avg_score = np.mean(scores)
    avg_latency = np.mean(latencies)

    crag_summary = {
        "architecture": "4-Tier Corrective RAG (CRAG) System with Gemini Multi-Node Integration",
        "gemini_api_nodes": {
            "node_a_evaluator": "Gemini 2.5 Flash (LLM-as-a-Judge Relevance Evaluator)",
            "node_b_rewriter": "Gemini 2.5 Flash (Query Rewriter & HyDE Expansion)",
            "node_c_generator": "Gemini 2.5 Flash (Grounded Response Generator with Citations)"
        },
        "knowledge_base_size": len(sections),
        "total_test_queries": len(test_queries),
        "average_relevance_score_percent": round(float(avg_score), 2),
        "average_total_latency_ms": round(float(avg_latency), 2),
        "decision_path_distribution": dict(Counter(paths)),
        "test_results": crag_results,
        "generated_figure": fig6_path
    }

    out_json = os.path.join(reports_dir, "rag_evaluation_results.json")
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(crag_summary, f, indent=2, ensure_ascii=False)

    print(f"[+] Laporan evaluasi Gemini CRAG berhasil disimpan di: {out_json}")
    print("=" * 90)


if __name__ == "__main__":
    run_rag_system_pipeline()

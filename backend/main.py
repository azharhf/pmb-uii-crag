"""
================================================================================
UJIAN AKHIR SEMESTER (UAS) - TRENDING TOPICS ON STATISTICS 2026
--------------------------------------------------------------------------------
FASTAPI BACKEND SERVICE FOR HUGGING FACE SPACES DEPLOYMENT
--------------------------------------------------------------------------------
API Endpoints:
- GET  /         : API status & metadata
- GET  /health   : Healthcheck for Hugging Face Spaces Container
- POST /api/chat : Core Corrective RAG (CRAG) Endpoint (Gemini 3.6 Flash + IndoBERT)
- GET  /api/docs : PMB UII Knowledge Base Documents Explorer
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
import importlib

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE_DIR = PROJECT_ROOT
from typing import Optional, List, Dict, Any
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

# Add project root to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

rag_module = importlib.import_module("pipeline.05_rag_system")
HybridPMBRetriever = rag_module.HybridPMBRetriever
CorrectiveRAGEngine = rag_module.CorrectiveRAGEngine

# Global variables for Retriever and CRAG Engine
retriever_instance: Optional[HybridPMBRetriever] = None
crag_engine_instance: Optional[CorrectiveRAGEngine] = None
knowledge_base_sections: List[Dict[str, Any]] = []

# Supabase REST Credentials for CRAG Audit Logs
s_url = None
s_key = None
try:
    from dotenv import load_dotenv
    base_dir_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    load_dotenv(os.path.join(base_dir_path, ".env"))
    s_url = os.getenv("SUPABASE_URL")
    s_key = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_ANON_KEY")
    if s_url and s_key:
        print("[+] Supabase REST logging configured for CRAG audit logging.")
except Exception as e:
        print(f"[!] Supabase config notice: {e}")


def log_crag_to_supabase(
    user_query: str,
    decision_path: str,
    confidence_label: str,
    rewritten_query: Optional[str],
    top_score: float,
    latency_ms: float,
    answer_generated: str,
    citations_count: int
):
    if not (s_url and s_key):
        return
    try:
        import requests
        headers = {
            "apikey": s_key,
            "Authorization": f"Bearer {s_key}",
            "Content-Type": "application/json",
            "Prefer": "return=minimal"
        }
        payload = {
            "user_query": user_query,
            "decision_path": str(decision_path)[:50],
            "confidence_label": str(confidence_label)[:50],
            "rewritten_query": str(rewritten_query)[:255] if rewritten_query else None,
            "top_score": float(top_score),
            "latency_ms": float(latency_ms),
            "answer_generated": str(answer_generated)[:1000] if answer_generated else None,
            "citations_count": int(citations_count)
        }
        requests.post(f"{s_url.rstrip('/')}/rest/v1/crag_logs", json=payload, headers=headers, timeout=3)
        print(f"[+] Successfully logged query '{user_query[:30]}...' to Supabase 'crag_logs' table.")
    except Exception as e:
        print(f"[!] Warning: Failed to insert crag_logs to Supabase: {e}")


def init_crag_engine():
    global crag_engine_instance, knowledge_base_sections
    if crag_engine_instance is not None:
        return crag_engine_instance
        
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    json_path = os.path.join(base_dir, "outputs", "reports", "preprocessed_nlp_dataset.json")
    if os.path.exists(json_path):
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            knowledge_base_sections = data.get("data", [])

        print(f"[+] Loaded {len(knowledge_base_sections)} sections into FastAPI Backend Knowledge Base.")
        retriever_instance = HybridPMBRetriever(knowledge_base_sections)
        crag_engine_instance = CorrectiveRAGEngine(retriever_instance)
        print("[+] Corrective RAG Engine (Gemini 3.6 Flash + IndoBERT) initialized successfully.")
    else:
        print(f"[!] Warning: Knowledge Base JSON not found at {json_path}")
    return crag_engine_instance


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_crag_engine()
    yield


from fastapi.staticfiles import StaticFiles

# Initialize FastAPI App with Lifespan
app = FastAPI(
    title="UII Academic CRAG Backend API",
    description="Backend Service for PMB UII Corrective RAG System using Gemini 3.6 Flash & IndoBERT",
    version="1.0.0",
    lifespan=lifespan
)

# Enable CORS for Vercel Frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static download directories for official brochures & documents
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
pdf_dir = os.path.join(base_dir, "data", "raw", "brosur", "pdf")
unduh_dir = os.path.join(base_dir, "data", "raw", "unduh_dokumen")

if os.path.exists(pdf_dir):
    app.mount("/downloads/pdf", StaticFiles(directory=pdf_dir), name="downloads_pdf")

if os.path.exists(unduh_dir):
    app.mount("/downloads/unduh", StaticFiles(directory=unduh_dir), name="downloads_unduh")


@app.get("/api/official_documents")
def get_official_documents():
    """Returns a complete list of all official PDF and DOCX documents hosted on Supabase Storage CDN."""
    supabase_base = "https://idrhzigiaewgtqexfgbj.supabase.co/storage/v1/object/public/pmb-documents"
    if s_url:
        supabase_base = f"{s_url.rstrip('/')}/storage/v1/object/public/pmb-documents"

    # Direct Curated Manifest for Supabase Storage CDN
    official_manifest = [
        ("Brosur Fakultas Kedokteran FK UII", "2024-Brosur-FK.pdf", "Brosur PDF Resmi", "PDF", "1.85 MB", f"{supabase_base}/pdf/2024-Brosur-FK.pdf"),
        ("Brosur Fakultas Hukum FH UII", "2024-Brosur-FH.pdf", "Brosur PDF Resmi", "PDF", "2.10 MB", f"{supabase_base}/pdf/2024-Brosur-FH.pdf"),
        ("Brosur Fakultas Ilmu Agama Islam FIAI UII", "Brosur FIAI 25_26.pdf", "Brosur PDF Resmi", "PDF", "1.92 MB", f"{supabase_base}/pdf/Brosur%20FIAI%2025_26.pdf"),
        ("Brosur Fakultas MIPA FMIPA UII", "2024-Brosur-FMIPA-1.pdf", "Brosur PDF Resmi", "PDF", "2.34 MB", f"{supabase_base}/pdf/2024-Brosur-FMIPA-1.pdf"),
        ("Brosur Fakultas Psikologi FPSB UII", "Brosur-FPSB.pdf", "Brosur PDF Resmi", "PDF", "2.05 MB", f"{supabase_base}/pdf/Brosur-FPSB.pdf"),
        ("Brosur Fakultas Teknik Sipil FTSP UII", "2024-Brosur-FTSP-1.pdf", "Brosur PDF Resmi", "PDF", "2.48 MB", f"{supabase_base}/pdf/2024-Brosur-FTSP-1.pdf"),
        ("Brosur Fakultas Teknologi Industri FTI UII", "Brosur FTI 25_26.pdf", "Brosur PDF Resmi", "PDF", "2.61 MB", f"{supabase_base}/pdf/Brosur%20FTI%2025_26.pdf"),
        ("Brosur Fakultas Bisnis dan Ekonomika FBE UII", "Brosur FBE 25_26.pdf", "Brosur PDF Resmi", "PDF", "2.23 MB", f"{supabase_base}/pdf/Brosur%20FBE%2025_26.pdf"),
        ("Brosur Panduan Umum PMB UII 2026", "Brosur-UII-170126.pdf", "Brosur PDF Resmi", "PDF", "1.81 MB", f"{supabase_base}/pdf/Brosur-UII-170126.pdf"),
        ("Brosur Program Pascasarjana Profesi UII", "030226-Brosur-Pasca-sarjana.pdf", "Brosur PDF Resmi", "PDF", "1.94 MB", f"{supabase_base}/pdf/030226-Brosur-Pasca-sarjana.pdf"),
        ("Surat Pernyataan Rapor Kedokteran Mandiri 2026", "Surat-Pernyataan-Rapor-Kedokteran-Mandiri-2026-2.pdf", "Panduan & Form Pendaftaran", "PDF", "0.45 MB", f"{supabase_base}/unduh/pdf/Surat-Pernyataan-Rapor-Kedokteran-Mandiri-2026-2.pdf"),
        ("Surat Pernyataan Tes Kedokteran Mandiri 2026", "Surat-Pernyataan-Tes-Kedokteran-Mandiri-2026.pdf", "Panduan & Form Pendaftaran", "PDF", "0.42 MB", f"{supabase_base}/unduh/pdf/Surat-Pernyataan-Tes-Kedokteran-Mandiri-2026.pdf"),
        ("Form Asesmen Diri Beasiswa Atlet dan Juara Seni", "Form-Asesmen-Diri-Beasiswa-Atlet-dan-Juara-Seni.docx", "Panduan & Form Pendaftaran", "DOCX", "0.15 MB", f"{supabase_base}/unduh/docx/Form-Asesmen-Diri-Beasiswa-Atlet-dan-Juara-Seni.docx"),
        ("Form Asesmen Diri Beasiswa Hafizah Hafiz", "Form-Asesmen-Diri-Beasiswa-Hafizah-Hafiz.docx", "Panduan & Form Pendaftaran", "DOCX", "0.18 MB", f"{supabase_base}/unduh/docx/Form-Asesmen-Diri-Beasiswa-Hafizah-Hafiz.docx"),
        ("Form Asesmen Diri Jalur Beasiswa Afirmasi", "Form-Asesmen-Diri-Jalur-Beasiswa-Afirmasi.docx", "Panduan & Form Pendaftaran", "DOCX", "0.16 MB", f"{supabase_base}/unduh/docx/Form-Asesmen-Diri-Jalur-Beasiswa-Afirmasi.docx"),
        ("Form Asesmen Diri Jalur Beasiswa Santri", "Form-Asesmen-Diri-Jalur-Beasiswa-Santri.docx", "Panduan & Form Pendaftaran", "DOCX", "0.17 MB", f"{supabase_base}/unduh/docx/Form-Asesmen-Diri-Jalur-Beasiswa-Santri.docx"),
        ("Surat Pernyataan Komitmen 2026", "Surat-Pernyataan-Komitmen-2026.docx", "Panduan & Form Pendaftaran", "DOCX", "0.12 MB", f"{supabase_base}/unduh/docx/Surat-Pernyataan-Komitmen-2026.docx"),
        ("Surat Pernyataan MABA Keabsahan Dokumen", "SURAT-PERNYATAAN-MABA.docx", "Panduan & Form Pendaftaran", "DOCX", "0.14 MB", f"{supabase_base}/unduh/docx/SURAT-PERNYATAAN-MABA.docx"),
    ]

    docs = []
    for title, fname, cat, ftype, sz, url in official_manifest:
        docs.append({
            "title": title,
            "filename": fname,
            "category": cat,
            "type": ftype,
            "size": sz,
            "download_url": url
        })

    return {"total": len(docs), "documents": docs}


class ChatRequest(BaseModel):
    query: str
    top_k: Optional[int] = 5
    chat_history: Optional[List[dict]] = None


class CitationItem(BaseModel):
    rank: int
    doc_id: str
    module: str
    section_title: str
    relevance_score: str
    raw_text: Optional[str] = None


class ChatResponse(BaseModel):
    query: str
    effective_query: Optional[str] = None
    decision_path: str
    relevance_eval_label: str
    top_relevance_score: float
    rewritten_query: Optional[str] = None
    answer: str
    citations: List[CitationItem]
    suggested_followup: Optional[str] = None
    total_latency_ms: float


@app.get("/")
def root():
    return {
        "status": "online",
        "service": "UII Academic CRAG Backend API",
        "ai_model": "gemini-3.6-flash",
        "vector_embeddings": "indobenchmark/indobert-base-p1",
        "total_sections": len(knowledge_base_sections)
    }


@app.get("/health")
def healthcheck():
    return {"status": "healthy", "timestamp": time.time()}


def validate_security_firewall(user_query: str):
    """
    Multi-Layer Security Firewall & Anti-Prompt-Injection Shield.
    Blocks SQL Injection, Cross-Site Scripting (XSS), and Jailbreak/Prompt-Injection attacks.
    """
    if len(user_query) > 1000:
        raise HTTPException(status_code=400, detail="[SECURITY FIREWALL] Query length exceeds maximum limit of 1000 characters.")

    injection_patterns = [
        r"ignore\s+previous\s+instruction",
        r"disregard\s+all\s+rule",
        r"system\s+override",
        r"you\s+are\s+now\s+DAN",
        r"jailbreak",
        r"eval\(",
        r"<script.*?>",
        r"drop\s+table",
        r"union\s+select",
        r"exec\s*\("
    ]

    for pattern in injection_patterns:
        if re.search(pattern, user_query, re.IGNORECASE):
            raise HTTPException(
                status_code=403,
                detail="[SECURITY FIREWALL NOTICE] Query terdeteksi memuat pola serangan atau Prompt Injection yang dilarang."
            )


@app.middleware("http")
async def add_security_headers(request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response


from fastapi import FastAPI, HTTPException, BackgroundTasks

@app.get("/api/rag/health")
@app.get("/health")
def health_check():
    """Health check endpoint to verify Backend + Knowledge Base status."""
    kb_loaded = len(knowledge_base_sections) > 0
    engine_ready = crag_engine_instance is not None
    return {
        "status": "healthy" if (kb_loaded and engine_ready) else "degraded",
        "knowledge_base_sections": len(knowledge_base_sections),
        "engine_initialized": engine_ready,
        "supabase_logging": (s_url is not None and s_key is not None),
        "keys_configured": len(GEMINI_KEYS)
    }


@app.post("/api/rag/chat", response_model=ChatResponse)
@app.post("/api/v1/chat", response_model=ChatResponse)
@app.post("/api/chat", response_model=ChatResponse)
def chat_endpoint(request: ChatRequest, background_tasks: BackgroundTasks):
    if not request.query or not request.query.strip():
        raise HTTPException(status_code=400, detail="Query string cannot be empty.")

    validate_security_firewall(request.query.strip())

    if not crag_engine_instance:
        raise HTTPException(status_code=500, detail="CRAG Engine not initialized.")

    try:
        res = crag_engine_instance.process_query(
            request.query.strip(),
            top_k=request.top_k or 5,
            chat_history=request.chat_history
        )
        background_tasks.add_task(
            log_crag_to_supabase,
            user_query=request.query.strip(),
            decision_path=res.get("decision_path", "UNKNOWN"),
            confidence_label=res.get("relevance_eval_label", "UNKNOWN"),
            rewritten_query=res.get("rewritten_query"),
            top_score=res.get("top_relevance_score", 0.0),
            latency_ms=res.get("latency_ms", 0.0),
            answer_generated=res.get("answer", ""),
            citations_count=len(res.get("citations", []))
        )

        citations_items = []
        for c in res.get("citations", []):
            citations_items.append(CitationItem(
                rank=c.get("rank", 0),
                doc_id=str(c.get("doc_id", "")),
                module=c.get("module", ""),
                section_title=c.get("section_title", ""),
                relevance_score=str(c.get("relevance_score", "0")),
                raw_text=c.get("raw_text")
            ))

        return ChatResponse(
            query=res.get("query", request.query.strip()),
            effective_query=res.get("effective_query"),
            decision_path=res.get("decision_path", "UNKNOWN"),
            relevance_eval_label=res.get("relevance_eval_label", "UNKNOWN"),
            top_relevance_score=float(res.get("top_relevance_score", 0.0)),
            rewritten_query=res.get("rewritten_query"),
            answer=res.get("answer", ""),
            citations=citations_items,
            total_latency_ms=float(res.get("latency_ms", 0.0))
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Inference error: {str(e)}")


@app.post("/api/rag/stream")
@app.post("/api/v1/chat/stream")
@app.post("/api/chat/stream")
def chat_stream_endpoint(request: ChatRequest, background_tasks: BackgroundTasks):
    """S2b: True Real-time SSE Token Streaming via Gemini generate_content_stream."""
    if not request.query or not request.query.strip():
        raise HTTPException(status_code=400, detail="Query string cannot be empty.")

    validate_security_firewall(request.query.strip())

    if not crag_engine_instance:
        raise HTTPException(status_code=500, detail="CRAG Engine not initialized.")

    def event_generator():
        meta_info = {}
        cit_count = 0
        try:
            history_payload = request.chat_history if request.chat_history else None

            for event in crag_engine_instance.process_query_stream(
                request.query.strip(),
                top_k=request.top_k or 5,
                chat_history=history_payload
            ):
                event_type = event.get("type", "unknown")

                if event_type == "meta":
                    meta_info = event
                    yield f"event: meta\ndata: {json.dumps(event)}\n\n"

                elif event_type == "citations":
                    cit_count = len(event.get("citations", []))
                    yield f"event: citations\ndata: {json.dumps(event)}\n\n"

                elif event_type == "token":
                    yield f"event: token\ndata: {json.dumps({'chunk': event['chunk']})}\n\n"

                elif event_type == "final":
                    # Guardrail fallback — stream the full answer as a single token
                    yield f"event: token\ndata: {json.dumps({'chunk': event['answer']})}\n\n"
                    if event.get("citations"):
                        cit_count = len(event.get("citations", []))
                        yield f"event: citations\ndata: {json.dumps({'type': 'citations', 'citations': event['citations']})}\n\n"

                elif event_type == "done":
                    yield f"event: done\ndata: {json.dumps(event)}\n\n"
                    # Background log to Supabase crag_logs table
                    background_tasks.add_task(
                        log_crag_to_supabase,
                        user_query=request.query.strip(),
                        decision_path=meta_info.get("decision_path", "STREAM_PASS"),
                        confidence_label=meta_info.get("relevance_eval_label", "NORMAL"),
                        rewritten_query=meta_info.get("rewritten_query"),
                        top_score=meta_info.get("top_relevance_score", 0.0),
                        latency_ms=event.get("total_latency_ms", 0.0),
                        answer_generated=event.get("answer", "") or "Stream Completed",
                        citations_count=cit_count
                    )

        except Exception as e:
            yield f"event: error\ndata: {json.dumps({'detail': str(e)})}\n\n"

    from fastapi.responses import StreamingResponse
    headers = {
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "X-Accel-Buffering": "no"
    }
    return StreamingResponse(event_generator(), media_type="text/event-stream", headers=headers)


@app.get("/api/documents")
def get_documents_metadata():
    if not knowledge_base_sections:
        return {"total": 0, "modules": {}}

    modules_count = {}
    for sec in knowledge_base_sections:
        mod = sec.get("module", "UNKNOWN")
        modules_count[mod] = modules_count.get(mod, 0) + 1

    return {
        "total_chunks": len(knowledge_base_sections),
        "modules_breakdown": modules_count
    }


MODULE_FILE_MAP = {
    "BROSUR": ("brosur", "brosur_knowledge_base.md"),
    "BIAYA": ("biaya", "biaya_pmb_knowledge_base.md"),
    "BEASISWA": ("jalur_beasiswa", "beasiswa_knowledge_base.md"),
    "JALUR_BEASISWA": ("jalur_beasiswa", "beasiswa_knowledge_base.md"),
    "SELEKSI": ("jalur_tes", "tes_knowledge_base.md"),
    "JALUR_TES": ("jalur_tes", "tes_knowledge_base.md"),
    "JALUR_RAPOR": ("jalur_rapor", "rapor_knowledge_base.md"),
    "RAPOR": ("jalur_rapor", "rapor_knowledge_base.md"),
    "PRODI": ("prodi", "prodi_knowledge_base.md"),
    "KONTAK": ("kontak", "kontak_knowledge_base.md"),
    "FAQ": ("faq", "faq_knowledge_base.md"),
    "PEMBAYARAN": ("pembayaran", "pembayaran_knowledge_base.md"),
    "UNDUH_DOKUMEN": ("unduh_dokumen", "unduh_knowledge_base.md"),
    "UNDUH": ("unduh_dokumen", "unduh_knowledge_base.md"),
    "CONTOH_SOAL": ("contoh_soal", "soal_knowledge_base.md"),
    "SOAL": ("contoh_soal", "soal_knowledge_base.md"),
}


@app.get("/api/document/{module_name}")
def get_full_document(module_name: str):
    clean_mod = module_name.split(":")[0].upper().strip()
    if clean_mod not in MODULE_FILE_MAP:
        matched_key = None
        for k in MODULE_FILE_MAP:
            if k == clean_mod or k in clean_mod or clean_mod in k:
                matched_key = k
                break
        if matched_key:
            folder, fname = MODULE_FILE_MAP[matched_key]
            mod_key = matched_key
        else:
            folder, fname = "brosur", "brosur_knowledge_base.md"
            mod_key = "BROSUR"
    else:
        folder, fname = MODULE_FILE_MAP[clean_mod]
        mod_key = clean_mod

    # 1. Try loading from Supabase Storage CDN first with User-Agent header
    content = None
    sup_url = os.environ.get("SUPABASE_URL", "") or s_url or "https://idrhzigiaewgtqexfgbj.supabase.co"
    supabase_cdn = f"{sup_url.rstrip('/')}/storage/v1/object/public/pmb-documents/master_md/{fname}"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

    try:
        import requests
        r = requests.get(supabase_cdn, headers=headers, timeout=10)
        if r.status_code == 200 and r.text:
            content = r.text
    except Exception as e:
        print(f"[!] Supabase CDN fetch error for {fname}: {e}")

    # 2. Fallback to local disk
    if content is None:
        file_path = os.path.join(base_dir, "data", "processed", folder, fname)
        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

    # 3. Direct Hardcoded CDN Retry Fallback
    if content is None:
        try:
            import requests
            direct_url = f"https://idrhzigiaewgtqexfgbj.supabase.co/storage/v1/object/public/pmb-documents/master_md/{fname}"
            r = requests.get(direct_url, headers=headers, timeout=12)
            if r.status_code == 200 and r.text:
                content = r.text
        except Exception:
            pass

    if content is None:
        raise HTTPException(status_code=404, detail=f"Document file {fname} not found.")

    return {
        "module": mod_key,
        "filename": fname,
        "file_path": supabase_cdn,
        "total_chars": len(content),
        "content": content
    }


if __name__ == "__main__":
    uvicorn.run("backend.main:app", host="0.0.0.0", port=7860, reload=True)


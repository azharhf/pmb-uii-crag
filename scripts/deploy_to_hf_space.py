import os
import shutil
from dotenv import dotenv_values
from huggingface_hub import HfApi

TOKEN = dotenv_values(".env").get("HF_TOKEN") or os.environ.get("HF_TOKEN")
USERNAME = "azharhf"
SPACE_NAME = "pmb-uii-crag-backend"
REPO_ID = f"{USERNAME}/{SPACE_NAME}"

def deploy():
    api = HfApi(token=TOKEN)
    
    print(f"[1/5] Verifying user token for {USERNAME}...")
    user_info = api.whoami()
    print(f"      Authenticated as: {user_info['name']}")
    
    # Prepare temporary staging folder
    staging_dir = os.path.abspath("scratch_hf_deploy")
    if os.path.exists(staging_dir):
        shutil.rmtree(staging_dir)
    os.makedirs(staging_dir, exist_ok=True)
    
    # 1. Create Space README.md
    readme_content = """---
title: PMB UII CRAG Backend API
emoji: 🎓
colorFrom: blue
colorTo: indigo
sdk: gradio
sdk_version: 4.44.1
app_file: app.py
pinned: false
license: mit
---

# PMB UII AI Academic Assistant - FastAPI + Gradio + ZeroGPU Backend
"""
    with open(os.path.join(staging_dir, "README.md"), "w", encoding="utf-8") as f:
        f.write(readme_content)

    # 2. Create app.py — Monkey-patch Gradio's create_app to inject middleware into the REAL server app
    app_py_content = r'''import os
import sys
import json
import warnings
import re as _re

os.environ["TF_ENABLE_ONEDNN_OPTS"] = "0"
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
os.environ["TOKENIZERS_PARALLELISM"] = "false"
warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=UserWarning)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# ──────────────────────────────────────────────────────────────────────────────
# STEP 0: Monkey-patch Gradio's App.create_app BEFORE importing anything else.
#         This ensures our middleware is injected into the ACTUAL server app
#         that demo.launch() creates internally — NOT the discarded demo.app.
# ──────────────────────────────────────────────────────────────────────────────
import gradio.routes as _gr_routes
from starlette.requests import Request as _Request
from starlette.responses import JSONResponse as _JSON, StreamingResponse as _Stream

# Import backend for use in middleware
import backend.main as backend

# Pre-initialize engine
backend.init_crag_engine()

# Save original create_app
_orig_create_app = _gr_routes.App.create_app

def _patched_create_app(*args, **kwargs):
    """Monkey-patched create_app that injects our API middleware."""
    app = _orig_create_app(*args, **kwargs)

    # Add CORS
    from fastapi.middleware.cors import CORSMiddleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["*"],
    )

    @app.middleware("http")
    async def api_interceptor(request: _Request, call_next):
        path = request.url.path.rstrip("/")
        method = request.method

        # CORS preflight
        if method == "OPTIONS" and (path.startswith("/api/") or path == "/health"):
            return _JSON({}, headers={
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
                "Access-Control-Allow-Headers": "*",
                "Access-Control-Allow-Private-Network": "true",
            })

        # GET /health
        if method == "GET" and path in ("/health", "/api/rag/health"):
            engine = backend.init_crag_engine()
            return _JSON({
                "status": "healthy" if engine else "degraded",
                "knowledge_base_sections": len(backend.knowledge_base_sections),
                "engine_initialized": engine is not None,
                "supabase_logging": bool(backend.s_url and backend.s_key),
            })

        # GET /api/documents
        if method == "GET" and path == "/api/documents":
            if not backend.knowledge_base_sections:
                return _JSON({"total": 0, "modules": {}})
            mc = {}
            for sec in backend.knowledge_base_sections:
                m = sec.get("module", "UNKNOWN")
                mc[m] = mc.get(m, 0) + 1
            return _JSON({"total_chunks": len(backend.knowledge_base_sections), "modules_breakdown": mc})

        # POST /api/chat
        if method == "POST" and path in ("/api/chat", "/api/v1/chat", "/api/rag/chat"):
            try:
                body = await request.json()
                query = (body.get("query") or "").strip()
                if not query:
                    return _JSON({"error": "Query cannot be empty."}, status_code=400)
                if len(query) > 1000:
                    return _JSON({"error": "Query too long."}, status_code=400)
                _inj = [r"ignore\s+previous\s+instruction", r"disregard\s+all\s+rule",
                         r"system\s+override", r"you\s+are\s+now\s+DAN", r"jailbreak",
                         r"eval\(", r"<script.*?>", r"drop\s+table", r"union\s+select", r"exec\s*\("]
                for p in _inj:
                    if _re.search(p, query, _re.IGNORECASE):
                        return _JSON({"error": "Security firewall: blocked."}, status_code=403)

                engine = backend.init_crag_engine()
                if not engine:
                    return _JSON({"error": "Engine not initialized."}, status_code=503)

                res = engine.process_query(query, top_k=body.get("top_k", 5), chat_history=body.get("chat_history"))
                try:
                    backend.log_crag_to_supabase(
                        user_query=query,
                        decision_path=res.get("decision_path", "UNKNOWN"),
                        confidence_label=res.get("relevance_eval_label", "UNKNOWN"),
                        rewritten_query=res.get("rewritten_query"),
                        top_score=res.get("top_relevance_score", 0.0),
                        latency_ms=res.get("latency_ms", 0.0),
                        answer_generated=res.get("answer", ""),
                        citations_count=len(res.get("citations", []))
                    )
                except Exception:
                    pass

                cits = []
                for c in res.get("citations", []):
                    cits.append({
                        "rank": c.get("rank", 0), "doc_id": str(c.get("doc_id", "")),
                        "module": c.get("module", ""), "section_title": c.get("section_title", ""),
                        "relevance_score": str(c.get("relevance_score", "0")),
                        "raw_text": c.get("raw_text")
                    })
                return _JSON({
                    "query": res.get("query", query),
                    "effective_query": res.get("effective_query"),
                    "decision_path": res.get("decision_path", "UNKNOWN"),
                    "relevance_eval_label": res.get("relevance_eval_label", "UNKNOWN"),
                    "top_relevance_score": float(res.get("top_relevance_score", 0.0)),
                    "rewritten_query": res.get("rewritten_query"),
                    "answer": res.get("answer", ""),
                    "citations": cits,
                    "suggested_followup": res.get("suggested_followup"),
                    "total_latency_ms": float(res.get("latency_ms", 0.0))
                })
            except Exception as e:
                import traceback; traceback.print_exc()
                return _JSON({"error": f"Inference error: {str(e)}"}, status_code=500)

        # POST /api/chat/stream
        if method == "POST" and path in ("/api/chat/stream", "/api/v1/chat/stream", "/api/rag/stream"):
            try:
                body = await request.json()
                query = (body.get("query") or "").strip()
                if not query:
                    return _JSON({"error": "Query cannot be empty."}, status_code=400)
                if len(query) > 1000:
                    return _JSON({"error": "Query too long."}, status_code=400)

                engine = backend.init_crag_engine()
                if not engine:
                    return _JSON({"error": "Engine not initialized."}, status_code=503)

                top_k = body.get("top_k", 5)
                chat_history = body.get("chat_history")

                def event_gen():
                    meta_info = {}
                    cit_count = 0
                    try:
                        for ev in engine.process_query_stream(query, top_k=top_k, chat_history=chat_history):
                            et = ev.get("type", "unknown")
                            if et == "meta":
                                meta_info.update(ev)
                                yield f"event: meta\ndata: {json.dumps(ev)}\n\n"
                            elif et == "citations":
                                cit_count = len(ev.get("citations", []))
                                yield f"event: citations\ndata: {json.dumps(ev)}\n\n"
                            elif et == "token":
                                yield f"event: token\ndata: {json.dumps({'chunk': ev['chunk']})}\n\n"
                            elif et == "final":
                                yield f"event: token\ndata: {json.dumps({'chunk': ev['answer']})}\n\n"
                                if ev.get("citations"):
                                    cit_count = len(ev["citations"])
                                    yield f"event: citations\ndata: {json.dumps({'type':'citations','citations':ev['citations']})}\n\n"
                            elif et == "done":
                                yield f"event: done\ndata: {json.dumps(ev)}\n\n"
                                try:
                                    backend.log_crag_to_supabase(
                                        user_query=query,
                                        decision_path=meta_info.get("decision_path", "STREAM"),
                                        confidence_label=meta_info.get("relevance_eval_label", "NORMAL"),
                                        rewritten_query=meta_info.get("rewritten_query"),
                                        top_score=meta_info.get("top_relevance_score", 0.0),
                                        latency_ms=ev.get("total_latency_ms", 0.0),
                                        answer_generated=ev.get("answer", "") or "Stream Done",
                                        citations_count=cit_count
                                    )
                                except Exception:
                                    pass
                    except Exception as e:
                        yield f"event: error\ndata: {json.dumps({'detail': str(e)})}\n\n"

                return _Stream(event_gen(), media_type="text/event-stream", headers={
                    "Cache-Control": "no-cache", "Connection": "keep-alive",
                    "X-Accel-Buffering": "no", "Access-Control-Allow-Origin": "*",
                })
            except Exception as e:
                return _JSON({"error": f"Stream error: {str(e)}"}, status_code=500)

        # Pass through to Gradio for all other routes
        response = await call_next(request)
        response.headers["Access-Control-Allow-Private-Network"] = "true"
        response.headers["X-Content-Type-Options"] = "nosniff"
        return response

    print("[+] API middleware injected into ACTUAL Gradio server app via create_app patch.")
    return app

_gr_routes.App.create_app = _patched_create_app

# ──────────────────────────────────────────────────────────────────────────────
# STEP 1: Import Gradio + ZeroGPU (AFTER monkey-patch)
# ──────────────────────────────────────────────────────────────────────────────
import spaces
import gradio as gr

@spaces.GPU(duration=60)
def run_crag_inference(user_query: str):
    if not user_query or not user_query.strip():
        return {"error": "Query cannot be empty."}
    engine = backend.init_crag_engine()
    if not engine:
        return {"error": "Engine not initialized."}
    try:
        res = engine.process_query(user_query.strip(), top_k=5)
        try:
            backend.log_crag_to_supabase(
                user_query=user_query.strip(),
                decision_path=res.get("decision_path", "UNKNOWN"),
                confidence_label=res.get("relevance_eval_label", "UNKNOWN"),
                rewritten_query=res.get("rewritten_query"),
                top_score=res.get("top_relevance_score", 0.0),
                latency_ms=res.get("latency_ms", 0.0),
                answer_generated=res.get("answer", ""),
                citations_count=len(res.get("citations", []))
            )
        except Exception:
            pass
        return res
    except Exception as e:
        return {"error": str(e)}

# ──────────────────────────────────────────────────────────────────────────────
# STEP 2: Create Gradio UI
# ──────────────────────────────────────────────────────────────────────────────
theme = gr.themes.Soft(primary_hue="indigo", secondary_hue="blue", neutral_hue="slate")

with gr.Blocks(theme=theme, title="PMB UII AI Academic Assistant - CRAG Engine") as demo:
    gr.Markdown("""
    # 🎓 PMB UII AI Academic Assistant Backend
    ### ⚡ Corrective RAG (IndoBERT + Gemini 3.6 Flash) & ZeroGPU
    ---
    """)
    with gr.Row():
        with gr.Column(scale=2):
            query_in = gr.Textbox(label="💬 Pertanyaan", placeholder="Berapa biaya pendaftaran PMB UII?", lines=3)
            submit_btn = gr.Button("🚀 Kirim (ZeroGPU)", variant="primary", size="lg")
            gr.Examples(
                examples=[["Berapa biaya pendaftaran PMB UII?"],
                          ["Apa saja syarat pendaftaran jalur CBT UII?"],
                          ["Bagaimana alur pendaftaran FK UII?"]],
                inputs=query_in, label="💡 Contoh"
            )
        with gr.Column(scale=3):
            output_out = gr.JSON(label="📊 CRAG Response")
    submit_btn.click(fn=run_crag_inference, inputs=query_in, outputs=output_out, api_name="gradio_chat")

# ──────────────────────────────────────────────────────────────────────────────
# STEP 3: Launch (create_app monkey-patch injects middleware automatically)
# ──────────────────────────────────────────────────────────────────────────────
demo.launch(server_name="0.0.0.0", server_port=7860)
'''
    with open(os.path.join(staging_dir, "app.py"), "w", encoding="utf-8") as f:
        f.write(app_py_content)

    # 3. Create requirements.txt (NO google-genai to avoid websockets conflict)
    requirements_content = """spaces==0.51.1
huggingface-hub<0.24.0
fastapi<0.113.0
uvicorn>=0.28.0
pydantic>=2.6.0
python-dotenv>=1.0.0
sentence-transformers>=2.5.0
torch>=2.2.0
google-generativeai>=0.4.0
scikit-learn>=1.4.0
numpy>=1.26.0
matplotlib>=3.8.0
seaborn>=0.13.0
requests>=2.28.0
gradio==4.44.1
"""
    with open(os.path.join(staging_dir, "requirements.txt"), "w", encoding="utf-8") as f:
        f.write(requirements_content)

    # 4. Copy required directories
    shutil.copytree("pipeline", os.path.join(staging_dir, "pipeline"), ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    shutil.copytree("outputs", os.path.join(staging_dir, "outputs"), ignore=shutil.ignore_patterns("figures", "*.png", "*.jpg"))
    shutil.copytree("backend", os.path.join(staging_dir, "backend"), ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))

    print(f"[2/5] Uploading project files to Hugging Face Space '{REPO_ID}'...")
    try:
        api.upload_folder(
            folder_path=staging_dir,
            repo_id=REPO_ID,
            repo_type="space",
            commit_message="ZeroGPU + FastAPI routes injected via add_api_route (no Gradio hijack)"
        )
        print("      Files uploaded successfully!")
    except Exception as e:
        print(f"      [!] Upload Error: {e}")
        return

    # 5. Upload Secrets from .env
    print("[3/5] Setting Space Secrets from .env...")
    env_vars = dotenv_values(".env")
    secret_keys = ["GEMINI_API_KEYS", "SUPABASE_URL", "SUPABASE_ANON_KEY", "SUPABASE_SERVICE_KEY"]
    
    for key in secret_keys:
        val = env_vars.get(key)
        if val:
            try:
                api.add_space_secret(repo_id=REPO_ID, key=key, value=val)
                print(f"      Secret '{key}' configured.")
            except Exception as se:
                print(f"      [!] Secret '{key}' error: {se}")
        else:
            print(f"      [!] Warning: '{key}' not found in .env!")

    # Clean up local staging
    if os.path.exists(staging_dir):
        shutil.rmtree(staging_dir)

    # 6. Restart Space
    print("[4/5] Restarting Space to apply secrets into os.environ...")
    try:
        api.restart_space(repo_id=REPO_ID)
        print("      Space restarted successfully!")
    except Exception as re:
        print(f"      [!] Restart notice: {re}")

    print("[5/5] Deployment complete!")
    print(f"      Space URL: https://huggingface.co/spaces/{REPO_ID}")
    print(f"      Direct API URL: https://{USERNAME}-{SPACE_NAME}.hf.space")

if __name__ == "__main__":
    deploy()

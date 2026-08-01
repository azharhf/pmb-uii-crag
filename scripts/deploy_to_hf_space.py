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
    
    # 1. Create Space README.md (ZeroGPU Gradio Configuration)
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

# PMB UII AI Academic Assistant - FastAPI Backend Service

This Space hosts the FastAPI backend server powering the Corrective Retrieval-Augmented Generation (CRAG) engine.
"""
    with open(os.path.join(staging_dir, "README.md"), "w", encoding="utf-8") as f:
        f.write(readme_content)

    # 2. Create app.py with @spaces.GPU(duration=60) and PNA header middleware
    app_py_content = """import os
import sys

# Ensure root directory is in sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import torch
import spaces
import gradio as gr
import backend.main as backend_main

# Mandatory ZeroGPU function requirement with explicit 60s duration allocation
@spaces.GPU(duration=60)
def run_crag_inference(user_query: str):
    \"\"\"ZeroGPU function requirement for Hugging Face ZeroGPU hardware allocation.\"\"\"
    if not user_query or not user_query.strip():
        return {"error": "Query string cannot be empty."}
    
    # Dynamically retrieve or initialize CRAG Engine instance
    engine = backend_main.crag_engine_instance
    if not engine:
        try:
            print("[+] Lazy-initializing CRAG Engine instance for ZeroGPU...")
            engine = backend_main.init_crag_engine()
            backend_main.crag_engine_instance = engine
        except Exception as ie:
            return {"error": f"Failed to initialize CRAG Engine: {str(ie)}"}
    
    try:
        res = engine.process_query(user_query.strip(), top_k=5)
        
        # Async Supabase logging
        try:
            backend_main.log_crag_to_supabase(
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

# Premium Design Theme
theme = gr.themes.Soft(
    primary_hue="indigo",
    secondary_hue="blue",
    neutral_hue="slate"
)

# Build Clean Native Gradio Interface
with gr.Blocks(theme=theme, title="PMB UII AI Academic Assistant - CRAG Engine") as demo:
    gr.Markdown(
        \"\"\"
        # 🎓 PMB UII AI Academic Assistant Backend
        ### ⚡ Powered by Corrective RAG (IndoBERT + Gemini 3.6 Flash) & Hugging Face ZeroGPU
        ---
        \"\"\"
    )
    
    with gr.Row():
        with gr.Column(scale=2):
            query_in = gr.Textbox(
                label="💬 Pertanyaan Seputar PMB UII",
                placeholder="Contoh: Berapa biaya pendaftaran PMB UII dan syarat jalur CBT?",
                lines=3
            )
            submit_btn = gr.Button("🚀 Kirim Pertanyaan (ZeroGPU)", variant="primary", size="lg")
            
            gr.Examples(
                examples=[
                    ["Berapa biaya pendaftaran PMB UII?"],
                    ["Apa saja syarat pendaftaran jalur CBT UII?"],
                    ["Bagaimana alur pendaftaran mahasiswa baru Fakultas Kedokteran UII?"]
                ],
                inputs=query_in,
                label="💡 Contoh Pertanyaan Populer"
            )
            
        with gr.Column(scale=3):
            output_out = gr.JSON(label="📊 Respons Terstruktur CRAG Engine (JSON Output)")

    submit_btn.click(
        fn=run_crag_inference,
        inputs=query_in,
        outputs=output_out,
        api_name="chat"
    )

# Inject Chrome Private Network Access (PNA) Header Middleware into demo.app
@demo.app.middleware("http")
async def allow_private_network_access(request, call_next):
    response = await call_next(request)
    response.headers["Access-Control-Allow-Private-Network"] = "true"
    response.headers["Access-Control-Allow-Origin"] = "*"
    return response

demo.launch()
"""
    with open(os.path.join(staging_dir, "app.py"), "w", encoding="utf-8") as f:
        f.write(app_py_content)

    # 3. Create requirements.txt (Includes spaces==0.51.1 and pinned hub/gradio)
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
            commit_message="Deploy backend with os.environ GEMINI_API_KEYS support"
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

    # 6. Restart Space to reload Environment Variables / Secrets into os.environ
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

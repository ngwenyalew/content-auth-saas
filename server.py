from fastapi import FastAPI, UploadFile, File
import os
import uuid
import shutil
import subprocess
from datetime import datetime
from supabase import create_client, Client

app = FastAPI()

# =========================
# 🧠 SUPABASE CONFIG (PASTE YOURS HERE)
# =========================
SUPABASE_URL = "https://tparixlwejsxnonjknei.supabase.co/rest/v1/"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InRwYXJpeGx3ZWpzeG5vbmprbmVpIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzY1NjQ0NTMsImV4cCI6MjA5MjE0MDQ1M30.tmoAZ6wrC7OR0IH2ACVcOKNcbYXmRvv_XpY9dClAW-g"

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# =========================
# 📁 LOCAL PATHS
# =========================
BASE_DIR = os.getcwd()

UPLOADS = os.path.join(BASE_DIR, "uploads")
SIGNED = os.path.join(BASE_DIR, "signed")
ARCHIVE = os.path.join(BASE_DIR, "archive")

C2PA_TOOL = os.path.join(BASE_DIR, "c2patool.exe")
MANIFEST = os.path.join(BASE_DIR, "manifest.json")

os.makedirs(UPLOADS, exist_ok=True)
os.makedirs(SIGNED, exist_ok=True)
os.makedirs(ARCHIVE, exist_ok=True)

# =========================
# 🚀 UPLOAD ENDPOINT
# =========================
@app.post("/upload")
async def upload_video(file: UploadFile = File(...)):

    asset_id = str(uuid.uuid4())

    input_path = os.path.join(UPLOADS, f"{asset_id}.mp4")
    signed_path = os.path.join(SIGNED, f"{asset_id}.mp4")

    # Save upload
    with open(input_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # 🔐 SIGN FILE (C2PA PIPELINE)
    subprocess.run([
        C2PA_TOOL,
        input_path,
        "-m", MANIFEST,
        "-o", signed_path,
        "-f"
    ])

    # 🗄️ SAVE TO SUPABASE
    supabase.table("assets").insert({
        "asset_id": asset_id,
        "filename": file.filename,
        "status": "signed",
        "created_at": datetime.utcnow().isoformat(),
        "verification_data": None
    }).execute()

    return {
        "asset_id": asset_id,
        "status": "signed",
        "verification_url": f"/verify/{asset_id}"
    }

# =========================
# 🔍 VERIFY ENDPOINT
# =========================
@app.get("/verify/{asset_id}")
def verify(asset_id: str):

    file_path = os.path.join(SIGNED, f"{asset_id}.mp4")

    if not os.path.exists(file_path):
        return {"status": "not found"}

    result = subprocess.run([
        C2PA_TOOL,
        file_path,
        "--info"
    ], capture_output=True, text=True)

    verification_text = result.stdout

    # 🗄️ UPDATE SUPABASE
    supabase.table("assets").update({
        "status": "verified",
        "verification_data": verification_text
    }).eq("asset_id", asset_id).execute()

    return {
        "asset_id": asset_id,
        "verification": verification_text
    }
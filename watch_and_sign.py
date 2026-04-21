import os
import time
import subprocess
import shutil
import datetime

BASE_DIR = os.getcwd()
INCOMING = os.path.join(BASE_DIR, "incoming")
SIGNED = os.path.join(BASE_DIR, "signed")
ARCHIVE = os.path.join(BASE_DIR, "archive")

C2PA_TOOL = os.path.join(BASE_DIR, "c2patool.exe")
MANIFEST = os.path.join(BASE_DIR, "manifest.json")
LOG_FILE = os.path.join(BASE_DIR, "log.csv")

def sign_file(filename):
    original_path = os.path.join(INCOMING, filename)
    watermarked_path = os.path.join(INCOMING, f"wm_{filename}")
    output_path = os.path.join(SIGNED, f"signed_{filename}")

    print(f"\nProcessing: {filename}")

    try:
        # 🎨 STEP 1: Add watermark using FFmpeg
        print("Adding watermark...")
        subprocess.run([
            "ffmpeg",
            "-i", original_path,
            "-vf", "drawtext=text='Standard of Truth':x=10:y=H-th-10:fontsize=24:fontcolor=white",
            "-codec:a", "copy",
            watermarked_path,
            "-y"
        ], check=True)

        # 🔐 STEP 2: Sign with c2patool
        print("Signing video...")
        subprocess.run([
            C2PA_TOOL,
            watermarked_path,
            "-m", MANIFEST,
            "-o", output_path,
            "-f"
        ], check=True)

        print(f"Signed: {filename}")

        # 🔍 STEP 3: Verify and display result
        print("Verifying signature...")
        subprocess.run([
            C2PA_TOOL,
            output_path,
            "--info"
        ])

        # 📊 STEP 4: Log result
        with open(LOG_FILE, "a") as f:
            f.write(f"{datetime.datetime.now()},{filename},signed\n")

        # 📦 STEP 5: Move original to archive
        shutil.move(original_path, os.path.join(ARCHIVE, filename))

        # 🧹 Cleanup watermarked temp file
        if os.path.exists(watermarked_path):
            os.remove(watermarked_path)

    except Exception as e:
        print(f"Error processing {filename}: {e}")

def watch_folder():
    print("Watching for new files...")

    processed = set()

    while True:
        files = os.listdir(INCOMING)

        for file in files:
            if file not in processed and file.lower().endswith(".mp4"):
                sign_file(file)
                processed.add(file)

        time.sleep(5)

if __name__ == "__main__":
    watch_folder()
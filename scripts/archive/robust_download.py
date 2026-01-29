from modelscope import snapshot_download
import os
import sys

# Target directory (Docker volume mount point)
TARGET_DIR = "/var/lib/docker/volumes/layra_model_weights/_data"

models = [
    {"id": "vidore/colqwen2.5-base", "name": "colqwen2.5-base"},
    {"id": "vidore/colqwen2.5-v0.2", "name": "colqwen2.5-v0.2"}
]

if not os.path.exists(TARGET_DIR):
    print(f"❌ Error: Target directory {TARGET_DIR} not found.")
    print("Please run this script with sudo or ensure the volume exists.")
    sys.exit(1)

for model in models:
    print(f"🚀 Starting robust download for {model['name']}...")
    try:
        # snapshot_download is resume-capable and optimized for China/global mirrors
        path = snapshot_download(
            model_id=model['id'],
            local_dir=os.path.join(TARGET_DIR, model['name']),
            cache_dir="/tmp/modelscope_cache"
        )
        # Create the 'complete' flag expected by Layra's init script
        with open(os.path.join(TARGET_DIR, model['name'], "complete.layra"), "w") as f:
            f.write("done")
        print(f"✅ {model['name']} downloaded to {path}")
    except Exception as e:
        print(f"❌ Failed to download {model['name']}: {e}")

print("\n🎉 All models processed.")

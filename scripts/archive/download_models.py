#!/usr/bin/env python3
"""
Download ColQwen2.5 models using huggingface_hub's snapshot_download
This handles LFS files and resumes interrupted downloads
"""

import os
import sys
from huggingface_hub import snapshot_download

# Create model_weights directory in current directory
TARGET_DIR = os.path.join(os.getcwd(), "model_weights")
os.makedirs(TARGET_DIR, exist_ok=True)

models = [
    {"id": "vidore/colqwen2.5-base", "name": "colqwen2.5-base"},
    {"id": "vidore/colqwen2.5-v0.2", "name": "colqwen2.5-v0.2"}
]

print(f"Downloading models to: {TARGET_DIR}")
print("=" * 60)

for model in models:
    model_dir = os.path.join(TARGET_DIR, model['name'])
    print(f"\n🚀 Downloading {model['name']} ({model['id']})...")
    
    try:
        # snapshot_download handles LFS files and resumes
        path = snapshot_download(
            repo_id=model['id'],
            local_dir=model_dir,
            local_dir_use_symlinks=False,  # Don't use symlinks, copy files directly
            resume_download=True,
            max_workers=4
        )
        
        # Create the 'complete' flag expected by Layra's init script
        with open(os.path.join(model_dir, "complete.layra"), "w") as f:
            f.write("done")
        
        print(f"✅ {model['name']} downloaded to {path}")
        
        # List downloaded files
        print(f"📁 Files in {model['name']}/:")
        files = os.listdir(model_dir)
        for f in sorted(files)[:10]:  # Show first 10 files
            if f != "complete.layra":
                size = os.path.getsize(os.path.join(model_dir, f))
                print(f"   - {f} ({size:,} bytes)")
        if len(files) > 10:
            print(f"   ... and {len(files) - 10} more files")
            
    except Exception as e:
        print(f"❌ Failed to download {model['name']}: {e}")
        import traceback
        traceback.print_exc()

print("\n" + "=" * 60)
print("🎉 Download complete!")

# If we need to copy to Docker volume, uncomment below
# docker_volume_path = "/var/lib/docker/volumes/layra_model_weights/_data"
# if os.path.exists(docker_volume_path):
#     print(f"\n📦 Copying to Docker volume: {docker_volume_path}")
#     os.system(f"sudo cp -r {TARGET_DIR}/* {docker_volume_path}/")
#     print("✅ Copied to Docker volume")
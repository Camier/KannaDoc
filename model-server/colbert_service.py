# app/core/colbert_service.py
import os
from colpali_engine.models import ColQwen2_5, ColQwen2_5_Processor
from colpali_engine.utils.torch_utils import ListDataset, get_torch_device
from torch.utils.data import DataLoader
import torch
from typing import List, cast
from transformers.utils.import_utils import is_flash_attn_2_available
from transformers import BitsAndBytesConfig
from tqdm import tqdm
from config import settings


def pick_compute_dtype() -> torch.dtype:
    if torch.cuda.is_available():
        major, _ = torch.cuda.get_device_capability()
        if major >= 8:
            return torch.bfloat16
        return torch.float16
    return torch.float32


compute_dtype = pick_compute_dtype()


class ColBERTService:
    def __init__(self, model_path):
        print(f"🚀 Initializing ColBERTService with model_path: {model_path}")
        print(
            f"   Path exists: {os.path.exists(model_path) if 'os' in globals() else 'N/A'}"
        )

        # Log environment variables for debugging
        env_vars = [
            "PYTORCH_CUDA_ALLOC_CONF",
            "PYTORCH_NO_CUDA_MEMORY_CACHING",
            "PYTORCH_CUDA_MEMORY_FRACTION",
            "CUDA_VISIBLE_DEVICES",
            "TOKENIZERS_PARALLELISM",
        ]
        print("🔧 Environment variables:")
        for var in env_vars:
            value = os.environ.get(var, "NOT SET")
            print(f"   {var}={value}")

        self.device = torch.device(get_torch_device("auto"))

        # --- HIGH PERFORMANCE CUDA SETTINGS ---
        # TF32 only beneficial on Ampere+ (SM >= 8.0)
        if torch.cuda.is_available():
            major, _ = torch.cuda.get_device_capability()
            if major >= 8:
                torch.backends.cuda.matmul.allow_tf32 = True
                torch.backends.cudnn.allow_tf32 = True
                print(f"🔧 TF32 enabled (Ampere+ GPU detected, SM {major}.x)")
            else:
                print(f"🔧 TF32 skipped (SM {major}.x < 8.0)")
        torch.backends.cudnn.benchmark = True

        # 4-bit quantization config
        bnb_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_use_double_quant=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=compute_dtype,
        )

        # Force SDPA (Optimized for Turing/RTX 5000 - Flash Attention 2 not supported)
        attn_impl = "sdpa"
        print(f"🚀 Using optimized attention implementation: {attn_impl}")

        print(f"🔧 Loading model from {model_path}...")
        print(f"   Using device: {self.device}")
        print(f"   Using compute dtype: {compute_dtype}")
        try:
            self.model = ColQwen2_5.from_pretrained(
                model_path,
                torch_dtype=compute_dtype,
                quantization_config=bnb_config,
                device_map=self.device,
                attn_implementation=attn_impl,
                local_files_only=True,
                trust_remote_code=True,
            ).eval()
            print("✅ Model loaded successfully!")
        except Exception as e:
            print(f"❌ Model loading failed: {e}")
            import traceback

            traceback.print_exc()
            raise

        # --- TORCH COMPILE DISABLED ---
        # "reduce-overhead" caused recompilation loops. Using Eager Mode for stability.
        # try:
        #     print("🚀 Compiling model with torch.compile (mode='reduce-overhead')...")
        #     self.model.visual = torch.compile(self.model.visual, mode="reduce-overhead")
        # except Exception as e:
        #     print(f"⚠️ Torch compile failed: {e}")

        # Explicitly disable inductor compilation to prevent zombie workers
        torch.compiler.disable()

        print("🔧 Loading processor...")
        try:
            self.processor = cast(
                ColQwen2_5_Processor,
                ColQwen2_5_Processor.from_pretrained(
                    model_path,
                    size={"shortest_edge": 768, "longest_edge": 1536},
                    local_files_only=True,
                    trust_remote_code=True,
                ),
            )
            print("✅ Processor loaded successfully!")
        except Exception as e:
            print(f"❌ Processor loading failed: {e}")
            import traceback

            traceback.print_exc()
            raise

    def warmup(self):
        """Warmup routine to populate CUDA caches"""
        print("🔥 Running Model Warmup (Text + Image)...")
        from PIL import Image
        import numpy as np

        # Dummy Text
        self.process_query(["warmup_query"])

        # Dummy Image (Black 224x224)
        dummy_img = Image.fromarray(np.zeros((224, 224, 3), dtype=np.uint8))
        self.process_image([dummy_img])
        print("✅ Warmup Complete: Model is Ready.")

    @torch.inference_mode()
    def process_query(self, queries: list) -> List[torch.Tensor]:
        dataloader = DataLoader(
            dataset=ListDataset[str](queries),
            batch_size=3,  # Optimized: was 2
            shuffle=False,
            collate_fn=lambda x: self.processor.process_queries(x),
        )

        qs: List[torch.Tensor] = []
        for batch_query in dataloader:
            with torch.no_grad():
                batch_query = {
                    k: v.to(self.model.device) for k, v in batch_query.items()
                }
                embeddings_query = self.model(**batch_query)
            qs.extend(list(torch.unbind(embeddings_query.to("cpu"))))
        for i in range(len(qs)):
            qs[i] = qs[i].float().tolist()
        return qs

    @torch.inference_mode()
    def process_image(self, images: List) -> List[List[float]]:
        # MEMORY OPTIMIZED: Process images with retry logic for OOM errors
        batch_size = 1
        max_retries = 3

        # Log image dimensions for debugging
        for i, img in enumerate(images[:3]):  # Log first 3 images
            if hasattr(img, "size"):
                w, h = img.size
                total_pixels = w * h
                print(
                    f"🔧 Image {i + 1}: {w}x{h} ({total_pixels} pixels, {total_pixels / 1e6:.2f}MP)"
                )

        print(f"🔧 Processing {len(images)} images with batch_size={batch_size}")
        print(
            f"🔧 GPU memory: {torch.cuda.memory_allocated() / 1e9:.2f}GB allocated, {torch.cuda.memory_reserved() / 1e9:.2f}GB reserved"
        )

        # Add additional PyTorch memory optimization
        if hasattr(torch.cuda, "memory_stats"):
            stats = torch.cuda.memory_stats()
            print(
                f"🔧 CUDA memory stats: allocated {stats.get('allocated_bytes.all.current', 0) / 1e9:.2f}GB, "
                f"reserved {stats.get('reserved_bytes.all.current', 0) / 1e9:.2f}GB"
            )

        dataloader = DataLoader(
            dataset=ListDataset[str](images),
            batch_size=batch_size,
            shuffle=False,
            num_workers=0,  # Set to 0 to avoid multiprocessing memory issues
            pin_memory=False,  # Disable pin_memory to reduce CPU memory pressure
            collate_fn=lambda x: self.processor.process_images(x),
        )

        ds: List[torch.Tensor] = []

        for batch_idx, batch_doc in enumerate(tqdm(dataloader)):
            retry_count = 0
            processed = False

            while not processed and retry_count < max_retries:
                try:
                    with torch.no_grad():
                        batch_doc = {
                            k: v.to(self.model.device) for k, v in batch_doc.items()
                        }
                        embeddings_doc = self.model(**batch_doc)
                    ds.extend(list(torch.unbind(embeddings_doc.to("cpu"))))
                    processed = True

                    # Clear GPU cache between batches to prevent OOM
                    if hasattr(torch.cuda, "empty_cache"):
                        torch.cuda.empty_cache()

                    # Log memory every batch
                    if hasattr(torch.cuda, "memory_allocated"):
                        allocated = torch.cuda.memory_allocated() / 1e9
                        reserved = torch.cuda.memory_reserved() / 1e9
                        print(
                            f"🔧 Batch {batch_idx}: GPU memory {allocated:.2f}GB allocated, {reserved:.2f}GB reserved"
                        )

                except torch.OutOfMemoryError as oom:
                    retry_count += 1
                    print(
                        f"⚠️ OOM error on batch {batch_idx}, retry {retry_count}/{max_retries}"
                    )

                    # Clear all caches
                    if hasattr(torch.cuda, "empty_cache"):
                        torch.cuda.empty_cache()

                    # Reduce memory usage
                    import gc

                    gc.collect()

                    if hasattr(torch.cuda, "memory_allocated"):
                        torch.cuda.reset_peak_memory_stats()

                    if retry_count == max_retries:
                        print(
                            f"❌ Failed to process batch {batch_idx} after {max_retries} retries"
                        )
                        # Try to process single image instead of batch
                        if batch_size > 1:
                            print(f"⚠️ Reducing batch size from {batch_size} to 1")
                            # This would require reconfiguring dataloader, but batch_size is already 1
                        raise oom

                    # Wait before retry (exponential backoff)
                    import time

                    wait_time = 2**retry_count  # 2, 4, 8 seconds
                    print(f"⏳ Waiting {wait_time}s before retry...")
                    time.sleep(wait_time)

            # If still not processed after retries, raise error
            if not processed:
                raise RuntimeError(
                    f"Failed to process batch {batch_idx} after {max_retries} retries"
                )

        # Convert to list of lists
        result = []
        for i in range(len(ds)):
            result.append(ds[i].float().tolist())

        # Final memory cleanup
        if hasattr(torch.cuda, "empty_cache"):
            torch.cuda.empty_cache()

        print(f"✅ Successfully processed {len(images)} images")
        return result


colbert = ColBERTService(settings.colbert_model_path)

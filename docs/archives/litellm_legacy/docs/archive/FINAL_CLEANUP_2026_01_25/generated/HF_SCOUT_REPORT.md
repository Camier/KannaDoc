# HF model scout report

Generated from official Hugging Face Hub metadata (JSON API).

- Generated: `2026-01-17T18:36:07Z`
- Sort: `trendingScore` (direction `-1`)
- Limit per tag: `12`

## Notes

- `providers` comes from `expand=inferenceProviderMapping` (HF Inference Providers availability).
- Image/audio/video/3D models should typically be wired in a dedicated media gateway (not in LiteLLM chat model_list).

## `text-generation`

| model_id | likes | downloads | storage | gated | providers | tasks | hf-inference? | local? |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| openbmb/AgentCPM-Explore | 321 | 1406 | 8.2 GB | n | - | - | n | n |
| zai-org/GLM-4.7 | 1667 | 66994 | 667.5 GB | n | cerebras,novita,zai-org | conversational | n | n |
| LiquidAI/LFM2.5-1.2B-Instruct | 355 | 45860 | 2.2 GB | n | - | - | n | y |
| MiniMaxAI/MiniMax-M2.1 | 1085 | 231427 | 214.3 GB | n | nebius,novita | conversational | n | n |
| NousResearch/NousCoder-14B | 154 | 1540 | 27.5 GB | n | - | - | n | n |
| FutureMa/Eva-4B | 77 | 197 | 22.5 GB | n | - | - | n | n |
| miromind-ai/MiroThinker-v1.5-30B | 212 | 4557 | 56.9 GB | n | - | - | n | n |
| LiquidAI/LFM2.5-1.2B-JP | 129 | 4651 | 6.5 GB | n | - | - | n | y |
| LiquidAI/LFM2-2.6B-Transcript | 145 | 666 | 4.8 GB | n | - | - | n | y |
| meituan-longcat/LongCat-Flash-Thinking-2601 | 61 | 106 | 1.0 TB | n | - | - | n | n |
| baichuan-inc/Baichuan-M3-235B | 60 | 825 | 439.1 GB | n | - | - | n | n |
| naver-hyperclovax/HyperCLOVAX-SEED-Think-32B | 388 | 31809 | 62.1 GB | n | - | - | n | n |


## `feature-extraction`

| model_id | likes | downloads | storage | gated | providers | tasks | hf-inference? | local? |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ekwek/Soprano-Encoder | 18 | 7 | 108.7 MB | n | - | - | n | y |
| Qwen/Qwen3-Embedding-8B | 535 | 1589540 | 56.4 GB | n | nebius,novita,scaleway | feature-extraction | n | n |
| Qwen/Qwen3-Embedding-0.6B | 826 | 2352466 | 5.6 GB | n | hf-inference | feature-extraction | y | y |
| Qwen/Qwen3-Embedding-4B | 208 | 433955 | 33.8 GB | n | - | - | n | n |
| nvidia/llama-embed-nemotron-8b | 121 | 469692 | 14.0 GB | n | - | - | n | n |
| nvidia/llama-nemotron-embed-vl-1b-v2 | 17 | 15004 | 3.1 GB | n | - | - | n | y |
| intfloat/multilingual-e5-large | 1119 | 2988350 | 9.4 GB | n | hf-inference | feature-extraction | y | n |
| mixedbread-ai/mxbai-embed-large-v1 | 754 | 1573636 | 5.0 GB | n | hf-inference | feature-extraction | y | y |
| intfloat/multilingual-e5-large-instruct | 600 | 1273873 | 8.3 GB | n | hf-inference | feature-extraction | y | n |
| nvidia/llama-nemotron-embed-1b-v2 | 32 | 22010 | 4.6 GB | n | - | - | n | y |
| Xenova/all-MiniLM-L6-v2 | 97 | 776414 | 349.5 MB | n | - | - | n | y |
| BAAI/bge-small-en-v1.5 | 397 | 3177967 | 795.9 MB | n | hf-inference | feature-extraction | y | y |


## `text-to-image`

| model_id | likes | downloads | storage | gated | providers | tasks | hf-inference? | local? |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| zai-org/GLM-Image | 787 | 6001 | 33.3 GB | n | fal-ai,zai-org | text-to-image | n | n |
| Tongyi-MAI/Z-Image-Turbo | 3808 | 416622 | 49.8 GB | n | fal-ai,replicate,wavespeed | text-to-image | n | n |
| Phr00t/Qwen-Image-Edit-Rapid-AIO | 1385 | 0 | 1.3 TB | n | - | - | n | n |
| Qwen/Qwen-Image-2512 | 603 | 46284 | 53.7 GB | n | fal-ai,replicate | text-to-image | n | n |
| black-forest-labs/FLUX.1-dev | 12162 | 723832 | 63.7 GB | n | fal-ai,hf-inference,nebius,replicate,together,wavespeed | text-to-image | y | n |
| stabilityai/stable-diffusion-xl-base-1.0 | 7326 | 1841600 | 72.1 GB | n | fal-ai,hf-inference,nscale,replicate,together | text-to-image | y | n |
| fal/FLUX.2-dev-Turbo | 289 | 11391 | 5.2 GB | n | fal-ai | text-to-image | n | y |
| unsloth/Qwen-Image-2512-GGUF | 267 | 117809 | 275.0 GB | n | fal-ai | text-to-image | n | y |
| lodestones/Zeta-Chroma | 88 | 0 | 145.2 GB | n | - | - | n | n |
| zooeyy/Qwen-Edit-2511_LightingRemap_Alpha0.2 | 17 | 234 | 571.0 MB | n | - | - | n | y |
| black-forest-labs/FLUX.1-schnell | 4538 | 623032 | 54.1 GB | n | fal-ai,hf-inference,nebius,nscale,replicate,together,wavespeed | text-to-image | y | n |
| lightx2v/Qwen-Image-2512-Lightning | 166 | 74650 | 100.1 GB | n | - | - | n | n |


## `image-to-image`

| model_id | likes | downloads | storage | gated | providers | tasks | hf-inference? | local? |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| fal/Qwen-Image-Edit-2511-Multiple-Angles-LoRA | 724 | 51009 | 318.9 MB | n | fal-ai | image-to-image | n | y |
| black-forest-labs/FLUX.2-klein-4B | 159 | 10003 | 22.1 GB | n | fal-ai,replicate | image-to-image | n | n |
| black-forest-labs/FLUX.2-klein-9B | 153 | 8531 | 49.3 GB | n | - | - | n | n |
| dx8152/Qwen-Image-Edit-2511-Gaussian-Splash | 98 | 0 | 287.2 MB | n | fal-ai | image-to-image | n | y |
| black-forest-labs/FLUX.2-klein-base-9B | 96 | 3489 | 49.3 GB | n | fal-ai,replicate | image-to-image | n | n |
| Qwen/Qwen-Image-Edit-2511 | 717 | 98280 | 53.7 GB | n | fal-ai,replicate | image-to-image | n | n |
| prithivMLmods/Qwen-Image-Edit-2511-Unblur-Upscale | 53 | 4225 | 1.1 GB | n | fal-ai | image-to-image | n | y |
| black-forest-labs/FLUX.2-klein-base-4B | 51 | 2812 | 22.1 GB | n | fal-ai,replicate | image-to-image | n | n |
| lilylilith/AnyPose | 380 | 34275 | 562.9 MB | n | fal-ai | image-to-image | n | y |
| black-forest-labs/FLUX.2-dev | 1239 | 94335 | 165.4 GB | n | fal-ai,replicate,wavespeed | image-to-image | n | n |
| black-forest-labs/FLUX.2-klein-9b-fp8 | 30 | 5695 | 8.8 GB | n | - | - | n | n |
| unsloth/FLUX.2-klein-4B-GGUF | 30 | 6044 | 48.3 GB | n | - | - | n | y |


## `image-text-to-image`

| model_id | likes | downloads | storage | gated | providers | tasks | hf-inference? | local? |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Qwen/Qwen-Image-Layered | 951 | 27158 | 53.8 GB | n | fal-ai | image-text-to-image | n | n |
| Arunk25/Qwen-Image-Edit-Rapid-AIO-GGUF | 106 | 65834 | 1.1 TB | n | - | - | n | y |
| unsloth/Qwen-Image-Layered-GGUF | 37 | 8289 | 349.2 GB | n | - | - | n | y |
| QuantStack/Qwen-Image-Layered-GGUF | 56 | 12772 | 161.6 GB | n | - | - | n | y |
| alb3530/Flux.2-dev-FALAI-Turbo-Merged-GGUF | 2 | 0 | 32.1 GB | n | - | - | n | y |
| BAAI/Emu3.5-Image | 66 | 232 | 63.5 GB | n | - | - | n | n |
| alexeisenach/SD3.5-Med-LoRA-Lineart | 0 | 0 | 86.7 MB | n | - | - | n | y |
| kushaaagr/controlnet-color-guider | 0 | 6 | 694.8 MB | n | - | - | n | y |
| Yooghrn/Mrtbk3 | 0 | 0 | 0 B | n | - | - | n | n |
| Runware/Qwen-Image-Layered | 0 | 152 | 53.7 GB | n | - | - | n | n |
| T5B/Qwen-Image-Layered-FP8 | 2 | 3289 | 38.1 GB | n | - | - | n | n |
| vantagewithai/Qwen-Image-Layered-GGUF | 1 | 771 | 146.7 GB | n | - | - | n | y |


## `text-to-speech`

| model_id | likes | downloads | storage | gated | providers | tasks | hf-inference? | local? |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Supertone/supertonic-2 | 276 | 11904 | 251.4 MB | n | - | - | n | y |
| ekwek/Soprano-1.1-80M | 66 | 2181 | 267.9 MB | n | - | - | n | y |
| FunAudioLLM/Fun-CosyVoice3-0.5B-2512 | 395 | 4362 | 10.1 GB | n | - | - | n | n |
| hexgrad/Kokoro-82M | 5577 | 1949673 | 1.1 GB | n | fal-ai,replicate | text-to-speech | n | y |
| ekwek/Soprano-80M | 303 | 8547 | 207.3 MB | n | - | - | n | y |
| coqui/XTTS-v2 | 3319 | 5334201 | 22.7 GB | n | - | - | n | n |
| neuphonic/neutts-nano | 23 | 691 | 689.9 MB | n | - | - | n | y |
| zai-org/GLM-TTS | 298 | 729 | 8.3 GB | n | - | - | n | n |
| ResembleAI/chatterbox-turbo | 563 | 0 | 3.8 GB | n | - | - | n | y |
| nvidia/magpie_tts_multilingual_357m | 57 | 842 | 2.3 GB | n | - | - | n | y |
| ResembleAI/chatterbox | 1422 | 515153 | 14.1 GB | n | fal-ai | text-to-speech | n | n |
| fishaudio/openaudio-s1-mini | 554 | 4150 | 3.4 GB | n | - | - | n | y |


## `automatic-speech-recognition`

| model_id | likes | downloads | storage | gated | providers | tasks | hf-inference? | local? |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| nvidia/nemotron-speech-streaming-en-0.6b | 393 | 5778 | 4.6 GB | n | - | - | n | y |
| google/medasr | 243 | 7465 | 1.0 GB | n | - | - | n | y |
| nvidia/parakeet-tdt-0.6b-v3 | 554 | 72139 | 9.3 GB | n | - | - | n | n |
| openai/whisper-large-v3 | 5314 | 6868311 | 29.5 GB | n | fal-ai,hf-inference,replicate,sambanova | automatic-speech-recognition | y | n |
| pyannote/speaker-diarization-3.1 | 1443 | 13851360 | 0 B | n | - | - | n | n |
| ggerganov/whisper.cpp | 1261 | 0 | 31.0 GB | n | - | - | n | n |
| zai-org/GLM-ASR-Nano-2512 | 325 | 189428 | 8.4 GB | n | - | - | n | n |
| pyannote/speaker-diarization | 1220 | 504489 | 0 B | n | - | - | n | n |
| openai/whisper-large-v3-turbo | 2770 | 2783468 | 4.7 GB | n | hf-inference | automatic-speech-recognition | y | y |
| pyannote/speaker-diarization-community-1 | 148 | 505514 | 32.1 MB | n | - | - | n | y |
| nvidia/canary-qwen-2.5b | 349 | 81456 | 14.3 GB | n | - | - | n | n |
| microsoft/Phi-4-multimodal-instruct | 1559 | 160831 | 22.4 GB | n | replicate | automatic-speech-recognition | n | n |


## `text-to-audio`

| model_id | likes | downloads | storage | gated | providers | tasks | hf-inference? | local? |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| HeartMuLa/HeartMuLa-oss-3B | 15 | 80 | 14.7 GB | n | - | - | n | n |
| ACE-Step/ACE-Step-v1-3.5B | 672 | 0 | 7.7 GB | n | - | - | n | y |
| stabilityai/stable-audio-open-1.0 | 1385 | 23755 | 14.6 GB | n | - | - | n | n |
| FabioSarracino/VibeVoice-Large-Q8 | 76 | 2753 | 10.8 GB | n | - | - | n | n |
| tencent/SongGeneration | 295 | 424 | 32.8 GB | n | - | - | n | n |
| facebook/musicgen-small | 470 | 83775 | 9.8 GB | n | - | - | n | n |
| facebook/musicgen-large | 513 | 4436 | 53.9 GB | n | - | - | n | n |
| stabilityai/stable-audio-open-small | 242 | 2037 | 4.7 GB | n | - | - | n | y |
| Xenova/musicgen-small | 51 | 2181 | 30.0 GB | n | - | - | n | n |
| 2Noise/ChatTTS | 1630 | 1005 | 2.2 GB | n | - | - | n | y |
| calcuis/ace-gguf | 24 | 2834 | 181.1 GB | n | - | - | n | y |
| facebook/musicgen-stereo-large | 87 | 522 | 31.9 GB | n | - | - | n | n |


## `text-to-video`

| model_id | likes | downloads | storage | gated | providers | tasks | hf-inference? | local? |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| tencent/HunyuanVideo-1.5 | 682 | 516375 | 346.2 GB | n | fal-ai,wavespeed | text-to-video | n | n |
| Lightricks/LTX-2-19b-IC-LoRA-Pose-Control | 16 | 0 | 624.1 MB | n | - | - | n | y |
| GitMylo/Wan_2.2_nvfp4 | 10 | 0 | 19.6 GB | n | - | - | n | n |
| Lightricks/LTX-2-19b-IC-LoRA-Depth-Control | 15 | 0 | 624.1 MB | n | - | - | n | y |
| calcuis/wan-gguf | 170 | 9859 | 1.2 TB | n | - | - | n | y |
| QuantStack/Wan2.2-T2V-A14B-GGUF | 209 | 169203 | 232.8 GB | n | - | - | n | y |
| meituan-longcat/LongCat-Video | 411 | 2113 | 77.6 GB | n | fal-ai | text-to-video | n | n |
| Lightricks/LTX-2-19b-LoRA-Camera-Control-Dolly-In | 9 | 0 | 312.1 MB | n | fal-ai | text-to-video | n | y |
| oumoumad/deepzoom-lora | 6 | 0 | 3.2 GB | n | fal-ai | text-to-video | n | y |
| Lightricks/LTX-2-19b-LoRA-Camera-Control-Static | 8 | 0 | 2.1 GB | n | fal-ai | text-to-video | n | y |
| Wan-AI/Wan2.1-T2V-1.3B | 421 | 9484 | 43.3 GB | n | fal-ai,replicate,wavespeed | text-to-video | n | n |
| Wan-AI/Wan2.2-TI2V-5B | 487 | 4538 | 50.5 GB | n | fal-ai,replicate,wavespeed | text-to-video | n | n |


## `image-to-video`

| model_id | likes | downloads | storage | gated | providers | tasks | hf-inference? | local? |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Lightricks/LTX-2 | 1116 | 1463289 | 424.0 GB | n | fal-ai,wavespeed | image-to-video | n | n |
| unsloth/LTX-2-GGUF | 54 | 13192 | 325.3 GB | n | - | - | n | y |
| QuantStack/LTX-2-GGUF | 62 | 16463 | 112.2 GB | n | - | - | n | y |
| Phr00t/WAN2.2-14B-Rapid-AllInOne | 1349 | 0 | 1.2 TB | n | - | - | n | n |
| Soul-AILab/SoulX-FlashTalk-14B | 21 | 2385 | 50.7 GB | n | - | - | n | n |
| kabachuha/ltx2-hydraulic-press | 17 | 28 | 621.2 MB | n | - | - | n | y |
| Wan-AI/Wan2.2-I2V-A14B | 579 | 10805 | 117.5 GB | n | fal-ai,wavespeed | image-to-video | n | n |
| vantagewithai/LTX-2-GGUF | 20 | 8784 | 298.4 GB | n | - | - | n | y |
| kabachuha/ltx2-inflate-it | 11 | 69 | 1.1 GB | n | - | - | n | y |
| kabachuha/ltx2-cakeify | 9 | 68 | 818.7 MB | n | - | - | n | y |
| kabachuha/ltx2-eat | 7 | 81 | 1.1 GB | n | - | - | n | y |
| tencent/HY-WorldPlay | 436 | 2298 | 144.4 GB | n | - | - | n | n |


## `image-to-3d`

| model_id | likes | downloads | storage | gated | providers | tasks | hf-inference? | local? |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| tencent/Hunyuan3D-2.1 | 818 | 19917 | 13.9 GB | n | - | - | n | n |
| microsoft/TRELLIS.2-4B | 545 | 0 | 15.1 GB | n | - | - | n | n |
| apple/Sharp | 329 | 6427 | 2.6 GB | n | - | - | n | y |
| infinith/UltraShape | 79 | 0 | 6.9 GB | n | - | - | n | y |
| IntimeAI/Miro | 6 | 0 | 6.9 GB | n | - | - | n | y |
| tencent/Hunyuan3D-2 | 1695 | 63559 | 57.9 GB | n | - | - | n | n |
| tencent/Hunyuan3D-Omni | 148 | 788 | 24.0 GB | n | - | - | n | n |
| stabilityai/TripoSR | 582 | 28138 | 4.9 GB | n | - | - | n | y |
| facebook/map-anything | 71 | 20166 | 6.7 GB | n | - | - | n | y |
| naver/DUSt3R_ViTLarge_BaseDecoder_512_dpt | 17 | 8263 | 2.1 GB | n | - | - | n | y |
| microsoft/TRELLIS-image-large | 611 | 2592844 | 3.1 GB | n | - | - | n | y |
| stabilityai/stable-point-aware-3d | 326 | 677 | 6.8 GB | n | - | - | n | y |



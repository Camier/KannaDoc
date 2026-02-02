ALL_FLAT is the single source of truth for PDFs (see `data/manifests/pdf_analysis_summary.csv` for current counts).
- Always activate the conda env before doing anything here: `conda activate kanna2` (env path: /home/miko/mambaforge/envs/kanna2).
- Former collections BIBLIOGRAPHIE and MASTER_BIBLIOGRAPHY were emptied to avoid duplicate storage.
- Add any new papers here, then regenerate manifest with `python3 create_manifest.py`.
  - Flags: `--no-text` to skip text extraction; `--no-page-rows` to skip per-page outputs; `--no-parquet` to skip `pdf_pages.parquet`.
  - Tuning: `--native-char-threshold N` adjusts native vs OCR text-layer classification.
- Helper files now live in `data/manifests/` (keeps this folder clean). A symlink to `rename_history.csv` is left here for convenience.
  - `pdf_index.csv`, `pdf_index_enriched.csv`, `pdf_index_enriched.xml`, `pdf_pages.csv`, `pdf_pages.parquet`, `pdf_text_stats.csv`, `pdf_analysis_summary.csv` → `data/manifests/`
  - `rename_history.csv` → symlink to `data/manifests/rename_history.csv`

Manifest schema (high level):
- `pdf_index.csv`: per-PDF row with size, sha256, page_count, text layer stats, text_origin, and OCR status.
- `pdf_index_enriched.csv`: `pdf_index.csv` + bibliographic fields + PDF metadata.
- `pdf_pages.csv`: per-page rows (page_num, page_id, text_chars, text_sha256, has_text, text_error).
- `pdf_pages.parquet`: same as `pdf_pages.csv` in Parquet format (if pyarrow available).
- `pdf_text_stats.csv`: per-PDF text distribution stats (min/p10/median/p90/max), coverage, and origin.

#!/bin/bash
cd /LAB/@thesis/layra
export CORPUS_DIR=/LAB/@thesis/layra/literature/corpus
export INGEST_BATCH_SIZE=1
export INGEST_BATCH_PAUSE=0.5
export LAYRA_API_BASE=http://localhost:8090/api
# SECURITY: Set credentials via environment before running
# export THESIS_USERNAME=your_username
# export THESIS_PASSWORD=your_password
export KB_NAME="Thesis Corpus Optimized"

echo "Starting full corpus ingestion at $(date)" >> /tmp/ingestion.log
python scripts/ingest_corpus.py >> /tmp/ingestion.log 2>&1
echo "Ingestion completed at $(date)" >> /tmp/ingestion.log
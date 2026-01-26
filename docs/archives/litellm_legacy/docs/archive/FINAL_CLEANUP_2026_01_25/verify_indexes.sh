#!/bin/bash
# ============================================================================
# LiteLLM Database Index Verification Script
# ============================================================================
# Purpose: Monitor index usage and scan ratios after performance migration
# Usage: ./verify_indexes.sh
# ============================================================================

set -euo pipefail

DB_URL="postgresql://miko:litellm@127.0.0.1:5434/litellm_db"

echo "============================================================================"
echo "LiteLLM Database Index Verification"
echo "============================================================================"
echo "Database: $DB_URL"
echo "Timestamp: $(date '+%Y-%m-%d %H:%M:%S')"
echo ""

# 1. Check if all indexes exist
echo "1. Index Creation Status"
echo "============================================================================"
psql "$DB_URL" -c "
SELECT
    relname::text as table_name,
    indexrelname::text as index_name,
    pg_size_pretty(pg_relation_size(indexrelid)) as size,
    indisunique as is_unique,
    indisvalid as is_valid
FROM pg_stat_user_indexes
WHERE indexrelname LIKE 'idx_%'
ORDER BY relname, indexrelname;
"

echo ""
echo "2. Index Usage Statistics"
echo "============================================================================"
psql "$DB_URL" -c "
SELECT
    relname::text as table_name,
    indexrelname::text as index_name,
    idx_scan as scans,
    idx_tup_read as tuples_read,
    idx_tup_fetch as tuples_fetched
FROM pg_stat_user_indexes
WHERE indexrelname LIKE 'idx_%'
ORDER BY idx_scan DESC
LIMIT 15;
"

echo ""
echo "3. Sequential vs Index Scan Ratios (Problem Tables)"
echo "============================================================================"
psql "$DB_URL" -c "
SELECT
    relname::text as table_name,
    seq_scan as sequential_scans,
    idx_scan as index_scans,
    (seq_scan + idx_scan) as total_scans,
    CASE
        WHEN (seq_scan + idx_scan) > 0
        THEN ROUND(100.0 * idx_scan / NULLIF(seq_scan + idx_scan, 0), 2)
        ELSE 0
    END as index_scan_percent
FROM pg_stat_user_tables
WHERE relname IN (
    'LiteLLM_CredentialsTable',
    'LiteLLM_MCPServerTable',
    'LiteLLM_GuardrailsTable',
    'LiteLLM_PromptTable',
    'LiteLLM_BudgetTable'
)
ORDER BY relname;
"

echo ""
echo "4. Unused Indexes (May indicate missing queries)"
echo "============================================================================"
psql "$DB_URL" -c "
SELECT
    relname::text as table_name,
    indexrelname::text as index_name,
    pg_size_pretty(pg_relation_size(indexrelid)) as size,
    idx_scan as scans
FROM pg_stat_user_indexes
WHERE indexrelname LIKE 'idx_%'
  AND idx_scan = 0
ORDER BY pg_relation_size(indexrelid) DESC;
"

echo ""
echo "5. Most Used Indexes"
echo "============================================================================"
psql "$DB_URL" -c "
SELECT
    relname::text as table_name,
    indexrelname::text as index_name,
    idx_scan as scans,
    idx_tup_read as tuples_read,
    pg_size_pretty(pg_relation_size(indexrelid)) as size
FROM pg_stat_user_indexes
WHERE idx_scan > 0
ORDER BY idx_scan DESC
LIMIT 10;
"

echo ""
echo "6. Index Size Summary"
echo "============================================================================"
psql "$DB_URL" -c "
SELECT
    pg_size_pretty(SUM(pg_relation_size(indexrelid))) as total_index_size,
    COUNT(*) as index_count
FROM pg_stat_user_indexes
WHERE indexrelname LIKE 'idx_%';
"

echo ""
echo "============================================================================"
echo "Verification Complete"
echo "============================================================================"
echo "Run this script periodically to monitor index usage patterns."
echo "Expected: Index scans should increase as the application runs queries."
echo ""

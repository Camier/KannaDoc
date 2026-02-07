"use client";
import { apiClient as api } from "./apiClient";

/**
 * Evaluation API Client
 * 
 * Provides functions to interact with the evaluation endpoints:
 * - Run evaluations on datasets
 * - Retrieve evaluation results and metrics
 * - List datasets and evaluation runs
 */

// ============================================================
// Response Types
// ============================================================

export interface MetricsResponse {
  queries_total: number;
  queries_processed: number;
  queries_failed: number;
  queries_with_labels: number;
  mrr: number;
  ndcg: number;
  precision: number;
  recall: number;
  p95_latency_ms?: number;
}

export interface QueryResult {
  query_text: string;
  status: "success" | "failed";
  retrieved_docs?: Array<{
    doc_id: string;
    file_id?: string;
    image_id?: string;
    page_number?: number;
    score: number;
  }>;
  ground_truth_count?: number;
  relevant_retrieved?: number;
  metrics?: {
    mrr: number;
    ndcg: number;
    precision: number;
    recall: number;
  };
  error?: string;
}

export interface EvalRunResponse {
  id: string;
  dataset_id: string;
  config: {
    top_k?: number;
    score_threshold?: number;
    [key: string]: any;
  };
  metrics: MetricsResponse;
  created_at: string;
  results?: QueryResult[];
}

export interface DatasetResponse {
  id: string;
  name: string;
  kb_id: string;
  query_count: number;
  created_at: string;
  queries?: Array<{
    query_text: string;
    relevant_docs: any[];
  }>;
}

export interface EvalRunListResponse {
  runs: EvalRunResponse[];
}

export interface DatasetListResponse {
  datasets: DatasetResponse[];
}

// ============================================================
// API Functions
// ============================================================

/**
 * Run an evaluation on a dataset
 * 
 * @param datasetId - Dataset ID to evaluate
 * @param config - Optional configuration (top_k, score_threshold, etc.)
 * @returns Evaluation run with aggregated metrics
 */
export const runEvaluation = async (
  datasetId: string,
  config?: { top_k?: number; score_threshold?: number }
): Promise<EvalRunResponse> => {
  const response = await api.post("/eval/run", {
    dataset_id: datasetId,
    config: config || {},
  });
  return response.data;
};

/**
 * Get evaluation run results by ID
 * 
 * @param runId - Evaluation run ID
 * @returns Evaluation run with per-query results and metrics
 */
export const getEvalRun = async (runId: string): Promise<EvalRunResponse> => {
  const response = await api.get(`/eval/runs/${runId}`);
  return response.data;
};

/**
 * List all datasets for a knowledge base
 * 
 * @param kbId - Knowledge base ID
 * @returns List of datasets
 */
export const listDatasets = async (kbId: string): Promise<DatasetListResponse> => {
  const response = await api.get(`/eval/datasets?kb_id=${kbId}`);
  return response.data;
};

/**
 * List all evaluation runs for a dataset
 * 
 * @param datasetId - Dataset ID
 * @returns List of evaluation runs (newest first)
 */
export const listEvalRuns = async (datasetId: string): Promise<EvalRunListResponse> => {
  const response = await api.get(`/eval/runs?dataset_id=${datasetId}`);
  return response.data;
};

/**
 * Get full dataset details including queries
 * 
 * @param datasetId - Dataset ID
 * @returns Dataset with all queries and relevant documents
 */
export const getDataset = async (datasetId: string): Promise<DatasetResponse> => {
  const response = await api.get(`/eval/datasets/${datasetId}`);
  return response.data;
};

/**
 * Create a new evaluation dataset
 * 
 * @param name - Dataset name (must be unique per KB)
 * @param kbId - Knowledge base ID
 * @param queryCount - Number of queries to generate (1-500)
 * @param labelWithLlm - Use LLM to label relevance scores
 * @returns Created dataset with metadata
 */
export const createDataset = async (
  name: string,
  kbId: string,
  queryCount: number,
  labelWithLlm: boolean = false
): Promise<DatasetResponse> => {
  const response = await api.post("/eval/datasets", {
    name,
    kb_id: kbId,
    query_count: queryCount,
    label_with_llm: labelWithLlm,
  });
  return response.data;
};

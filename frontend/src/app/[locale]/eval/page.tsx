'use client';

import { useState } from 'react';
import { MetricCard, Button, Card, CardHeader, CardTitle, CardContent } from '@/components/ui';
import { runEvaluation as runEvalAPI, type EvalRunResponse } from '@/lib/api/evalApi';

export default function EvalPage() {
  const [evalData, setEvalData] = useState<EvalRunResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  const runEvaluation = async () => {
    setLoading(true);
    setError(null);
    
    try {
      const result = await runEvalAPI('dataset-dev', { top_k: 5 });
      setEvalData(result);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to run evaluation';
      setError(errorMessage);
      console.error('Evaluation failed:', err);
    } finally {
      setLoading(false);
    }
  };
  
  if (error) {
    return (
      <main className="pharmacopeia-bg min-h-screen p-8">
        <div className="max-w-6xl mx-auto">
          <div className="flex justify-between items-center mb-8">
            <div>
              <h1 className="font-display text-4xl text-parchment-100">
                Retrieval Evaluation
              </h1>
              <p className="mt-2 text-parchment-400 font-serif">
                Measure RAG performance with IR metrics
              </p>
            </div>
            <Button onClick={runEvaluation} loading={loading}>
              Run Evaluation
            </Button>
          </div>
          <Card variant="glass" className="border-red-500/20">
            <CardContent className="py-8">
              <p className="text-red-400 text-center">
                Error: {error}
              </p>
            </CardContent>
          </Card>
        </div>
      </main>
    );
  }

  if (!evalData) {
    return (
      <main className="pharmacopeia-bg min-h-screen p-8">
        <div className="max-w-6xl mx-auto">
          <div className="flex justify-between items-center mb-8">
            <div>
              <h1 className="font-display text-4xl text-parchment-100">
                Retrieval Evaluation
              </h1>
              <p className="mt-2 text-parchment-400 font-serif">
                Measure RAG performance with IR metrics
              </p>
            </div>
            <Button onClick={runEvaluation} loading={loading}>
              Run Evaluation
            </Button>
          </div>
          <Card variant="glass">
            <CardContent className="py-12">
              <p className="text-parchment-400 text-center">
                No evaluation results yet. Click "Run Evaluation" to start.
              </p>
            </CardContent>
          </Card>
        </div>
      </main>
    );
  }

  const metrics = evalData.metrics;
  const p95Latency = metrics.p95_latency_ms || 0;

  return (
    <main className="pharmacopeia-bg min-h-screen p-8">
      <div className="max-w-6xl mx-auto">
        <div className="flex justify-between items-center mb-8">
          <div>
            <h1 className="font-display text-4xl text-parchment-100">
              Retrieval Evaluation
            </h1>
            <p className="mt-2 text-parchment-400 font-serif">
              Measure RAG performance with IR metrics
            </p>
          </div>
          <Button onClick={runEvaluation} loading={loading}>
            Run Evaluation
          </Button>
        </div>
        
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
          <MetricCard 
            label="MRR" 
            value={metrics.mrr.toFixed(3)} 
            trend="neutral" 
            trendValue=""
          />
          <MetricCard 
            label="NDCG@K" 
            value={metrics.ndcg.toFixed(3)} 
            trend="neutral"
            trendValue=""
          />
          <MetricCard 
            label="Precision@K" 
            value={metrics.precision.toFixed(3)} 
            trend="neutral"
            trendValue=""
          />
          <MetricCard 
            label="Recall@K" 
            value={metrics.recall.toFixed(3)} 
            trend="neutral"
            trendValue=""
          />
        </div>
        
        <Card variant="glass" className="mb-8">
          <CardHeader>
            <CardTitle>Query Statistics</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
              <div>
                <p className="text-sm text-parchment-400">Total Queries</p>
                <p className="text-2xl font-mono text-parchment-100">{metrics.queries_total}</p>
              </div>
              <div>
                <p className="text-sm text-parchment-400">Processed</p>
                <p className="text-2xl font-mono text-forest-400">{metrics.queries_processed}</p>
              </div>
              <div>
                <p className="text-sm text-parchment-400">Failed</p>
                <p className="text-2xl font-mono text-red-400">{metrics.queries_failed}</p>
              </div>
              <div>
                <p className="text-sm text-parchment-400">With Labels</p>
                <p className="text-2xl font-mono text-parchment-100">{metrics.queries_with_labels}</p>
              </div>
            </div>
            <div className="space-y-4">
              <div>
                <div className="flex justify-between text-sm text-parchment-400 mb-1">
                  <span>p95 Latency</span>
                  <span className="font-mono">{p95Latency.toFixed(2)}ms</span>
                </div>
                <div className="h-2 bg-parchment-900 rounded-full overflow-hidden">
                  <div 
                    className="h-full bg-amber-500 rounded-full transition-all"
                    style={{ width: `${Math.min((p95Latency / 2000) * 100, 100)}%` }}
                  />
                </div>
              </div>
              <p className="text-xs text-parchment-500 mt-2">Target: ≤2000ms for p95</p>
            </div>
          </CardContent>
        </Card>
      </div>
    </main>
  );
}

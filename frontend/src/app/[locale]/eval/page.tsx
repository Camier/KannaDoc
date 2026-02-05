'use client';

import { useState } from 'react';
import { MetricCard, Button, Card, CardHeader, CardTitle, CardContent } from '@/components/ui';

// Mock data for initial display
const mockMetrics = {
  mrr: 0.72,
  ndcg: 0.68,
  precision: 0.85,
  recall: 0.61,
  latency: { p50: 245, p95: 892, p99: 1450 }
};

export default function EvalPage() {
  const [metrics, setMetrics] = useState(mockMetrics);
  const [loading, setLoading] = useState(false);
  
  const runEvaluation = async () => {
    setLoading(true);
    // TODO: Call /api/v1/eval/run
    setTimeout(() => setLoading(false), 2000);
  };
  
  return (
    <main className="pharmacopeia-bg min-h-screen p-8">
      <div className="max-w-6xl mx-auto">
        {/* Header */}
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
        
        {/* Metrics Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
          <MetricCard 
            label="MRR" 
            value={metrics.mrr.toFixed(3)} 
            trend="up" 
            trendValue="+0.05"
          />
          <MetricCard 
            label="NDCG@5" 
            value={metrics.ndcg.toFixed(3)} 
            trend="up"
            trendValue="+0.03"
          />
          <MetricCard 
            label="Precision@5" 
            value={metrics.precision.toFixed(3)} 
            trend="neutral"
            trendValue="0.00"
          />
          <MetricCard 
            label="Recall@5" 
            value={metrics.recall.toFixed(3)} 
            trend="down"
            trendValue="-0.02"
          />
        </div>
        
        {/* Latency Panel */}
        <Card variant="glass" className="mb-8">
          <CardHeader>
            <CardTitle>Query Latency</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {/* p50 */}
              <div>
                <div className="flex justify-between text-sm text-parchment-400 mb-1">
                  <span>p50</span>
                  <span className="font-mono">{metrics.latency.p50}ms</span>
                </div>
                <div className="h-2 bg-parchment-900 rounded-full overflow-hidden">
                  <div 
                    className="h-full bg-forest-500 rounded-full transition-all"
                    style={{ width: `${Math.min((metrics.latency.p50 / 2000) * 100, 100)}%` }}
                  />
                </div>
              </div>
              {/* p95 */}
              <div>
                <div className="flex justify-between text-sm text-parchment-400 mb-1">
                  <span>p95</span>
                  <span className="font-mono">{metrics.latency.p95}ms</span>
                </div>
                <div className="h-2 bg-parchment-900 rounded-full overflow-hidden">
                  <div 
                    className="h-full bg-amber-500 rounded-full transition-all"
                    style={{ width: `${Math.min((metrics.latency.p95 / 2000) * 100, 100)}%` }}
                  />
                </div>
              </div>
              {/* p99 */}
              <div>
                <div className="flex justify-between text-sm text-parchment-400 mb-1">
                  <span>p99</span>
                  <span className="font-mono">{metrics.latency.p99}ms</span>
                </div>
                <div className="h-2 bg-parchment-900 rounded-full overflow-hidden">
                  <div 
                    className="h-full bg-red-500 rounded-full transition-all"
                    style={{ width: `${Math.min((metrics.latency.p99 / 2000) * 100, 100)}%` }}
                  />
                </div>
              </div>
              {/* Threshold line at 2000ms */}
              <p className="text-xs text-parchment-500 mt-2">Target: ≤2000ms for p95</p>
            </div>
          </CardContent>
        </Card>
      </div>
    </main>
  );
}

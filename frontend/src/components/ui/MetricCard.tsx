'use client';

import { HTMLAttributes } from 'react';
import { cn } from '@/lib/utils';

interface MetricCardProps extends HTMLAttributes<HTMLDivElement> {
  label: string;
  value: string | number;
  trend?: 'up' | 'down' | 'neutral';
  trendValue?: string;
}

const MetricCard = ({ className, label, value, trend, trendValue, ...props }: MetricCardProps) => {
  const trendColors = {
    up: 'text-forest-400',
    down: 'text-red-400',
    neutral: 'text-parchment-500',
  };
  
  const trendIcons = {
    up: '\u2191',
    down: '\u2193',
    neutral: '\u2192',
  };
  
  return (
    <div
      className={cn(
        'bg-parchment-900/60 border border-parchment-800 rounded-xl p-5',
        'relative overflow-hidden',
        className
      )}
      {...props}
    >
      {/* Botanical accent line */}
      <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-forest-600 via-amber-600 to-forest-600" />
      
      <p className="font-display text-sm text-parchment-400 uppercase tracking-wider">
        {label}
      </p>
      <p className="mt-2 font-mono text-4xl text-parchment-100 tabular-nums">
        {value}
      </p>
      
      {trend && trendValue && (
        <p className={cn('mt-2 text-sm font-sans', trendColors[trend])}>
          {trendIcons[trend]} {trendValue}
        </p>
      )}
    </div>
  );
};

export { MetricCard, type MetricCardProps };

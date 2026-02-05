'use client';

import { HTMLAttributes } from 'react';
import { cn } from '@/lib/utils';

type BadgeVariant = 'success' | 'warning' | 'error' | 'info';
type BadgeStyle = 'solid' | 'subtle';

interface BadgeProps extends HTMLAttributes<HTMLSpanElement> {
  variant?: BadgeVariant;
  badgeStyle?: BadgeStyle;
}

const Badge = ({ className, variant = 'info', badgeStyle = 'subtle', ...props }: BadgeProps) => {
  const colors = {
    success: badgeStyle === 'solid' 
      ? 'bg-forest-600 text-parchment-100' 
      : 'bg-forest-900/50 text-forest-400 border border-forest-700',
    warning: badgeStyle === 'solid' 
      ? 'bg-amber-600 text-parchment-100' 
      : 'bg-amber-900/50 text-amber-400 border border-amber-700',
    error: badgeStyle === 'solid' 
      ? 'bg-red-600 text-parchment-100' 
      : 'bg-red-900/50 text-red-400 border border-red-700',
    info: badgeStyle === 'solid' 
      ? 'bg-indigo-600 text-parchment-100' 
      : 'bg-indigo-900/50 text-indigo-400 border border-indigo-700',
  };
  
  return (
    <span
      className={cn(
        'inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-sans font-medium',
        colors[variant],
        className
      )}
      {...props}
    />
  );
};

export { Badge, type BadgeProps };

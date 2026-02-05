'use client';

import { HTMLAttributes, forwardRef } from 'react';
import { cn } from '@/lib/utils';

type CardVariant = 'default' | 'glass' | 'specimen';

interface CardProps extends HTMLAttributes<HTMLDivElement> {
  variant?: CardVariant;
}

const Card = forwardRef<HTMLDivElement, CardProps>(
  ({ className, variant = 'default', children, ...props }, ref) => {
    const variants = {
      default: 'bg-parchment-900/80 border border-parchment-700/50',
      glass: 'glass-card',
      specimen: 'bg-forest-950/90 border border-forest-800 shadow-specimen',
    };
    
    return (
      <div
        ref={ref}
        className={cn(
          'rounded-xl p-6 transition-all duration-300 hover:-translate-y-1',
          variants[variant],
          className
        )}
        {...props}
      >
        {children}
      </div>
    );
  }
);

Card.displayName = 'Card';

const CardHeader = ({ className, ...props }: HTMLAttributes<HTMLDivElement>) => (
  <div className={cn('mb-4', className)} {...props} />
);

const CardTitle = ({ className, ...props }: HTMLAttributes<HTMLHeadingElement>) => (
  <h3 className={cn('font-display text-2xl text-parchment-100', className)} {...props} />
);

const CardContent = ({ className, ...props }: HTMLAttributes<HTMLDivElement>) => (
  <div className={cn('text-parchment-300 font-serif', className)} {...props} />
);

export { Card, CardHeader, CardTitle, CardContent, type CardProps };

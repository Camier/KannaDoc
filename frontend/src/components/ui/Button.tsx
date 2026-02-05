'use client';

import { forwardRef, ButtonHTMLAttributes } from 'react';
import { cn } from '@/lib/utils';

type ButtonVariant = 'primary' | 'secondary' | 'ghost' | 'icon';
type ButtonSize = 'sm' | 'md' | 'lg';

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: ButtonSize;
  loading?: boolean;
}

const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = 'primary', size = 'md', loading, children, disabled, ...props }, ref) => {
    const variants = {
      primary: 'bg-forest-600 hover:bg-forest-500 text-parchment-100 hover:shadow-glow-forest',
      secondary: 'border border-parchment-400 text-parchment-200 hover:bg-parchment-900/50',
      ghost: 'text-amber-500 hover:underline underline-offset-4',
      icon: 'p-2 text-parchment-300 hover:text-parchment-100 hover:bg-parchment-800/50 rounded-full',
    };
    
    const sizes = {
      sm: 'px-3 py-1.5 text-sm',
      md: 'px-5 py-2.5 text-base',
      lg: 'px-8 py-3 text-lg',
    };
    
    return (
      <button
        ref={ref}
        disabled={disabled || loading}
        className={cn(
          'font-sans font-medium rounded-lg transition-all duration-200 disabled:opacity-50',
          variants[variant],
          variant !== 'icon' && sizes[size],
          loading && 'animate-pulse-gentle',
          className
        )}
        {...props}
      >
        {loading ? <span className="opacity-70">Loading...</span> : children}
      </button>
    );
  }
);

Button.displayName = 'Button';

export { Button, type ButtonProps };

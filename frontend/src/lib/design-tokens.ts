// Design tokens derived from Tailwind config for design-system parity
// Exports color scales, typography, spacing, animation, and shadows

// 1) Color tokens matching Tailwind color scales (and academic/ botanical variants)
export const colors = {
  forest: {
    50: '#f0fdf4',
    100: '#dcfce7',
    200: '#bbf7d0',
    300: '#86efac',
    400: '#4ade80',
    500: '#22c55e',
    600: '#16a34a',
    700: '#15803d',
    800: '#166534',
    900: '#14532d',
    950: '#0D2818',
  },
  amber: {
    50: '#fffbeb',
    100: '#fef3c7',
    200: '#fde68a',
    300: '#fcd34d',
    400: '#fbbf24',
    500: '#f59e0b',
    600: '#d97706',
    700: '#b45309',
    800: '#92400e',
    900: '#78350f',
    950: '#451a03',
  },
  parchment: {
    50: '#FDFCFB',
    100: '#FAF6F1',
    200: '#F5EDE3',
    300: '#E8DED0',
    400: '#D4C4AE',
    500: '#B8A586',
    600: '#9C8664',
    700: '#7D6A4E',
    800: '#5F4F3A',
    900: '#423728',
    950: '#2A2318',
  },
  ink: {
    50: '#f8f7f6',
    100: '#efecea',
    200: '#ddd8d3',
    300: '#c4bcb3',
    400: '#a69a8e',
    500: '#8f8173',
    600: '#7a6c5f',
    700: '#65584e',
    800: '#554a42',
    900: '#3d352f',
    950: '#1C1917',
  },
  botanical: {
    rose: '#BE185D',
    lavender: '#7C3AED',
    sage: '#059669',
    ochre: '#CA8A04',
    rust: '#DC2626',
    indigo: '#4338CA',
  },
  academic: {
    50: '#f8fafc',
    100: '#f1f5f9',
    200: '#e2e8f0',
    300: '#cbd5e1',
    400: '#94a3b8',
    500: '#64748b',
    600: '#475569',
    700: '#334155',
    800: '#1e293b',
    900: '#0f172a',
    950: '#020617',
  },
} as const;

// 2) Typography tokens
export const typography = {
  fontFamily: {
    display: 'var(--font-cormorant)',
    serif: 'var(--font-source-serif)',
    mono: 'var(--font-dm-mono)',
    sans: 'var(--font-inter)',
  },
  fontSize: {
    xs: '0.75rem',
    sm: '0.875rem',
    base: '1rem',
    lg: '1.125rem',
    xl: '1.25rem',
    '2xl': '1.5rem',
    '3xl': '1.875rem',
    '4xl': '2.25rem',
    '5xl': '3rem',
    '6xl': '3.75rem',
  },
} as const;

// 3) Spacing tokens (standalone, mirror Tailwind-like scale)
export const spacing = {
  px: '1px',
  0: '0px',
  0.5: '0.125rem',
  1: '0.25rem',
  1.5: '0.375rem',
  2: '0.5rem',
  2.5: '0.625rem',
  3: '0.75rem',
  3.5: '0.875rem',
  4: '1rem',
  5: '1.25rem',
  6: '1.5rem',
  8: '2rem',
  10: '2.5rem',
  12: '3rem',
  16: '4rem',
  20: '5rem',
  24: '6rem',
  28: '7rem',
  32: '8rem',
  36: '9rem',
  40: '10rem',
  48: '12rem',
  56: '14rem',
  64: '16rem',
  72: '18rem',
  80: '20rem',
  96: '24rem',
} as const;

// 4) Animation tokens
export const animation = {
  duration: {
    fast: '150ms',
    normal: '300ms',
    slow: '500ms',
    botanical: '2000ms',
  },
  easing: {
    default: 'ease-out',
    spring: 'cubic-bezier(0.34, 1.56, 0.64, 1)',
  },
} as const;

// 5) Shadow tokens
export const shadows = {
  botanical: '0 4px 14px 0 rgba(22, 101, 52, 0.15)',
  specimen: '0 8px 30px rgba(0, 0, 0, 0.12)',
  parchment: '0 2px 4px rgba(42, 35, 24, 0.05), 0 8px 16px rgba(42, 35, 24, 0.05)',
  glowAmber: '0 0 15px rgba(217, 119, 6, 0.3)',
  glowForest: '0 0 15px rgba(22, 163, 74, 0.3)',
} as const;

// 6) Type exports for theme typing
export type ColorScale = typeof colors.forest;
export type ThemeColors = typeof colors;
export type ThemeTypography = typeof typography;

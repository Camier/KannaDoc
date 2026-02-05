import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: "class",
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  plugins: [
    require("@tailwindcss/typography"), // 增强排版样式
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ['var(--font-inter)', 'ui-sans-serif', 'system-ui'],
        display: ['var(--font-cormorant)', 'Cormorant Garamond', 'Georgia', 'serif'],
        serif: ['var(--font-source-serif)', 'Source Serif Pro', 'Georgia', 'serif'],
        mono: ['var(--font-dm-mono)', 'DM Mono', 'JetBrains Mono', 'monospace'],
      },
      colors: {
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
          950: '#0D2818'
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
          950: '#451a03'
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
          950: '#2A2318'
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
          950: '#1C1917'
        },
        botanical: {
           rose: '#BE185D', 
           lavender: '#7C3AED', 
           sage: '#059669', 
           ochre: '#CA8A04', 
           rust: '#DC2626', 
           indigo: '#4338CA'
        }
      },
      backgroundImage: {
        'grain': "url(\"data:image/svg+xml,%3Csvg viewBox='0 0 200 200' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noiseFilter'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.65' numOctaves='3' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noiseFilter)' opacity='0.05'/%3E%3C/svg%3E\")",
        'botanical-pattern': "url(\"data:image/svg+xml,%3Csvg width='20' height='20' viewBox='0 0 20 20' xmlns='http://www.w3.org/2000/svg'%3E%3Cg fill='%23166534' fill-opacity='0.05' fill-rule='evenodd'%3E%3Ccircle cx='3' cy='3' r='3'/%3E%3Ccircle cx='13' cy='13' r='3'/%3E%3C/g%3E%3C/svg%3E\")",
        'dots': "url(\"data:image/svg+xml,%3Csvg width='20' height='20' viewBox='0 0 20 20' xmlns='http://www.w3.org/2000/svg'%3E%3Ccircle cx='2' cy='2' r='1' fill='%231C1917' fill-opacity='0.1'/%3E%3C/svg%3E\")",
      },
      boxShadow: {
        'inset-glow': 'inset 0 0 20px rgba(255, 255, 255, 0.1)',
        'botanical': '0 4px 14px 0 rgba(22, 101, 52, 0.15)',
        'specimen': '0 0 0 1px rgba(28, 25, 23, 0.05), 0 2px 8px rgba(28, 25, 23, 0.05)',
        'parchment': '0 2px 4px rgba(42, 35, 24, 0.05), 0 8px 16px rgba(42, 35, 24, 0.05)',
        'card': '0 1px 3px rgba(0,0,0,0.12), 0 1px 2px rgba(0,0,0,0.24)',
        'glow-amber': '0 0 15px rgba(217, 119, 6, 0.3)',
        'glow-forest': '0 0 15px rgba(22, 163, 74, 0.3)',
      },
      animation: {
        border: 'border 4s ease infinite',
        'fade-in': 'fadeIn 0.5s ease-out forwards',
        'fade-in-up': 'fadeInUp 0.7s ease-out forwards',
        'fade-in-down': 'fadeInDown 0.7s ease-out forwards',
        'scale-in': 'scaleIn 0.5s ease-out forwards',
        'slide-in-right': 'slideInRight 0.5s ease-out forwards',
        'slide-in-left': 'slideInLeft 0.5s ease-out forwards',
        'botanical-grow': 'botanicalGrow 2s ease-out forwards',
        'ink-spread': 'inkSpread 1.5s ease-out forwards',
        'pulse-gentle': 'pulseGentle 3s infinite ease-in-out',
        'float': 'float 6s ease-in-out infinite',
        'shimmer': 'shimmer 2.5s infinite linear',
      },
      keyframes: {
        border: {
          '0%, 100%': { backgroundPosition: '0% 50%' },
          '50%': { backgroundPosition: '100% 50%' },
        },
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        fadeInUp: {
          '0%': { opacity: '0', transform: 'translateY(20px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        fadeInDown: {
          '0%': { opacity: '0', transform: 'translateY(-20px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        scaleIn: {
          '0%': { opacity: '0', transform: 'scale(0.95)' },
          '100%': { opacity: '1', transform: 'scale(1)' },
        },
        slideInRight: {
          '0%': { opacity: '0', transform: 'translateX(20px)' },
          '100%': { opacity: '1', transform: 'translateX(0)' },
        },
        slideInLeft: {
          '0%': { opacity: '0', transform: 'translateX(-20px)' },
          '100%': { opacity: '1', transform: 'translateX(0)' },
        },
        botanicalGrow: {
          '0%': { transform: 'scaleY(0)', transformOrigin: 'bottom' },
          '100%': { transform: 'scaleY(1)', transformOrigin: 'bottom' },
        },
        inkSpread: {
          '0%': { opacity: '0', transform: 'scale(0.8) rotate(-2deg)' },
          '100%': { opacity: '1', transform: 'scale(1) rotate(0deg)' },
        },
        pulseGentle: {
          '0%, 100%': { opacity: '1' },
          '50%': { opacity: '0.8' },
        },
        float: {
          '0%, 100%': { transform: 'translateY(0)' },
          '50%': { transform: 'translateY(-10px)' },
        },
        shimmer: {
          '0%': { backgroundPosition: '-1000px 0' },
          '100%': { backgroundPosition: '1000px 0' },
        },
      },
    },
  },
};
export default config;

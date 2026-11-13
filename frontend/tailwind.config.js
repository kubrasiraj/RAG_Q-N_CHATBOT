// Every color comes from the CSS variables in src/styles/globals.css (the design tokens).
const token = (name) => `rgb(var(--${name}) / <alpha-value>)`;

/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        app: token('c-app'),
        sidebar: token('c-sidebar'),
        workspace: token('c-workspace'),
        card: token('c-card'),
        elevated: token('c-elevated'),
        line: token('c-line'),
        brand: { DEFAULT: token('c-brand'), deep: token('c-deep'), mint: token('c-mint') },
        ink: { DEFAULT: token('c-ink'), soft: token('c-soft'), muted: token('c-muted') },
        warn: token('c-warn'),
        danger: token('c-danger'),
      },
      fontFamily: { sans: ['"Inter Variable"', 'Inter', 'system-ui', 'sans-serif'] },
      boxShadow: {
        card: '0 1px 0 rgb(255 255 255 / 0.03) inset, 0 10px 30px -16px rgb(0 0 0 / 0.7)',
        glow: '0 0 0 1px rgb(var(--c-brand) / 0.4), 0 0 36px -10px rgb(var(--c-brand) / 0.5)',
      },
      keyframes: {
        'fade-up': { from: { opacity: '0', transform: 'translateY(6px)' }, to: { opacity: '1', transform: 'none' } },
        shimmer: { '100%': { transform: 'translateX(100%)' } },
        'dot-pulse': { '0%,80%,100%': { opacity: '0.25' }, '40%': { opacity: '1' } },
      },
      animation: {
        'fade-up': 'fade-up 0.25s ease-out both',
        shimmer: 'shimmer 1.6s infinite',
        'dot-pulse': 'dot-pulse 1.2s infinite ease-in-out',
      },
    },
  },
  plugins: [],
};

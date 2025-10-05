import forms from '@tailwindcss/forms'

/** @type {import('tailwindcss').Config} */
export default {
  darkMode: 'class',
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        background: {
          DEFAULT: '#0f172a',
          muted: '#1e293b',
          subtle: '#1a2438',
        },
        primary: {
          DEFAULT: '#38bdf8',
          foreground: '#0f172a',
        },
        accent: {
          DEFAULT: '#6366f1',
          foreground: '#f8fafc',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
      },
      boxShadow: {
        panel: '0 20px 45px -20px rgba(15, 23, 42, 0.45)',
      },
    },
  },
  plugins: [forms],
}

/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './overlay.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        navy: { 900: '#0f172a', 800: '#1e293b', 700: '#334155', 600: '#475569' },
        accent: { DEFAULT: '#6366f1', light: '#818cf8', dark: '#4f46e5' },
      }
    },
  },
  plugins: [],
}

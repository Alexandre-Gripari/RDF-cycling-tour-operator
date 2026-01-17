/** @type {import('tailwindcss').Config} */
export default {
    content: [
      "./index.html",
      "./src/**/*.{js,ts,jsx,tsx}",
    ],
    theme: {
      extend: {
        fontFamily: {
          sans: ['Inter', 'sans-serif'],
          mono: ['Fira Code', 'monospace'],
        },
        colors: {
          bg: {
            main: '#0f172a',
            card: '#1e293b',
            hover: '#334155',
          },
          brand: {
            DEFAULT: '#10b981',
            glow: '#34d399',
            dim: 'rgba(16, 185, 129, 0.1)'
          }
        },
        boxShadow: {
          'neon': '0 0 10px rgba(16, 185, 129, 0.3)',
        }
      },
    },
    plugins: [],
  }

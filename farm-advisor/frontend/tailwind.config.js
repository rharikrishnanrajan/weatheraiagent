/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        farm: {
          50: '#f2f8f3',
          100: '#e1f0e4',
          200: '#c5e2cb',
          300: '#9bcca5',
          400: '#6caf78',
          500: '#489255',
          600: '#377543',
          700: '#2d5d36',
          800: '#274b2e',
          900: '#213e27',
          950: '#0d2212',
        },
        earth: {
          50: '#faf6f0',
          100: '#f3ece0',
          200: '#e5d7c0',
          300: '#d4bc9a',
          400: '#c19d73',
          500: '#b18454',
          600: '#9c6f44',
          700: '#7f5638',
          800: '#684732',
          900: '#563c2c',
        }
      }
    },
  },
  plugins: [],
}

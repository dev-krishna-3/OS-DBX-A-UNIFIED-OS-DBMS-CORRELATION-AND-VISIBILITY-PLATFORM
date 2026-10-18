import type { Config } from 'tailwindcss';
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        paper: '#fffdf6', ink: { DEFAULT: '#0e1116', 700: '#2a313c', 500: '#4a7fa8' },
        sky: { 50: '#eaf6ff', 100: '#d3ecfc', 200: '#a9d9f6', 400: '#62bcee', 500: '#3aa4ea' },
        sun: { DEFAULT: '#ffd84d', deep: '#ffb938' }, brick: '#d6453d',
      },
      fontFamily: { display: ['Fraunces', 'Georgia', 'serif'], sans: ['"DM Sans"', 'system-ui', 'sans-serif'] },
      borderRadius: { frame: '28px', card: '22px' },
      boxShadow: { frame: '0 30px 70px -25px rgba(30,100,170,.5)', soft: '0 14px 36px -18px rgba(20,70,120,.35)' },
    },
  },
  plugins: [],
} satisfies Config;

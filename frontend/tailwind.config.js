/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './pages/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        primary: '#cad2fd',
        secondary: '#c7bc92',
        background: '#020203',
        surface: '#1a191c',
        danger: '#EF4444',
        warning: '#F59E0B',
        outline: '#6c6e79',
      },
    },
  },
  plugins: [],
};

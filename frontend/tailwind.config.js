/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        display: ['Outfit', 'Inter', 'sans-serif'],
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['IBM Plex Mono', 'monospace'],
      },
      colors: {
        brand: {
          DEFAULT: '#22489E', // #22489E Deep UII Royal Blue
          blue: '#22489E',
          periwinkle: '#BDCDEA', // #BDCDEA Soft Periwinkle
          sand: '#D6CDC5', // #D6CDC5 Warm Sand
          pearl: '#EFEEF1', // #EFEEF1 Soft Warm Pearl Surface
          sidebar: '#F8FAFC', // #F8FAFC Soft Slate Sidebar
          ink: '#0F172A', // #0F172A Deep Slate Navy
          border: '#E2E8F0', // #E2E8F0 Mineral Slate 1px
        }
      }
    },
  },
  plugins: [],
}

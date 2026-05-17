import type { Config } from "tailwindcss";

export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        domain: {
          schedule: { DEFAULT: '#7c3aed', soft: '#f5f3ff' },
          todo:     { DEFAULT: '#0891b2', soft: '#ecfeff' },
          ledger:   { DEFAULT: '#16a34a', soft: '#ecfdf5' },
          finance:  { DEFAULT: '#854d0e', soft: '#fef3c7' },
          ideas:    { DEFAULT: '#a21caf', soft: '#fae8ff' },
          files:    { DEFAULT: '#475569', soft: '#f1f5f9' },
        },
        cat: {
          food:      { DEFAULT: '#9a3412', soft: '#ffedd5' },
          transport: { DEFAULT: '#0369a1', soft: '#e0f2fe' },
          living:    { DEFAULT: '#4d7c0f', soft: '#ecfccb' },
          leisure:   { DEFAULT: '#be185d', soft: '#fce7f3' },
          medical:   { DEFAULT: '#dc2626', soft: '#fef2f2' },
          fixed:     { DEFAULT: '#78716c', soft: '#f5f5f4' },
          misc:      { DEFAULT: '#a8a29e', soft: '#fafaf9' },
        },
      },
    },
  },
  plugins: [],
} satisfies Config;

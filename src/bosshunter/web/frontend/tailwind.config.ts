/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        background: 'hsl(var(--background))',
        foreground: 'hsl(var(--foreground))',
        card: {
          DEFAULT: 'hsl(var(--card))',
          foreground: 'hsl(var(--card-foreground))',
          border: 'hsl(var(--border))',
        },
        surface: {
          DEFAULT: 'hsl(var(--surface))',
          muted: 'hsl(var(--surface-muted))',
        },
        popover: {
          DEFAULT: 'hsl(var(--popover))',
          foreground: 'hsl(var(--popover-foreground))',
        },
        primary: {
          DEFAULT: 'hsl(var(--primary))',
          foreground: 'hsl(var(--primary-foreground))',
        },
        secondary: {
          DEFAULT: 'hsl(var(--secondary))',
          foreground: 'hsl(var(--secondary-foreground))',
        },
        muted: {
          DEFAULT: 'hsl(var(--muted))',
          foreground: 'hsl(var(--muted-foreground))',
        },
        accent: {
          DEFAULT: 'hsl(var(--accent))',
          foreground: 'hsl(var(--accent-foreground))',
        },
        success: {
          soft: 'hsl(var(--success-soft))',
          border: 'hsl(var(--success-border))',
          DEFAULT: 'hsl(var(--success))',
          strong: 'hsl(var(--success-strong))',
        },
        warning: {
          soft: 'hsl(var(--warning-soft))',
          border: 'hsl(var(--warning-border))',
          DEFAULT: 'hsl(var(--warning))',
          strong: 'hsl(var(--warning-strong))',
        },
        danger: {
          soft: 'hsl(var(--danger-soft))',
          border: 'hsl(var(--danger-border))',
          DEFAULT: 'hsl(var(--danger))',
          strong: 'hsl(var(--danger-strong))',
          solid: 'hsl(var(--danger-solid))',
          'solid-foreground': 'hsl(var(--danger-solid-foreground))',
        },
        info: {
          soft: 'hsl(var(--info-soft))',
          border: 'hsl(var(--info-border))',
          DEFAULT: 'hsl(var(--info))',
          strong: 'hsl(var(--info-strong))',
        },
        cyan: {
          soft: 'hsl(var(--cyan-soft))',
          border: 'hsl(var(--cyan-border))',
          DEFAULT: 'hsl(var(--cyan))',
        },
        sky: {
          soft: 'hsl(var(--sky-soft))',
          border: 'hsl(var(--sky-border))',
          DEFAULT: 'hsl(var(--sky))',
        },
        purple: {
          soft: 'hsl(var(--purple-soft))',
          border: 'hsl(var(--purple-border))',
          DEFAULT: 'hsl(var(--purple))',
        },
        star: 'hsl(var(--star))',
        border: 'hsl(var(--border))',
        input: 'hsl(var(--input))',
        ring: 'hsl(var(--ring))',
        scrollbar: {
          track: 'hsl(var(--scrollbar-track))',
          thumb: 'hsl(var(--scrollbar-thumb))',
          'thumb-hover': 'hsl(var(--scrollbar-thumb-hover))',
        },
      },
      borderRadius: {
        lg: 'var(--radius)',
        md: 'calc(var(--radius) - 2px)',
        sm: 'calc(var(--radius) - 4px)',
      },
    },
  },
  plugins: [],
}

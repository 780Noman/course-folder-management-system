/** @type {import('tailwindcss').Config} */
module.exports = {
  // Scan project-level templates and each app's templates for class names.
  content: [
    "./templates/**/*.html",
    "./*/templates/**/*.html",
  ],
  theme: {
    extend: {
      colors: {
        // Semantic tokens (see design-system/.../MASTER.md). Values are
        // WCAG AA verified for their text pairings.
        primary: {
          DEFAULT: "#166534",
          strong: "#14532D",
        },
        "on-primary": "#FFFFFF",
        accent: {
          DEFAULT: "#9A6B00",
        },
        "on-accent": "#FFFFFF",
        background: "#F7F6F2",
        foreground: "#1C1917",
        card: "#FFFFFF",
        muted: {
          DEFAULT: "#EFEDE6",
          foreground: "#57534E",
        },
        border: "#E0DDD3",
        success: "#166534",
        warning: "#B45309",
        destructive: "#B91C1C",
        ring: "#166534",
      },
      fontFamily: {
        display: ['"Crimson Pro"', "Georgia", "serif"],
        sans: ['"Atkinson Hyperlegible"', "system-ui", "sans-serif"],
      },
      borderRadius: {
        DEFAULT: "0.5rem",
      },
      boxShadow: {
        sm: "0 1px 2px rgba(28,25,23,0.05)",
        md: "0 4px 6px rgba(28,25,23,0.08)",
        lg: "0 10px 15px rgba(28,25,23,0.10)",
      },
    },
  },
  plugins: [],
};

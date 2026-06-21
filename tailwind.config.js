/** @type {import('tailwindcss').Config} */
module.exports = {
  // Scan project-level templates and each app's templates for class names.
  content: [
    "./templates/**/*.html",
    "./*/templates/**/*.html",
  ],
  theme: {
    extend: {},
  },
  plugins: [],
};

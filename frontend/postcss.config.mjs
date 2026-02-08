const config = {
  // Vite/Vitest (postcss-load-config) expects resolvable plugin modules.
  // Using a string entry in an array leaves it as a string and fails validation.
  plugins: {
    "@tailwindcss/postcss": {},
  },
};

export default config;

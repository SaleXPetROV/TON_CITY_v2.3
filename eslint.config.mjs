import frontendConfig from "./frontend/eslint.config.mjs";

export default [
  {
    ignores: [
      "**/node_modules/**",
      "frontend/build/**",
      "frontend/public/**",
      "frontend/plugins/**",
      "backend/**",
      "test_reports/**",
    ],
  },
  ...frontendConfig,
];

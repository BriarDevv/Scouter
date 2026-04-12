import { defineConfig, globalIgnores } from "eslint/config";
import nextVitals from "eslint-config-next/core-web-vitals";
import nextTs from "eslint-config-next/typescript";

const eslintConfig = defineConfig([
  ...nextVitals,
  ...nextTs,
  // Override default ignores of eslint-config-next.
  globalIgnores([
    // Default ignores of eslint-config-next:
    ".next/**",
    "out/**",
    "build/**",
    "next-env.d.ts",
    // Vendored third-party scripts (minified, not our code)
    "lib/vendor/**",
  ]),
  // Playwright e2e specs are CommonJS (sibling of playwright.config.cjs).
  // Allow require() style imports there — converting to ESM would require
  // dashboard-wide "type": "module" which affects too much else.
  {
    files: ["e2e/**/*.js", "e2e/**/*.cjs"],
    rules: {
      "@typescript-eslint/no-require-imports": "off",
    },
  },
]);

export default eslintConfig;

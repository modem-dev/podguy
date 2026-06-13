import { describe, expect, test } from "vitest";
import { execFileSync } from "node:child_process";
import { readdirSync } from "node:fs";

// Discover smoke tests instead of maintaining a registry; a new
// tests/test_*.sh file is automatically picked up.
const smokeTests = readdirSync("tests")
  .filter((name) => name.startsWith("test_") && name.endsWith(".sh"))
  .sort()
  .map((name) => `tests/${name}`);

if (smokeTests.length === 0) {
  throw new Error("no tests/test_*.sh smoke tests found");
}

describe("podguy smoke tests", () => {
  for (const script of smokeTests) {
    test(
      script,
      () => {
        execFileSync("bash", [script], { stdio: "inherit" });
        expect(true).toBe(true);
      },
      180_000,
    );
  }
});

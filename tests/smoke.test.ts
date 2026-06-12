import { describe, expect, test } from "vitest";
import { execFileSync } from "node:child_process";

const smokeTests = [
  "tests/test_transcribe_video.sh",
  "tests/test_prepare_transcript_analysis.sh",
  "tests/test_scan_podcast.sh",
  "tests/test_cut_clips.sh",
  "tests/test_youtube_publish.sh",
  "tests/test_download_sample_media.sh",
  "tests/test_launcher.sh",
];

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

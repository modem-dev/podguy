import { existsSync, readFileSync } from "node:fs";
import { homedir } from "node:os";
import { relative, resolve } from "node:path";
import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";

const WIDGET_ID = "podguy-startup";
const cwd = process.cwd();
const home = homedir();

function toDisplayPath(filePath: string): string {
  const normalized = filePath.replaceAll("\\", "/");
  const normalizedCwd = cwd.replaceAll("\\", "/");
  const normalizedHome = home.replaceAll("\\", "/");

  if (normalized === normalizedCwd) return ".";
  if (normalized.startsWith(`${normalizedCwd}/`)) {
    return `./${relative(cwd, filePath).replaceAll("\\", "/")}`;
  }
  if (normalized.startsWith(`${normalizedHome}/`)) {
    return `~/${relative(home, filePath).replaceAll("\\", "/")}`;
  }
  return normalized;
}

function readProfileSummary(): string | undefined {
  for (const profilePath of [resolve(cwd, "podguy.toml"), resolve(cwd, "podcast.toml")]) {
    if (!existsSync(profilePath)) continue;
    try {
      const text = readFileSync(profilePath, "utf8");
      const showName = text.match(/^\s*show_name\s*=\s*["']([^"']+)["']/m)?.[1];
      const displayPath = toDisplayPath(profilePath);
      return showName ? `${showName} (${displayPath})` : displayPath;
    } catch {
      return toDisplayPath(profilePath);
    }
  }
  return undefined;
}

function formatSection(
  theme: { fg(color: "mdHeading" | "text" | "muted" | "dim", text: string): string },
  label: string,
  items: Array<{ path: string; scope: string }>,
): string[] {
  if (items.length === 0) return [];
  const prefix = `[${label}]`.padEnd(13, " ");
  const indent = " ".repeat(prefix.length);
  return items.map((item, index) => {
    const labelText = index === 0 ? theme.fg("mdHeading", prefix) : indent;
    const pathText = theme.fg("text", item.path);
    const scopeText = theme.fg("muted", `[${item.scope}]`);
    return `${labelText}${pathText} ${scopeText}`;
  });
}

export default function podguyStartupExtension(pi: ExtensionAPI) {
  pi.on("session_start", (_event, ctx) => {
    if (!ctx.hasUI) return;

    ctx.ui.setHeader((_tui, theme) => ({
      render(_width: number): string[] {
        const accent = (text: string) => theme.fg("accent", text);
        const muted = (text: string) => theme.fg("muted", text);
        const dim = (text: string) => theme.fg("dim", text);

        const projectAgents = resolve(cwd, "AGENTS.md");
        const userAgents = resolve(home, ".pi/agent/AGENTS.md");
        const skillPaths = [
          resolve(cwd, "src/podguy-post-production/SKILL.md"),
          resolve(cwd, "src/podguy-clip-cutter/SKILL.md"),
          resolve(cwd, "src/podguy-youtube-publisher/SKILL.md"),
        ];
        const promptsPath = resolve(cwd, "prompts");
        const extensionPath = resolve(cwd, "src/podguy-startup.ts");
        const profilePath = [resolve(cwd, "podguy.toml"), resolve(cwd, "podcast.toml")].find(
          (path) => existsSync(path),
        );
        const themePath = ctx.ui.theme.sourcePath;
        const themeScope = ctx.ui.theme.sourceInfo?.scope;

        const contextItems = [
          ...(existsSync(projectAgents)
            ? [{ path: toDisplayPath(projectAgents), scope: "project" }]
            : []),
          ...(existsSync(userAgents) ? [{ path: toDisplayPath(userAgents), scope: "user" }] : []),
        ];
        const skillItems = skillPaths
          .filter((path) => existsSync(path))
          .map((path) => ({ path: toDisplayPath(path), scope: "project" }));
        const promptItems = existsSync(promptsPath)
          ? [{ path: toDisplayPath(promptsPath), scope: "project" }]
          : [];
        const extensionItems = existsSync(extensionPath)
          ? [{ path: toDisplayPath(extensionPath), scope: "project" }]
          : [];
        const profileItems = profilePath
          ? [{ path: toDisplayPath(profilePath), scope: "project" }]
          : [];
        const themeItems = themePath
          ? [{ path: toDisplayPath(themePath), scope: themeScope ?? "user" }]
          : ctx.ui.theme.name
            ? [{ path: ctx.ui.theme.name, scope: "builtin" }]
            : [];

        const profileSummary = readProfileSummary();

        return [
          accent("                     __                 "),
          accent("    ____  ____  ____/ /___ ___  ____  __"),
          accent("   / __ \\/ __ \\/ __  / __ `/ / / / / / /"),
          accent("  / /_/ / /_/ / /_/ / /_/ / /_/ / /_/ / "),
          accent(" / .___/\\____/\\__,_/\\__, /\\__,_/\\__, /  "),
          accent("/_/                /____/      /____/"),
          muted("  Podcast post-production"),
          dim(profileSummary ? `  profile: ${profileSummary}` : "  no podguy.toml profile yet"),
          "",
          ...formatSection(theme, "Context", contextItems),
          ...formatSection(theme, "Profile", profileItems),
          ...formatSection(theme, "Skill", skillItems),
          ...formatSection(theme, "Prompts", promptItems),
          ...formatSection(theme, "Extension", extensionItems),
          ...formatSection(theme, "Theme", themeItems),
        ];
      },
      invalidate() {},
    }));

    ctx.ui.setWidget(WIDGET_ID, [
      "Start here:",
      '- Say: Analyze "episode-006-draft.mp4" as ep006',
      "- Optional: copy podguy.example.toml to podguy.toml and set show_name/hosts/tone",
      "- If your ask is broad, pi should clarify: quick pass or full review?",
      "- Quick pass = optional scan + transcript + prep + short summary",
      "- Full review = quick pass + chapters + clips + cuts + notes + quotes + cleanup",
      "- Cut social exports after clips exist: /cut-clips ep006",
      "- Upload finished episodes to YouTube: /publish-youtube ep006",
      "- Optional shortcuts: /phase1 ep006 | /full-review ep006 | /chapters ep006 | /cuts ep006 | /cut-clips ep006 | /publish-youtube ep006",
    ]);
  });

  pi.on("agent_start", async (_event, ctx) => {
    if (!ctx.hasUI) return;
    ctx.ui.setWidget(WIDGET_ID, undefined);
  });
}

# Optional integration: Playwright MCP

**Status:** optional developer tooling — not bundled, not required, not part of
the Stitchcraft runtime. The built-in AI browser (Obscura) already covers
screenshots and DOM audits; Playwright MCP is for interactive end-to-end testing
against a running preview.

## What it is

[Playwright MCP](https://github.com/microsoft/playwright-mcp) is Microsoft's Model
Context Protocol server that lets an AI client drive a real browser through the
accessibility tree: navigate, click, type, select options, wait for elements and
inspect the page. It is Apache-2.0 licensed and requires **Node.js 18+**.

## Why it is not bundled

- Stitchcraft's backend is Python standard library only; adding Node and browser
  binaries to the runtime would break the dependency-free/offline rule.
- Obscura already provides the built-in render/screenshot/DOM audit path.
- A second browser stack should be an explicit developer choice, not a silent
  install.

## Local setup

```bash
# Node 18+ is required. Install nothing into the Stitchcraft repo.
npx @playwright/mcp@latest --headless --isolated \
  --allowed-origins "http://127.0.0.1:8765" \
  --output-dir .stitch/playwright-mcp
```

Add it to your MCP client configuration (for Kiro, use the MCP servers panel or
your `mcp.json`). A typical stdio configuration looks like:

```json
{
  "mcpServers": {
    "playwright": {
      "command": "npx",
      "args": [
        "@playwright/mcp@latest",
        "--headless",
        "--isolated",
        "--allowed-origins",
        "http://127.0.0.1:8765",
        "--output-dir",
        ".stitch/playwright-mcp"
      ]
    }
  }
}
```

## Use it with Stitchcraft

1. Start the studio: `python -m stitchcraft app` (or `--no-window`).
2. Generate a site or open a project so the preview URL
   `http://127.0.0.1:<port>/api/preview/<project_id>/` is available.
3. Give the MCP client a test task, for example: "Open the preview, click
   **Add item**, fill the form, save, and confirm the row appears; check the
   console for errors."
4. Review the trace/screenshots under `.stitch/playwright-mcp/`.

Useful prompts for a generated site:

- "Check every primary nav link resolves and the mobile menu opens."
- "Tab through the page and report the focus order and any missing labels."
- "Submit the main form with an empty required field; confirm the error is shown."
- "Check the console for errors and failed network requests."

## Safety

- Point it at `127.0.0.1` only; never at production or a site with real accounts.
- Use `--isolated` so each session has a fresh profile; do not persist cookies.
- Do not paste API keys or secrets into prompts or forms.
- Treat recorded traces/screenshots as local artifacts; keep them out of Git
  (`.stitch/` is already ignored).

## License

Playwright MCP is Apache-2.0, Copyright Microsoft Corporation. It is **not
redistributed** in this repository; the user installs it from npm. This page and
the Stitchcraft repository only reference it as an optional integration.

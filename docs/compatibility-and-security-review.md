# MCP integration audit and Codex compatibility

This review covers repository commit `9088472ddacdb89f3c5943c3db6be7b8ee25c922` and the separately published npm package `meta-ads-mcp@1.1.0` selected by the configuration template at review time. The npm tarball SHA-1 reported by the registry was `1709b763abcd7115660069af08bef13b3a997823`.

The repository contains an analysis skill, configuration examples and helper scripts. It does **not** contain the MCP server implementation. Findings below distinguish this repository from its external dependency; fixes to the latter must be made upstream or in a reviewed replacement.

## Validation scope

The published server completed MCP initialization, tool discovery and a health check through the JavaScript MCP SDK against a local HTTP fixture with a fake token. It registered 39 tools. No real advertising account was authenticated and no advertising objects were changed. Protocol compatibility is therefore established for that fixture, not end-to-end authentication or reporting accuracy in Codex.

Production dependencies were installed in an isolated directory with lifecycle scripts disabled. `npm audit --omit=dev` reported zero known vulnerabilities for the resolved dependencies at review time. That result does not cover the logic and credential-handling issues described here.

## Findings in this repository

### 1. Unpinned external executable

`mcp/mcp.json.example`, `scripts/setup.sh` and `scripts/refresh_token.sh` launch `npx -y meta-ads-mcp` without a version. Installing the skill and reviewing this repository does not review whatever server version npm resolves later.

**Suggested improvement:** explicitly identify the external maintainer and package, pin a reviewed release, and document an update/review policy. Pinning `1.1.0` alone does not fix the defects listed below.

### 2. Credential serialization and file permissions

The setup script reads tokens and secrets visibly, then interpolates them into both executable shell assignments and JSON without escaping. Refresh executes the credential file with `source`. Generated credential files had mode `0644` under the test environment's umask.

**Reproduction:** supply a fake token containing a double quote; the generated `.mcp.json` is invalid JSON. A shell metacharacter stored in the shell file can also be interpreted when refresh sources it.

**Suggested improvement:** use hidden input, serialize credentials with a JSON library, avoid executable shell files as secret storage, and create credential files with mode `0600`. Do not print authentication responses containing secrets.

### 3. Connection success is not sufficiently validated

Setup classifies a response as successful whenever its text does not contain `error`. An empty response from a curl fixture with exit status zero produced `CONNECTION SUCCESSFUL`. A transport failure with a nonzero curl exit correctly stopped the script under `set -e`.

**Suggested improvement:** validate the HTTP status, parse JSON, require the expected `data` structure and distinguish zero accessible accounts from access to the intended account. Add bounded connection and request timeouts. Return a nonzero exit status for unsuccessful validation.

### 4. Destructive configuration replacement

Setup and refresh overwrite the entire project `.mcp.json`, potentially removing unrelated servers.

**Suggested improvement:** preserve existing entries and atomically update only `mcpServers.meta-ads`, or write a dedicated config fragment for explicit import.

### 5. Token lifecycle instructions do not match implementation

The README says setup exchanges a token for a long-lived token. Setup actually saves credentials and lists accounts; it performs no exchange. App ID is optional during setup but required by refresh, and is not forwarded to the server in the current MCP template. Scripts use Graph `v21.0`, while the external package defaults to `v23.0`.

**Suggested improvement:** document acquisition, exchange, validation and renewal as separate operations; forward required configuration; use one configurable, supported API version. This review does not establish that either API version is retired.

## Reproduced defects in external `meta-ads-mcp@1.1.0`

Paths in this section refer to the npm package's source and published build, not files maintained in this repository.

| Finding | Evidence / reproduction | Suggested upstream fix |
| --- | --- | --- |
| Requested breakdown dimensions and financial fields disappear | `src/tools/analytics.ts` maps `get_insights` rows to a fixed field list. A fixture containing `age`, `publisher_platform`, `purchase_roas` and `action_values` lost all four in the response. | Preserve requested/raw response fields, including dimension labels; add round-trip fixtures. |
| Insights pagination cannot be continued through the tool | `GetInsightsSchema` lacks `after`, although `get_insights` returns a cursor. Summaries and comparisons use the fetched page. | Expose cursors or collect all pages; clearly label partial summaries and comparisons. |
| Aggregate data is labeled daily | `get_campaign_performance` returns `daily_breakdown` without setting `time_increment=1`; the public schema has no `time_increment`. | Request daily granularity explicitly, or rename the output to match its actual aggregation. |
| Zero values vanish from rankings | `getMetricValue` uses `total_x || average_x || x`. Two fixture campaigns with zero clicks produced an empty clicks ranking. | Use nullish fallback and preserve valid zero values. |
| OAuth URL has a duplicate version prefix | `AuthManager.generateAuthUrl()` adds `v` to the default `v23.0`, producing `/vv23.0/dialog/oauth`. | Normalize the version prefix once. |
| Explicit seven-day preset is rejected | `GetInsightsSchema` rejects `date_preset: "last_7d"`, although the tool uses it as its default. | Align schemas, defaults and documented presets. |
| Token prefix is logged | `src/index.ts` prints the first 20 token characters on startup; the fake-token prefix appeared in captured stderr. | Remove token material from logs; review OAuth tool outputs that return complete tokens. |

Additional source-level concerns:

- The server registers write-capable tools, including campaign creation, deletion, pause and resume. It should not be described or deployed as read-only without an enforced tool allowlist and appropriate credential permissions.
- `autoRefreshToken()` treats an unknown expiration as not expiring. With `META_AUTO_REFRESH=true`, startup returns the configured token through that path without running the normal validation. Load/verify expiration and validate the token; do not report renewal merely because this method returned.
- Refresh messages use `console.log` on stdout, which is also the stdio MCP protocol channel. Send diagnostics to stderr.
- Summary calculation sums reach across rows and derives frequency from that sum. Reach is not generally additive across overlapping entities or time slices; obtain deduplicated aggregate reach at the requested reporting level.
- Attribution summary combines purchases and registrations, then divides by all clicks. Select the relevant action event and explicitly define denominator, attribution window and reporting period.
- The skill requires `get_recommendations`, but that name was absent from the server's 39 discovered tools. Treat recommendations as optional unless a documented capability exists.

## Skill guidance that needs clarification

The nine reference files do not include source URLs supporting their description as official Meta documentation. Add primary links, retrieval dates and applicability notes.

The skill defines conversion rate using impressions, while the external attribution implementation uses all clicks. Neither denominator should be silently assumed for every conversion metric. Specify the metric being calculated.

The fixed 20–30% and 50% fluctuation thresholds lack supporting references in the files. Present heuristics as such and account for sample size, objective and baseline. Likewise, low CPM alone does not establish better business performance.

Marginal-efficiency explanations should be framed as hypotheses unless the data establishes them. Average segment CPA and aggregate time series do not, on their own, prove why delivery was allocated.

The terminology guidance claims legal requirements without citations and contains conflicting instructions for “people” and “person.” Cite the applicable policy or remove the unsupported legal assertion.

## Codex compatibility and suggested installation

The skill's `SKILL.md` frontmatter has the expected `name` and `description`. Preserve its references and place the folder at `.agents/skills/meta-ads-analyzer/` for project-scoped Codex discovery, rather than relying on `.claude/skills/`.

Codex supports stdio MCP servers. Direct local server configuration uses `[mcp_servers.<name>]` in `config.toml`; copying this repository's Claude `.mcp.json` by itself does not register a direct Codex server. Plugins can separately bundle MCP configuration.

The following is an **illustrative disabled configuration**, not a claim that the external package's reporting defects are fixed. Enable it only after addressing the relevant defects and testing authentication. Set environment variables outside version-controlled files.

```toml
[mcp_servers.meta_ads_analyzer]
command = "npx"
args = ["-y", "meta-ads-mcp@1.1.0"]
env_vars = ["META_ACCESS_TOKEN"]
enabled = false
startup_timeout_sec = 30
tool_timeout_sec = 60
enabled_tools = [
  "get_ad_accounts",
  "get_campaign",
  "list_campaigns",
  "list_ad_sets",
  "list_ads",
  "get_insights",
  "health_check",
]
```

Use analysis-only permissions where feasible, verify account identity, currency, timezone, explicit dates and daily versus lifetime budgets, and separate reach, profile visits, followers, leads and customers. Do not assume an API-created campaign is equivalent to the Instagram in-app Boost workflow.

Official Codex references:

- [MCP configuration, environment forwarding and tool allowlists](https://learn.chatgpt.com/docs/extend/mcp?surface=cli)
- [Skill structure and local discovery](https://learn.chatgpt.com/docs/build-skills)

## Proposed remediation order

1. Harden credential storage, remove secret logging, preserve existing configs and enforce read-only tool access for analysis.
2. Correct field preservation, pagination, granularity, zero handling and aggregate metrics in the external server.
3. Fix and test OAuth URLs, token validation/renewal and API-version consistency.
4. Align the skill with actual server capabilities and add citations for its domain claims.
5. Test the revised integration in Codex with an authorized account. Validate identity and a known reporting fixture before relying on recommendations.

## Reproducing the isolated protocol check

Download and inspect the package before executing it:

```sh
npm pack meta-ads-mcp@1.1.0 --ignore-scripts
```

In an isolated extraction, install dependencies with lifecycle scripts disabled. Start a local HTTP fixture returning `{ "id": "fixture" }` for `/v23.0/me` and `{ "data": [] }` for `/v23.0/me/adaccounts`. Launch the package's `build/index.js` with a fake token of at least ten characters and `META_BASE_URL` pointing to that fixture. Use an MCP SDK client to initialize, list tools and call `health_check`; capture stderr to verify whether token material is logged.

For analytics, register `registerAnalyticsTools` with a fixture client returning the rows described above and invoke the captured callbacks. This exercises response transformation without accessing Meta or changing campaigns. A local health check passing only proves fixture connectivity.

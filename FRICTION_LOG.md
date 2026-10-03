# Friction Log

Every tool/API/SDK friction point we hit while building HotSeat.
The hackathon awards up to a **10% judging bonus** in Stage 1 for friction logs —
so we log everything: what we tried, what broke, what worked, what we'd change.

## Template

### YYYY-MM-DD — <tool/API>
- **What we were doing:**
- **What happened:**
- **Workaround / fix:**
- **Would use again?** (yes / with caveats / no)
- **Feature request for the vendor:**

---

## Log

### 2026-10-02 — MCP Python SDK (`mcp==2.2.0`)
- **What we were doing:** Verifying Streamable HTTP server support for the
  Alexa+ track requirement (MCP spec 2025-11-25+, Streamable HTTP transport).
- **What happened:** `mcp` has no `__version__` attribute (minor annoyance when
  checking versions programmatically); `StreamableHTTPSessionManager` imports
  cleanly and works as documented.
- **Workaround / fix:** Used `pip show` / `importlib.metadata` for version checks.
- **Would use again?** Yes.
- **Feature request for the vendor:** Expose `mcp.__version__`.

### 2026-10-02 — MCP Python SDK v2 migration (`mcp==2.2.0`)
- **What we were doing:** Wiring the Streamable HTTP server. Wrote it first with
  the classic `Server` + `@server.list_tools()` / `@server.call_tool()` decorator
  pattern from the v1 docs.
- **What happened:** `AttributeError: 'Server' object has no attribute 'list_tools'`.
  In SDK 2.x, `FastMCP` was renamed to `MCPServer` (`mcp.server.mcpserver`), and
  the decorator API moved there as `@mcp.tool()` with `streamable_http_app()`.
  The migration guide URL is printed in the FastMCP import error, which helped.
- **Workaround / fix:** Rewrote `src/server.py` on `MCPServer`; verified
  initialize handshake (protocolVersion 2025-11-25), `tools/list`, and a live
  `tools/call` over Streamable HTTP with session-id headers.
- **Would use again?** Yes — but pin the major version in requirements and read
  the v2 migration guide first.
- **Feature request for the vendor:** Keep a `Server.list_tools` compatibility
  shim (or a louder error message pointing at `MCPServer`).

### 2026-10-03 — Strands `BedrockModel` eager credential lookup
- **What we were doing:** Constructing Strands agents in a test environment
  without AWS credentials.
- **What happened:** `BedrockModel.__init__` immediately calls
  `boto3.session.client(...)`, which triggers the credential chain — with no
  keys set it falls through to IMDS, which fails behind our proxy. Agent
  *construction* shouldn't need credentials; only *invocation* should.
- **Workaround / fix:** Set dummy `AWS_ACCESS_KEY_ID`/`AWS_SECRET_ACCESS_KEY`
  env vars in tests (client creation makes no network calls). In production
  `make_client()` only builds the Strands backend when real creds exist.
- **Would use again?** Yes — with the lazy-construction caveat documented.
- **Feature request for the vendor:** Defer client/credential resolution to
  first invoke, not `__init__`.

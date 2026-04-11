# Credential & Sensitive Data Protocol
## ABSOLUTE — non-negotiable rules

### Hard Rules

1. **NEVER create accounts or generate API keys.** Guide the user to do it themselves.
2. **NEVER store credentials in plain text** outside of `.env` files.
3. **NEVER commit credentials to git.** Verify `.gitignore` includes `.env`, `*.key`, `*.pem`, `credentials/` before every commit.
4. **NEVER log, echo, print, or write credentials** to any file other than `.env`. This includes: mission boards, LESSONS.md, recall-stack primer, claude-mem observations, chat output.
5. **NEVER send credentials to any endpoint** without explicit user approval.
6. **ALWAYS use environment variable references** in code (`process.env.KEY_NAME`), never raw values.
7. **ALWAYS maintain a credential inventory** (service + env var name, NEVER values).

### Credential Lifecycle

**Discovery:** Commander identifies a tool/API needs auth → reports to user with:
- What service needs authentication
- How to sign up (URL, steps)
- Cost profile (free tier? paid?)
- What env var name to use

**Collection:** User creates account, generates key, provides to system.

**Storage:**
- Project-level: `.env` file (auto-added to `.gitignore`)
- Global: macOS Keychain (for cross-project credentials)
- MCP-specific: `claude mcp add` with env vars
- `.env.example` committed with empty values as template

**Usage:** Code reads `process.env.KEY_NAME`. Key never in source.

**Rotation:** Commander flags expired/failed keys, user generates new one.

**Revocation:** Commander reminds user to revoke unused keys from provider dashboards.

### Project Structure

Every project with credentials gets:

```
project-root/
├── .env              ← actual keys (NEVER committed)
├── .env.example      ← template with empty values (committed)
├── .gitignore        ← MUST include: .env, *.key, *.pem, credentials/
```

### Credential Inventory Format

In the mission board (values NEVER shown):

```
## Connected Services
| Service | Auth Method | Env Variable | Status |
|---------|-------------|--------------|--------|
| Unsplash | API Key | UNSPLASH_ACCESS_KEY | ✅ Configured |
| GitHub | Token | GITHUB_TOKEN | ✅ In keychain |
| Pinterest | None (Playwright) | N/A | ✅ No auth needed |
```

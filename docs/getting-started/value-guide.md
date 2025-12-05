# 💎 What Value Do You Get?

This guide shows exactly what SpecMem gives you and how to use each feature.

## 30-Second Value: Demo

```bash
pip install specmem[local]
specmem demo
```

**What you see:** A dashboard with SpecMem's own specs - browse, search, see relationships.

---

## 2-Minute Value: Your Project Dashboard

```bash
cd your-project
specmem init
specmem scan
specmem serve
```

**What you get:**

### 📊 Spec Overview
All your specifications in one searchable place:
- Requirements, designs, tasks from `.kiro/specs/`
- `CLAUDE.md`, `.cursorrules` if you use those
- Organized by feature, searchable by content

### 💚 Health Score
A grade (A-F) showing your project's spec health:
```bash
specmem health
```
```
Project Health: B (82/100)

✅ Strengths:
   • 47 specs indexed
   • 89% have code references
   • Average freshness: 12 days

⚠️  Issues:
   • 3 orphaned specs (no code references)
   • 2 stale specs (>90 days old)
```

### 📈 Coverage Report
See which acceptance criteria have tests:
```bash
specmem cov
```
```
Spec Coverage: 68%

auth-requirements.md: 80% (4/5 criteria tested)
  ✅ 1.1 User login
  ✅ 1.2 Password validation
  ✅ 1.3 Session management
  ❌ 1.4 Rate limiting (no test found)
  ✅ 1.5 Logout

payment-requirements.md: 50% (2/4 criteria tested)
  ...
```

---

## 5-Minute Value: Agent Integration

### For Kiro Users

Add SpecMem as an MCP server:

```json
// .kiro/settings/mcp.json
{
  "mcpServers": {
    "specmem": {
      "command": "specmem-mcp",
      "args": []
    }
  }
}
```

**What you get:** Kiro's agent can now query your specs automatically!

When you ask Kiro to implement a feature, it can:
- Look up relevant requirements
- Check design decisions
- Find related tests

### For Any Agent (Python API)

```python
from specmem import SpecMemClient

sm = SpecMemClient()

# Before implementing auth changes
context = sm.get_context_for_change(["src/auth/service.py"])
print(context.tldr)
# "Auth service implements JWT-based authentication.
#  Key requirements: rate limiting (1.4), session timeout (1.3).
#  Related tests: test_auth.py, test_login.py"
```

---

## 10-Minute Value: Impact Analysis

Before making changes, know what's affected:

```bash
specmem impact --files src/auth/service.py
```

```
Impact Analysis for: src/auth/service.py

📋 Affected Specs:
   • .kiro/specs/auth/requirements.md
   • .kiro/specs/auth/design.md

🧪 Suggested Tests:
   • tests/test_auth.py
   • tests/test_login.py
   • tests/integration/test_auth_flow.py

⚠️  Acceptance Criteria to Verify:
   • 1.1 User login with valid credentials
   • 1.3 Session management
   • 1.4 Rate limiting
```

---

## Ongoing Value: Living Documentation

### Spec Drift Detection
```bash
specmem drift
```
Finds specs that have drifted from implementation.

### Contradiction Detection
```bash
specmem validate
```
Finds conflicting requirements across specs.

### Stale Spec Cleanup
```bash
specmem prune --dry-run
```
Identifies specs that should be archived or deleted.

---

## Value Summary

| Feature | Command | What You Learn |
|---------|---------|----------------|
| **Demo** | `specmem demo` | How SpecMem works |
| **Dashboard** | `specmem serve` | Visual overview of all specs |
| **Health** | `specmem health` | Project spec quality grade |
| **Coverage** | `specmem cov` | Which criteria are tested |
| **Impact** | `specmem impact` | What's affected by changes |
| **Query** | `specmem query "..."` | Find relevant specs |
| **Validate** | `specmem validate` | Find spec issues |

---

## Next Steps

1. **Try the demo:** `specmem demo`
2. **Set up your project:** `specmem init && specmem scan && specmem serve`
3. **Add MCP integration:** Connect to Kiro for automatic spec awareness
4. **Run in CI:** Add `specmem cov` and `specmem health` to your pipeline

# specmem cov

Analyze the gap between specification acceptance criteria and existing tests.

## Overview

The `specmem cov` command provides spec coverage analysis - measuring how well your acceptance criteria are covered by tests. It scans your spec files to extract acceptance criteria, scans test files to find test functions, and uses semantic matching to link them together.

## Usage

```bash
# Show overall coverage summary
specmem cov

# Show detailed report for a feature
specmem cov report user-authentication

# Get test suggestions for uncovered criteria
specmem cov suggest user-authentication

# Generate coverage badge for README
specmem cov badge

# Export coverage data
specmem cov export --format json
specmem cov export --format markdown
```

## Commands

### `specmem cov`

Shows overall coverage summary with a table of all features.

```bash
$ specmem cov

📊 Spec Coverage Report ✅
========================================
Overall: 374/463 criteria covered (80.8%)

                      Coverage by Feature  
┏━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━┳━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━━┓
┃ Feature               ┃ Tested ┃ Total ┃ Coverage ┃      Gap ┃
┡━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━╇━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━━┩
│ user-authentication   │      8 │    12 │    66.7% │ 33.3% ⚠️ │
│ payment-processing    │     15 │    15 │   100.0% │  0.0% ✅ │
│ notification-system   │      6 │    10 │    60.0% │ 40.0% ⚠️ │
└───────────────────────┴────────┴───────┴──────────┴──────────┘
```

### `specmem cov report [FEATURE]`

Shows detailed coverage for a specific feature or all features.

```bash
$ specmem cov report user-authentication

user-authentication ⚠️
Coverage: 8/12 (66.7%)

  ✅ AC 1.1: WHEN user provides valid credentials... → tests/test_auth.py:45
  ✅ AC 1.2: WHEN user provides invalid credentials... → tests/test_auth.py:67
  ⚠️ AC 1.3: WHEN user fails login 5 times... → NO TEST FOUND
  ⚠️ AC 1.4: WHEN session inactive 30min... → NO TEST FOUND
```

Options:
- `--path, -p`: Workspace path (default: current directory)
- `--verbose, -v`: Show detailed output

### `specmem cov suggest FEATURE`

Get test suggestions for uncovered acceptance criteria.

```bash
$ specmem cov suggest user-authentication

📝 Test Suggestions for: user-authentication
==================================================

1. AC 1.3:
   "WHEN user fails login 5 times THEN system SHALL lock account..."

   Suggested test approach:
   - Test file: tests/test_user_authentication.py
   - Test name: test_user_fails_login_5_times
   - What to verify:
     • Verify: the system SHALL lock account

2. AC 1.4:
   "WHEN session inactive 30min THEN system SHALL expire session..."

   Suggested test approach:
   - Test file: tests/test_user_authentication.py
   - Test name: test_session_inactive_30min
   - What to verify:
     • Verify: the system SHALL expire session

💡 Copy these suggestions to your agent to generate the actual tests.
```

### `specmem cov badge`

Generate a coverage badge for your README.

```bash
$ specmem cov badge
![Spec Coverage](https://img.shields.io/badge/Spec_Coverage-80%25-green)

# Save to file
$ specmem cov badge --output COVERAGE_BADGE.md
```

Badge colors:
- 🔴 Red: Coverage < 50%
- 🟡 Yellow: Coverage 50-80%
- 🟢 Green: Coverage > 80%

### `specmem cov export`

Export coverage data in JSON or Markdown format.

```bash
# Export as JSON
$ specmem cov export --format json > coverage.json

# Export as Markdown
$ specmem cov export --format markdown > COVERAGE.md

# Export to specific file
$ specmem cov export --format json --output coverage-report.json
```

## How It Works

1. **Extract Criteria**: Parses `requirements.md` files in `.kiro/specs/` to extract numbered acceptance criteria in EARS format.

2. **Scan Tests**: Scans test files (pytest, jest, vitest, playwright, mocha) to extract test functions with their docstrings.

3. **Match**: Uses two matching strategies:
   - **Explicit links**: Tests with `Validates: X.Y` in docstrings get confidence 1.0
   - **Semantic matching**: Text similarity between criterion and test name/docstring

4. **Report**: Criteria with confidence ≥ 0.5 are considered "covered".

## Linking Tests to Criteria

For best results, add explicit links in your test docstrings:

```python
def test_account_lockout_after_failed_attempts():
    """Test that accounts are locked after 5 failed login attempts.

    Validates: 1.3
    """
    # Test implementation
```

```typescript
// Validates: 1.3
test('account lockout after failed attempts', () => {
  // Test implementation
});
```

## Python API

```python
from specmem import SpecMemClient

client = SpecMemClient()

# Get overall coverage
result = client.get_coverage()
print(f"Coverage: {result.coverage_percentage:.1f}%")

# Get coverage for specific feature
result = client.get_coverage("user-authentication")

# Get test suggestions
suggestions = client.get_coverage_suggestions("user-authentication")
for s in suggestions:
    print(f"- {s.criterion.number}: {s.suggested_name}")

# Generate badge
badge = client.get_coverage_badge()
```

## See Also

- [specmem validate](validate.md) - Validate spec quality
- [specmem impact](impact.md) - Analyze impact of changes

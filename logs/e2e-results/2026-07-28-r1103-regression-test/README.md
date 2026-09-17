# R110-3 Regression Verification (2026-07-28)

**Purpose:** Verify the R110-3 fix reverts the OPENAI_HOST regression
introduced by R110-1 (c5e854d), and that the corrected config actually
works end-to-end.

**Related commits:**
- R110-1 (c5e854d) — introduced the bug (added /v1 to OPENAI_HOST)
- R110-2 (6bd2a3a) — evidence report documenting the regression
- R110-3 (this commit) — the fix (revert OPENAI_HOST change)

## Method

Run the same recipe (`sub_mas-unix-test-runner.yaml`) under two
configurations, capture full stdout/stderr to log files, then read back
the recorded HTTP status codes from goose output.

| Scenario | OPENAI_HOST | Expected | Log file |
|----------|-------------|----------|----------|
| A — R110-3 fix (correct) | `https://api.deepseek.com` (no /v1) | recipe executes, LLM responds | `evidence/A-r1103-no-v1-goose-run.log` |
| B — R110-1 broken (control) | `https://api.deepseek.com/v1` (with /v1) | HTTP 404 at `/v1/v1/chat/completions` | `evidence/B-r1101-with-v1-control-run.log` |

Both scenarios use the same model (`deepseek-v4-flash`), the same
recipe, and the same `DEEPSEEK_API_KEY` (loaded from
`mas-engineer/.env`).

## Results

### Scenario A (R110-3 fix, correct)

```
exit: 0
elapsed: 19.4s
log size: 13647 bytes
HTTP status: 200 OK (recipe executed, LLM responded with code review)
```

Goose loaded the recipe, called DeepSeek via the OpenAI-compatible
endpoint, received a 200 response with a real LLM answer, and the
session ended cleanly. No HTTP error, no path-doubling.

### Scenario B (R110-1 broken, control)

```
exit: 0 (process completed, but recipe did NOT run)
elapsed: 8.6s
log size: 717 bytes
HTTP status: 404 Not Found
error: Request failed: Resource not found (404) at
       https://api.deepseek.com/v1/v1/chat/completions
```

The 404 URL `https://api.deepseek.com/v1/v1/chat/completions` proves
the path-doubling hypothesis from R110-2. Goose's internal client
appends `/v1` to the OPENAI_HOST value, and because the value already
ends with `/v1`, the result has `/v1/v1/`.

## Conclusion

R110-3 is correct:

1. **Reverting OPENAI_HOST** in `.state/goose-defaults.env` and
   `.env.example` to `https://api.deepseek.com` (without /v1) restores
   the working configuration.
2. **Keeping the model change** (deepseek-chat → deepseek-v4-flash) is
   still correct — the model is what made scenario A succeed in
   R110-1 evidence, and it still works in R110-3.
3. **The skill gotcha** that R110-1 misread (gotcha #3b in
   `goose-cli-e2e-testing`) needs to be patched to clarify: goose
   1.44 appends /v1 internally, do NOT add /v1 manually.

## Files in this evidence

- `README.md` — this file
- `evidence/A-r1103-no-v1-goose-run.log` — 13647 bytes, success
- `evidence/B-r1101-with-v1-control-run.log` — 717 bytes, 404 with
  double-/v1 URL proving the regression

## Audit-trail notes

- Both log files contain the full goose output, no redaction needed
  (no secrets, no PII, only the test workflow).
- `DEEPSEEK_API_KEY` was loaded from `mas-engineer/.env` (gitignored)
  and passed as env-var `OPENAI_API_KEY`. It is NOT in any log file.
- Pre-commit hook secret scan on this evidence: 0 hits.
- Byte-level scan: 0 sk-*, 0 ghp_*.

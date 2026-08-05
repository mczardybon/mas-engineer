---
name: hermes-write-file-mcp-stub-trap
description: Diagnose & workaround when write_file reports success but file is empty/missing on disk
---

# write_file MCP Stub Trap

## Symptom
`write_file(path=..., content=...)` returns `{bytes_written: N, success: True}` but:
- `ls -la <path>` shows the file does NOT exist
- OR the file exists but is empty / partial
- OR follow-up `read_file` shows old content

Hit at least 2x in 2026-08-04 session:
- `mas-engineer/tools/dev_category_drift.py` (155 lines, 5.4KB content reported as written, file did not exist)
- `mas-engineer/tools/dev_category_drift.README.md` (3371 bytes reported, file did not exist)

Both times the file was multi-line, code-heavy content. May correlate with content size or special chars.

## Diagnose
After EVERY write_file call:
```bash
ls -la <path> 2>&1
wc -c <path> 2>&1
```
If file missing or wrong size -> stub hit. Treat write_file as UNTRUSTED for this content.

## Workaround
Use terminal with heredoc (NOT single-quoted `cat > file <<EOF` for content with `$` / backticks — use `<<'EOF'` single-quoted to disable interpolation):
```bash
cat > /path/to/file <<'EOF'
... content ...
EOF
chmod +x /path/to/file   # if executable script
```

Verify after:
```bash
ls -la /path/to/file
wc -c /path/to/file
head -3 /path/to/file
```

## When write_file IS reliable
Single-line short content, plain text, no embedded special chars. For multi-line code or markdown, prefer heredoc first time.

## Pitfall
If you `git add <file>` immediately after a silent-fail write_file, git will succeed (file may be empty or absent depending on stub behavior). The error surfaces only at `git commit` (if file gone) or at pre-push-validator (if content is empty/wrong). Catch it at write time with the diagnose step above.

## Related
- `mas-engineer-verification-theater-guard` -- same family of "tool says success but reality differs" traps
- VT-WARN+R110-24/30 in memory -- pre-existing pattern of display-vs-reality drift

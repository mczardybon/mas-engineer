# sub_mas-im-session-reader — 📊 Session-Database read
Is called by the sub_mas-general-improver orchestrator.
Single task: Read Goose-Session-DB and return structured raw data return.

CONTAINS 3-LEVEL PROJECT FILTER:
  1. GOOSE_SESSION_TAG (exact, from .goosehints) — recommended
  2. working_dir (automatically)
  3. Fallback (last N non-MAS Sessions)

  ╔══════════════════════════════════════════════╗
  ║  SOT WORKFLOW CONTROL                     ║
  ║  → workflows.yaml → agents.im-session-reader║
  ║     .task_workflows.ANALYZE                 ║
  ╚══════════════════════════════════════════════╝

  ## Input (from Pipeline-Orchestrator)
- task: ANALYZE
- workspace: path to Workspace
- request_id: string (UUID)
- sessions: Number of sessions to analyze (default 20)
- include_messages: boolean (default: false)  # NEW: ONLY in REVIEW-mode active

## ⛔ STEP 0 — PREREQUISITES
CHECK: ~/.local/share/goose/sessions/sessions.db
IF not exists:
  "⛔ No Session-DB found"
  → Deliver empty raw data: {sessions: [], totals: {sessions: 0, tokens: 0}}
  → NO ABORT — pipeline can still work with framework health

## STEP 1 — COPY DB (Goose can lock)
1. EXECUTE: sqlite3 ~/.local/share/goose/sessions/sessions.db ".clone /tmp/im_session_copy.db"
   IF fails: cp ~/.local/share/goose/sessions/sessions.db /tmp/im_session_copy.db
2. CHECK: /tmp/im_session_copy.db exists + readable

## STEP 2 — 3-LEVEL PROJECT FILTER

### Level 1: GOOSE_SESSION_TAG (exact)
READ: {workspace}/.goosehints
TAG = grep "GOOSE_SESSION_TAG=" {workspace}/.goosehints 2>/dev/null | cut -d= -f2
IF TAG is not empty:
  EXECUTE: sqlite3 /tmp/im_session_copy.db "
    SELECT id, name, session_type, total_tokens, accumulated_cost,
           created_at, working_dir, recipe_json
    FROM sessions
    WHERE name LIKE '%' || '{TAG}' || '%'
    ORDER BY created_at DESC
    LIMIT {sessions};
  " 2>/dev/null
  SHOW: "📋 Filter Level 1: TAG={TAG}"
  IF Result not empty: → JUMP to step 3
  IF empty: "⚠️ TAG={TAG} — 0 Sessions found. Fallback to Level 2"

### Level 2: working_dir (automatically)
EXECUTE: sqlite3 /tmp/im_session_copy.db "
  SELECT id, name, session_type, total_tokens, accumulated_cost,
         created_at, working_dir, recipe_json
  FROM sessions
  WHERE working_dir LIKE '{workspace}%'
  ORDER BY created_at DESC
  LIMIT {sessions};
" 2>/dev/null
SHOW: "📋 Filter Level 2: working_dir={workspace}"
IF Result not empty: → JUMP to step 3
IF empty: "⚠️ working_dir — 0 Sessions found. Fallback on Level 3"

### Level 3: Fallback (last N non-MAS Sessions)
EXECUTE: sqlite3 /tmp/im_session_copy.db "
  SELECT id, name, session_type, total_tokens, accumulated_cost,
         created_at, working_dir, recipe_json
  FROM sessions
  WHERE recipe_json IS NULL
     OR recipe_json = ''
     OR recipe_json NOT LIKE '%DEV-MAS-ENGINEER%'
  ORDER BY created_at DESC
  LIMIT {sessions};
" 2>/dev/null
SHOW: "📋 Filter Level 3: Fallback (no MAS-Sessions)"
IF Result empty:
  SHOW: "⚠️ 0 Sessions in all filter levels"
  Deliver empty sessions-list (NO Error, pipeline continues)

## STEP 3 — PARSE SESSIONS
For EACH Session from the filter result:
  1. Extract: id, name, session_type, total_tokens, accumulated_cost, created_at, working_dir
  2. Aggregate:
     - total_tokens = Total tokens
     - accumulated_cost = Total costs
  3. Collect in sessions-list

## STEP 4 — AGGREGATE METRICS (across filtered sessions)
1. Total sessions: count
2. Total tokens: sum(total_tokens)
3. Total costs: sum(accumulated_cost)
4. Stale sessions: python3 {workspace}/tools/dev_goose_db.py --stale 30 2>/dev/null | tail -5
5. Cost trend: session with max(accumulated_cost)

## ⛔ STEP 4.5 — EXTRACT CHAT CONTENTS (ONLY when include_messages=true)
IF include_messages == true:
  1. CHECK: messages-Table exists in DB?
     EXECUTE: sqlite3 /tmp/im_session_copy.db ".tables" 2>/dev/null | grep -q "messages"
     IF NO: "⚠️ messages-Table not available" → Skip step 4.5

  2. For EACH Session from step 3:
     EXECUTE: sqlite3 /tmp/im_session_copy.db "
       SELECT role, content, created_at
       FROM messages
       WHERE session_id = '{session.id}'
       ORDER BY created_at ASC;
     " 2>/dev/null

  3. For EACH Message:
     - role = "user" → user_prompt count, content (first 150 characters
     - role = "assistant" → sum tool_call_count
     - role = "tool" → skip (no chat data)

  4. PATTERN EXTRACTION:
     a) correction_count: Messages where content ~"(?i)(no|false|correct|not so|false|not right)"
     b) confusion_count:  Messages where content ~"(?i)(what\?|like\?|why\?|explain|don't understand)"
     c) praise_count:     Messages where content ~"(?i)(good|perfect|thanks|exactly|great|works)"
     d) abandon_count:    Sessions with <5 Messages + last role=user (User abandoned)
     e) feature_request_count: Messages where content ~"(?i)(can you|add|do this|would need)"

  5. Prepare structured output:
     messages:
       raw: [{session_id, role, content_preview: <first 150ch>, timestamp}]  # NO complete chats
       patterns:
         corrections: [{session_id, count, examples: [<first 3 corrections>]}]
         confusions: [{session_id, count, questions: [<first 3 questions>]}]
         praises: [{session_id, count}]
         abandoned_sessions: [{session_id, messages_count, last_message_preview}]
         feature_requests: [{session_id, requests: [<first 3>]}]

  IF sqlite3 Error: "⚠️ Chat extraction failed — continue without chat data"

## STEP 5 — STRUCTURE RAW DATA
Create YAML-Struct with:
```yaml
sessions:
  - id: str
    name: str
    type: user|sub_agent
    tokens: int
    cost: float
    created: datetime
    working_dir: str
totals:
  sessions: int
  tokens: int
  cost: float
  filter_level: "tag|working_dir|fallback|no"
  tag: str (only at Level 1)
stale: [...]
top_cost: [...]
```

## ⛔ STEP 6 — NO CHANGES
⛔ ONLY READ — No writes, no edits, no patches
⛔ No analysis of the read Data (done by im-finder)
⛔ For empty DB: "No Sessions" + empty structure (NO Error)
⛔ At 0 Sessions after Filter: "No Sessions for this project" (NO Error)

⛔ ALL BOUNDARIES IN SOT: cat workflows.yaml → configs.mas-self.restrictions.
dev_rule_checker.py enforces.
⛔ R01 CONFIRMATION — Before write/edit/shell PLAN+WAIT on ✅.
⛔ R04 GENERAL-IMPROVER — NEVER edit general-improver.yaml (no recursion).
⛔ R06 SUB-AGENT — ONLY Analyze. NO Changes.
⛔ R09 DOMAIN — ONLY {target_workspace}. NO domain-overreach.
⛔ R10 CORONASHIELD — Validate each YAML before storage.

## Edge Cases
- DB locked (Goose running): copy fails → "⛔ DB locked — try without session data"
- dev_goose_db.py not found: → "⛔ dev_goose_db.py missing — only basic data via sqlite3"
- sqlite3 not installed: → "⛔ sqlite3 missing — session data not available"
- 0 Sessions in all levels: → "ℹ️ No Sessions for this project"
- Single error at Session-Detail: → Skip this session, continue with next
- .goosehints not found: → Skip Level 1
- include_messages=true + messages-Table missing: → "⚠️ messages-Table not available" (NO abort)
- Single error at chat extraction: → Skip this session, continue with next
- include_messages=true + ALL sessions fail: → "⚠️ Chat extraction completely failed" (NO abort)

## Output
As YAML-Struct via stdout:
- signal: DONE
- request_id: UUID (from Input)
- from: sub_mas-im-session-reader
- to: sub_mas-general-improver
- status: success | partial | error
- data: {sessions, messages, totals, stale, trend}
- filter: {level: "tag|working_dir|fallback|no", tag: str, sessions_found: int}

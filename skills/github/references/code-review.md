# Code Review

1|---
2|name: github-code-review
3|description: "Review PRs: diffs, inline comments via gh or REST."
4|version: 1.1.0
5|author: Hermes Agent
6|license: MIT
7|platforms: [linux, macos, windows]
8|metadata:
9|  hermes:
10|    tags: [GitHub, Code-Review, Pull-Requests, Git, Quality]
11|    related_skills: [github-auth, github-pr-workflow]
12|---
13|
14|# GitHub Code Review
15|
16|Perform code reviews on local changes before pushing, or review open PRs on GitHub. Most of this skill uses plain `git` — the `gh`/`curl` split only matters for PR-level interactions.
17|
18|## Prerequisites
19|
20|- Authenticated with GitHub (see `github-auth` skill)
21|- Inside a git repository
22|
23|### Setup (for PR interactions)
24|
25|```bash
26|if command -v gh &>/dev/null && gh auth status &>/dev/null; then
27|  AUTH="gh"
28|else
29|  AUTH="git"
30|  if [ -z "$GITHUB_TOKEN" ]; then
31|    if _hermes_env="${HERMES_HOME:-$HOME/.hermes}/.env"; [ -f "$_hermes_env" ] && grep -q "^GITHUB_TOKEN=" "$_hermes_env"; then
32|      GITHUB_TOKEN=$(grep "^GITHUB_TOKEN=" "$_hermes_env" | head -1 | cut -d= -f2 | tr -d '\n\r')
33|    elif grep -q "github.com" ~/.git-credentials 2>/dev/null; then
34|      GITHUB_TOKEN=$(grep "github.com" ~/.git-credentials 2>/dev/null | head -1 | sed 's|https://[^:]*:\([^@]*\)@.*|\1|')
35|    fi
36|  fi
37|fi
38|
39|REMOTE_URL=$(git remote get-url origin)
40|OWNER_REPO=$(echo "$REMOTE_URL" | sed -E 's|.*github\.com[:/]||; s|\.git$||')
41|OWNER=$(echo "$OWNER_REPO" | cut -d/ -f1)
42|REPO=$(echo "$OWNER_REPO" | cut -d/ -f2)
43|```
44|
45|---
46|
47|## 1. Reviewing Local Changes (Pre-Push)
48|
49|This is pure `git` — works everywhere, no API needed.
50|
51|### Get the Diff
52|
53|```bash
54|# Staged changes (what would be committed)
55|git diff --staged
56|
57|# All changes vs main (what a PR would contain)
58|git diff main...HEAD
59|
60|# File names only
61|git diff main...HEAD --name-only
62|
63|# Stat summary (insertions/deletions per file)
64|git diff main...HEAD --stat
65|```
66|
67|### Review Strategy
68|
69|1. **Get the big picture first:**
70|
71|```bash
72|git diff main...HEAD --stat
73|git log main..HEAD --oneline
74|```
75|
76|2. **Review file by file** — use `read_file` on changed files for full context, and the diff to see what changed:
77|
78|```bash
79|git diff main...HEAD -- src/auth/login.py
80|```
81|
82|3. **Check for common issues:**
83|
84|```bash
85|# Debug statements, TODOs, console.logs left behind
86|git diff main...HEAD | grep -n "print(\|console\.log\|TODO\|FIXME\|HACK\|XXX\|debugger"
87|
88|# Large files accidentally staged
89|git diff main...HEAD --stat | sort -t'|' -k2 -rn | head -10
90|
91|# Secrets or credential patterns
92|git diff main...HEAD | grep -in "password\|secret\|api_key\|token.*=\|private_key"
93|
94|# Merge conflict markers
95|git diff main...HEAD | grep -n "<<<<<<\|>>>>>>\|======="
96|```
97|
98|4. **Present structured feedback** to the user.
99|
100|### Review Output Format
101|
102|When reviewing local changes, present findings in this structure:
103|
104|```
105|## Code Review Summary
106|
107|### Critical
108|- **src/auth.py:45** — SQL injection: user input passed directly to query.
109|  Suggestion: Use parameterized queries.
110|
111|### Warnings
112|- **src/models/user.py:23** — Password stored in plaintext. Use bcrypt or argon2.
113|- **src/api/routes.py:112** — No rate limiting on login endpoint.
114|
115|### Suggestions
116|- **src/utils/helpers.py:8** — Duplicates logic in `src/core/utils.py:34`. Consolidate.
117|- **tests/test_auth.py** — Missing edge case: expired token test.
118|
119|### Looks Good
120|- Clean separation of concerns in the middleware layer
121|- Good test coverage for the happy path
122|```
123|
124|---
125|
126|## 2. Reviewing a Pull Request on GitHub
127|
128|### View PR Details
129|
130|**With gh:**
131|
132|```bash
133|gh pr view 123
134|gh pr diff 123
135|gh pr diff 123 --name-only
136|```
137|
138|**With git + curl:**
139|
140|```bash
141|PR_NUMBER=123
142|
143|# Get PR details
144|curl -s \
145|  -H "Authorization: token $GITHUB_TOKEN" \
146|  https://api.github.com/repos/$OWNER/$REPO/pulls/$PR_NUMBER \
147|  | python3 -c "
148|import sys, json
149|pr = json.load(sys.stdin)
150|print(f\"Title: {pr['title']}\")
151|print(f\"Author: {pr['user']['login']}\")
152|print(f\"Branch: {pr['head']['ref']} -> {pr['base']['ref']}\")
153|print(f\"State: {pr['state']}\")
154|print(f\"Body:\n{pr['body']}\")"
155|
156|# List changed files
157|curl -s \
158|  -H "Authorization: token $GITHUB_TOKEN" \
159|  https://api.github.com/repos/$OWNER/$REPO/pulls/$PR_NUMBER/files \
160|  | python3 -c "
161|import sys, json
162|for f in json.load(sys.stdin):
163|    print(f\"{f['status']:10} +{f['additions']:-4} -{f['deletions']:-4}  {f['filename']}\")"
164|```
165|
166|### Check Out PR Locally for Full Review
167|
168|This works with plain `git` — no `gh` needed:
169|
170|```bash
171|# Fetch the PR branch and check it out
172|git fetch origin pull/123/head:pr-123
173|git checkout pr-123
174|
175|# Now you can use read_file, search_files, run tests, etc.
176|
177|# View diff against the base branch
178|git diff main...pr-123
179|```
180|
181|**With gh (shortcut):**
182|
183|```bash
184|gh pr checkout 123
185|```
186|
187|### Leave Comments on a PR
188|
189|**General PR comment — with gh:**
190|
191|```bash
192|gh pr comment 123 --body "Overall looks good, a few suggestions below."
193|```
194|
195|**General PR comment — with curl:**
196|
197|```bash
198|curl -s -X POST \
199|  -H "Authorization: token $GITHUB_TOKEN" \
200|  https://api.github.com/repos/$OWNER/$REPO/issues/$PR_NUMBER/comments \
201|  -d '{"body": "Overall looks good, a few suggestions below."}'
202|```
203|
204|### Leave Inline Review Comments
205|
206|**Single inline comment — with gh (via API):**
207|
208|```bash
209|HEAD_SHA=$(gh pr view 123 --json headRefOid --jq '.headRefOid')
210|
211|gh api repos/$OWNER/$REPO/pulls/123/comments \
212|  --method POST \
213|  -f body="This could be simplified with a list comprehension." \
214|  -f path="src/auth/login.py" \
215|  -f commit_id="$HEAD_SHA" \
216|  -f line=45 \
217|  -f side="RIGHT"
218|```
219|
220|**Single inline comment — with curl:**
221|
222|```bash
223|# Get the head commit SHA
224|HEAD_SHA=$(curl -s \
225|  -H "Authorization: token $GITHUB_TOKEN" \
226|  https://api.github.com/repos/$OWNER/$REPO/pulls/$PR_NUMBER \
227|  | python3 -c "import sys,json; print(json.load(sys.stdin)['head']['sha'])")
228|
229|curl -s -X POST \
230|  -H "Authorization: token $GITHUB_TOKEN" \
231|  https://api.github.com/repos/$OWNER/$REPO/pulls/$PR_NUMBER/comments \
232|  -d "{
233|    \"body\": \"This could be simplified with a list comprehension.\",
234|    \"path\": \"src/auth/login.py\",
235|    \"commit_id\": \"$HEAD_SHA\",
236|    \"line\": 45,
237|    \"side\": \"RIGHT\"
238|  }"
239|```
240|
241|### Submit a Formal Review (Approve / Request Changes)
242|
243|**With gh:**
244|
245|```bash
246|gh pr review 123 --approve --body "LGTM!"
247|gh pr review 123 --request-changes --body "See inline comments."
248|gh pr review 123 --comment --body "Some suggestions, nothing blocking."
249|```
250|
251|**With curl — multi-comment review submitted atomically:**
252|
253|```bash
254|HEAD_SHA=$(curl -s \
255|  -H "Authorization: token $GITHUB_TOKEN" \
256|  https://api.github.com/repos/$OWNER/$REPO/pulls/$PR_NUMBER \
257|  | python3 -c "import sys,json; print(json.load(sys.stdin)['head']['sha'])")
258|
259|curl -s -X POST \
260|  -H "Authorization: token $GITHUB_TOKEN" \
261|  https://api.github.com/repos/$OWNER/$REPO/pulls/$PR_NUMBER/reviews \
262|  -d "{
263|    \"commit_id\": \"$HEAD_SHA\",
264|    \"event\": \"COMMENT\",
265|    \"body\": \"Code review from Hermes Agent\",
266|    \"comments\": [
267|      {\"path\": \"src/auth.py\", \"line\": 45, \"body\": \"Use parameterized queries to prevent SQL injection.\"},
268|      {\"path\": \"src/models/user.py\", \"line\": 23, \"body\": \"Hash passwords with bcrypt before storing.\"},
269|      {\"path\": \"tests/test_auth.py\", \"line\": 1, \"body\": \"Add test for expired token edge case.\"}
270|    ]
271|  }"
272|```
273|
274|Event values: `"APPROVE"`, `"REQUEST_CHANGES"`, `"COMMENT"`
275|
276|The `line` field refers to the line number in the *new* version of the file. For deleted lines, use `"side": "LEFT"`.
277|
278|---
279|
280|## 3. Review Checklist
281|
282|When performing a code review (local or PR), systematically check:
283|
284|### Correctness
285|- Does the code do what it claims?
286|- Edge cases handled (empty inputs, nulls, large data, concurrent access)?
287|- Error paths handled gracefully?
288|
289|### Security
290|- No hardcoded secrets, credentials, or API keys
291|- Input validation on user-facing inputs
292|- No SQL injection, XSS, or path traversal
293|- Auth/authz checks where needed
294|
295|### Code Quality
296|- Clear naming (variables, functions, classes)
297|- No unnecessary complexity or premature abstraction
298|- DRY — no duplicated logic that should be extracted
299|- Functions are focused (single responsibility)
300|
301|### Testing
302|- New code paths tested?
303|- Happy path and error cases covered?
304|- Tests readable and maintainable?
305|
306|### Performance
307|- No N+1 queries or unnecessary loops
308|- Appropriate caching where beneficial
309|- No blocking operations in async code paths
310|
311|### Documentation
312|- Public APIs documented
313|- Non-obvious logic has comments explaining "why"
314|- README updated if behavior changed
315|
316|---
317|
318|## 4. Pre-Push Review Workflow
319|
320|When the user asks you to "review the code" or "check before pushing":
321|
322|1. `git diff main...HEAD --stat` — see scope of changes
323|2. `git diff main...HEAD` — read the full diff
324|3. For each changed file, use `read_file` if you need more context
325|4. Apply the checklist above
326|5. Present findings in the structured format (Critical / Warnings / Suggestions / Looks Good)
327|6. If critical issues found, offer to fix them before the user pushes
328|
329|---
330|
331|## 5. PR Review Workflow (End-to-End)
332|
333|When the user asks you to "review PR #N", "look at this PR", or gives you a PR URL, follow this recipe:
334|
335|### Step 1: Set up environment
336|
337|```bash
338|source "${HERMES_HOME:-$HOME/.hermes}/skills/github/github-auth/scripts/gh-env.sh"
339|# Or run the inline setup block from the top of this skill
340|```
341|
342|### Step 2: Gather PR context
343|
344|Get the PR metadata, description, and list of changed files to understand scope before diving into code.
345|
346|**With gh:**
347|```bash
348|gh pr view 123
349|gh pr diff 123 --name-only
350|gh pr checks 123
351|```
352|
353|**With curl:**
354|```bash
355|PR_NUMBER=123
356|
357|# PR details (title, author, description, branch)
358|curl -s -H "Authorization: token $GITHUB_TOKEN" \
359|  https://api.github.com/repos/$GH_OWNER/$GH_REPO/pulls/$PR_NUMBER
360|
361|# Changed files with line counts
362|curl -s -H "Authorization: token $GITHUB_TOKEN" \
363|  https://api.github.com/repos/$GH_OWNER/$GH_REPO/pulls/$PR_NUMBER/files
364|```
365|
366|### Step 3: Check out the PR locally
367|
368|This gives you full access to `read_file`, `search_files`, and the ability to run tests.
369|
370|```bash
371|git fetch origin pull/$PR_NUMBER/head:pr-$PR_NUMBER
372|git checkout pr-$PR_NUMBER
373|```
374|
375|### Step 4: Read the diff and understand changes
376|
377|```bash
378|# Full diff against the base branch
379|git diff main...HEAD
380|
381|# Or file-by-file for large PRs
382|git diff main...HEAD --name-only
383|# Then for each file:
384|git diff main...HEAD -- path/to/file.py
385|```
386|
387|For each changed file, use `read_file` to see full context around the changes — diffs alone can miss issues visible only with surrounding code.
388|
389|### Step 5: Run automated checks locally (if applicable)
390|
391|```bash
392|# Run tests if there's a test suite
393|python -m pytest 2>&1 | tail -20
394|# or: npm test, cargo test, go test ./..., etc.
395|
396|# Run linter if configured
397|ruff check . 2>&1 | head -30
398|# or: eslint, clippy, etc.
399|```
400|
401|### Step 6: Apply the review checklist (Section 3)
402|
403|Go through each category: Correctness, Security, Code Quality, Testing, Performance, Documentation.
404|
405|### Step 7: Post the review to GitHub
406|
407|Collect your findings and submit them as a formal review with inline comments.
408|
409|**With gh:**
410|```bash
411|# If no issues — approve
412|gh pr review $PR_NUMBER --approve --body "Reviewed by Hermes Agent. Code looks clean — good test coverage, no security concerns."
413|
414|# If issues found — request changes with inline comments
415|gh pr review $PR_NUMBER --request-changes --body "Found a few issues — see inline comments."
416|```
417|
418|**With curl — atomic review with multiple inline comments:**
419|```bash
420|HEAD_SHA=$(curl -s -H "Authorization: token $GITHUB_TOKEN" \
421|  https://api.github.com/repos/$GH_OWNER/$GH_REPO/pulls/$PR_NUMBER \
422|  | python3 -c "import sys,json; print(json.load(sys.stdin)['head']['sha'])")
423|
424|# Build the review JSON — event is APPROVE, REQUEST_CHANGES, or COMMENT
425|curl -s -X POST \
426|  -H "Authorization: token $GITHUB_TOKEN" \
427|  https://api.github.com/repos/$GH_OWNER/$GH_REPO/pulls/$PR_NUMBER/reviews \
428|  -d "{
429|    \"commit_id\": \"$HEAD_SHA\",
430|    \"event\": \"REQUEST_CHANGES\",
431|    \"body\": \"## Hermes Agent Review\n\nFound 2 issues, 1 suggestion. See inline comments.\",
432|    \"comments\": [
433|      {\"path\": \"src/auth.py\", \"line\": 45, \"body\": \"🔴 **Critical:** User input passed directly to SQL query — use parameterized queries.\"},
434|      {\"path\": \"src/models.py\", \"line\": 23, \"body\": \"⚠️ **Warning:** Password stored without hashing.\"},
435|      {\"path\": \"src/utils.py\", \"line\": 8, \"body\": \"💡 **Suggestion:** This duplicates logic in core/utils.py:34.\"}
436|    ]
437|  }"
438|```
439|
440|### Step 8: Also post a summary comment
441|
442|In addition to inline comments, leave a top-level summary so the PR author gets the full picture at a glance. Use the review output format from `references/review-output-template.md`.
443|
444|**With gh:**
445|```bash
446|gh pr comment $PR_NUMBER --body "$(cat <<'EOF'
447|## Code Review Summary
448|
449|**Verdict: Changes Requested** (2 issues, 1 suggestion)
450|
451|### 🔴 Critical
452|- **src/auth.py:45** — SQL injection vulnerability
453|
454|### ⚠️ Warnings
455|- **src/models.py:23** — Plaintext password storage
456|
457|### 💡 Suggestions
458|- **src/utils.py:8** — Duplicated logic, consider consolidating
459|
460|### ✅ Looks Good
461|- Clean API design
462|- Good error handling in the middleware layer
463|
464|---
465|*Reviewed by Hermes Agent*
466|EOF
467|)"
468|```
469|
470|### Step 9: Clean up
471|
472|```bash
473|git checkout main
474|git branch -D pr-$PR_NUMBER
475|```
476|
477|### Decision: Approve vs Request Changes vs Comment
478|
479|- **Approve** — no critical or warning-level issues, only minor suggestions or all clear
480|- **Request Changes** — any critical or warning-level issue that should be fixed before merge
481|- **Comment** — observations and suggestions, but nothing blocking (use when you're unsure or the PR is a draft)
482|
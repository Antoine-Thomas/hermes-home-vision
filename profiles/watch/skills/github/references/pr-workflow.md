# Pr Workflow

1|---
2|name: github-pr-workflow
3|description: "GitHub PR lifecycle: branch, commit, open, CI, merge."
4|version: 1.1.0
5|author: Hermes Agent
6|license: MIT
7|platforms: [linux, macos, windows]
8|metadata:
9|  hermes:
10|    tags: [GitHub, Pull-Requests, CI/CD, Git, Automation, Merge]
11|    related_skills: [github-auth, github-code-review]
12|---
13|
14|# GitHub Pull Request Workflow
15|
16|Complete guide for managing the PR lifecycle. Each section shows the `gh` way first, then the `git` + `curl` fallback for machines without `gh`.
17|
18|## Prerequisites
19|
20|- Authenticated with GitHub (see `github-auth` skill)
21|- Inside a git repository with a GitHub remote
22|
23|### Quick Auth Detection
24|
25|```bash
26|# Determine which method to use throughout this workflow
27|if command -v gh &>/dev/null && gh auth status &>/dev/null; then
28|  AUTH="gh"
29|else
30|  AUTH="git"
31|  # Ensure we have a token for API calls
32|  if [ -z "$GITHUB_TOKEN" ]; then
33|    if _hermes_env="${HERMES_HOME:-$HOME/.hermes}/.env"; [ -f "$_hermes_env" ] && grep -q "^GITHUB_TOKEN=" "$_hermes_env"; then
34|      GITHUB_TOKEN=$(grep "^GITHUB_TOKEN=" "$_hermes_env" | head -1 | cut -d= -f2 | tr -d '\n\r')
35|    elif grep -q "github.com" ~/.git-credentials 2>/dev/null; then
36|      GITHUB_TOKEN=$(grep "github.com" ~/.git-credentials 2>/dev/null | head -1 | sed 's|https://[^:]*:\([^@]*\)@.*|\1|')
37|    fi
38|  fi
39|fi
40|echo "Using: $AUTH"
41|```
42|
43|### Extracting Owner/Repo from the Git Remote
44|
45|Many `curl` commands need `owner/repo`. Extract it from the git remote:
46|
47|```bash
48|# Works for both HTTPS and SSH remote URLs
49|REMOTE_URL=$(git remote get-url origin)
50|OWNER_REPO=$(echo "$REMOTE_URL" | sed -E 's|.*github\.com[:/]||; s|\.git$||')
51|OWNER=$(echo "$OWNER_REPO" | cut -d/ -f1)
52|REPO=$(echo "$OWNER_REPO" | cut -d/ -f2)
53|echo "Owner: $OWNER, Repo: $REPO"
54|```
55|
56|---
57|
58|## 1. Branch Creation
59|
60|This part is pure `git` — identical either way:
61|
62|```bash
63|# Make sure you're up to date
64|git fetch origin
65|git checkout main && git pull origin main
66|
67|# Create and switch to a new branch
68|git checkout -b feat/add-user-authentication
69|```
70|
71|Branch naming conventions:
72|- `feat/description` — new features
73|- `fix/description` — bug fixes
74|- `refactor/description` — code restructuring
75|- `docs/description` — documentation
76|- `ci/description` — CI/CD changes
77|
78|## 2. Making Commits
79|
80|Use the agent's file tools (`write_file`, `patch`) to make changes, then commit:
81|
82|```bash
83|# Stage specific files
84|git add src/auth.py src/models/user.py tests/test_auth.py
85|
86|# Commit with a conventional commit message
87|git commit -m "feat: add JWT-based user authentication
88|
89|- Add login/register endpoints
90|- Add User model with password hashing
91|- Add auth middleware for protected routes
92|- Add unit tests for auth flow"
93|```
94|
95|Commit message format (Conventional Commits):
96|```
97|type(scope): short description
98|
99|Longer explanation if needed. Wrap at 72 characters.
100|```
101|
102|Types: `feat`, `fix`, `refactor`, `docs`, `test`, `ci`, `chore`, `perf`
103|
104|## 3. Pushing and Creating a PR
105|
106|### Push the Branch (same either way)
107|
108|```bash
109|git push -u origin HEAD
110|```
111|
112|### Create the PR
113|
114|**With gh:**
115|
116|```bash
117|gh pr create \
118|  --title "feat: add JWT-based user authentication" \
119|  --body "## Summary
120|- Adds login and register API endpoints
121|- JWT token generation and validation
122|
123|## Test Plan
124|- [ ] Unit tests pass
125|
126|Closes #42"
127|```
128|
129|Options: `--draft`, `--reviewer user1,user2`, `--label "enhancement"`, `--base develop`
130|
131|**With git + curl:**
132|
133|```bash
134|BRANCH=$(git branch --show-current)
135|
136|curl -s -X POST \
137|  -H "Authorization: token $GITHUB_TOKEN" \
138|  -H "Accept: application/vnd.github.v3+json" \
139|  https://api.github.com/repos/$OWNER/$REPO/pulls \
140|  -d "{
141|    \"title\": \"feat: add JWT-based user authentication\",
142|    \"body\": \"## Summary\nAdds login and register API endpoints.\n\nCloses #42\",
143|    \"head\": \"$BRANCH\",
144|    \"base\": \"main\"
145|  }"
146|```
147|
148|The response JSON includes the PR `number` — save it for later commands.
149|
150|To create as a draft, add `"draft": true` to the JSON body.
151|
152|## 4. Monitoring CI Status
153|
154|### Check CI Status
155|
156|**With gh:**
157|
158|```bash
159|# One-shot check
160|gh pr checks
161|
162|# Watch until all checks finish (polls every 10s)
163|gh pr checks --watch
164|```
165|
166|**With git + curl:**
167|
168|```bash
169|# Get the latest commit SHA on the current branch
170|SHA=$(git rev-parse HEAD)
171|
172|# Query the combined status
173|curl -s \
174|  -H "Authorization: token $GITHUB_TOKEN" \
175|  https://api.github.com/repos/$OWNER/$REPO/commits/$SHA/status \
176|  | python3 -c "
177|import sys, json
178|data = json.load(sys.stdin)
179|print(f\"Overall: {data['state']}\")
180|for s in data.get('statuses', []):
181|    print(f\"  {s['context']}: {s['state']} - {s.get('description', '')}\")"
182|
183|# Also check GitHub Actions check runs (separate endpoint)
184|curl -s \
185|  -H "Authorization: token $GITHUB_TOKEN" \
186|  https://api.github.com/repos/$OWNER/$REPO/commits/$SHA/check-runs \
187|  | python3 -c "
188|import sys, json
189|data = json.load(sys.stdin)
190|for cr in data.get('check_runs', []):
191|    print(f\"  {cr['name']}: {cr['status']} / {cr['conclusion'] or 'pending'}\")"
192|```
193|
194|### Poll Until Complete (git + curl)
195|
196|```bash
197|# Simple polling loop — check every 30 seconds, up to 10 minutes
198|SHA=$(git rev-parse HEAD)
199|for i in $(seq 1 20); do
200|  STATUS=$(curl -s \
201|    -H "Authorization: token $GITHUB_TOKEN" \
202|    https://api.github.com/repos/$OWNER/$REPO/commits/$SHA/status \
203|    | python3 -c "import sys,json; print(json.load(sys.stdin)['state'])")
204|  echo "Check $i: $STATUS"
205|  if [ "$STATUS" = "success" ] || [ "$STATUS" = "failure" ] || [ "$STATUS" = "error" ]; then
206|    break
207|  fi
208|  sleep 30
209|done
210|```
211|
212|## 5. Auto-Fixing CI Failures
213|
214|When CI fails, diagnose and fix. This loop works with either auth method.
215|
216|### Step 1: Get Failure Details
217|
218|**With gh:**
219|
220|```bash
221|# List recent workflow runs on this branch
222|gh run list --branch $(git branch --show-current) --limit 5
223|
224|# View failed logs
225|gh run view <RUN_ID> --log-failed
226|```
227|
228|**With git + curl:**
229|
230|```bash
231|BRANCH=$(git branch --show-current)
232|
233|# List workflow runs on this branch
234|curl -s \
235|  -H "Authorization: token $GITHUB_TOKEN" \
236|  "https://api.github.com/repos/$OWNER/$REPO/actions/runs?branch=$BRANCH&per_page=5" \
237|  | python3 -c "
238|import sys, json
239|runs = json.load(sys.stdin)['workflow_runs']
240|for r in runs:
241|    print(f\"Run {r['id']}: {r['name']} - {r['conclusion'] or r['status']}\")"
242|
243|# Get failed job logs (download as zip, extract, read)
244|RUN_ID=<run_id>
245|curl -s -L \
246|  -H "Authorization: token $GITHUB_TOKEN" \
247|  https://api.github.com/repos/$OWNER/$REPO/actions/runs/$RUN_ID/logs \
248|  -o /tmp/ci-logs.zip
249|cd /tmp && unzip -o ci-logs.zip -d ci-logs && cat ci-logs/*.txt
250|```
251|
252|### Step 2: Fix and Push
253|
254|After identifying the issue, use file tools (`patch`, `write_file`) to fix it:
255|
256|```bash
257|git add <fixed_files>
258|git commit -m "fix: resolve CI failure in <check_name>"
259|git push
260|```
261|
262|### Step 3: Verify
263|
264|Re-check CI status using the commands from Section 4 above.
265|
266|### Auto-Fix Loop Pattern
267|
268|When asked to auto-fix CI, follow this loop:
269|
270|1. Check CI status → identify failures
271|2. Read failure logs → understand the error
272|3. Use `read_file` + `patch`/`write_file` → fix the code
273|4. `git add . && git commit -m "fix: ..." && git push`
274|5. Wait for CI → re-check status
275|6. Repeat if still failing (up to 3 attempts, then ask the user)
276|
277|## 6. Merging
278|
279|**With gh:**
280|
281|```bash
282|# Squash merge + delete branch (cleanest for feature branches)
283|gh pr merge --squash --delete-branch
284|
285|# Enable auto-merge (merges when all checks pass)
286|gh pr merge --auto --squash --delete-branch
287|```
288|
289|**With git + curl:**
290|
291|```bash
292|PR_NUMBER=<number>
293|
294|# Merge the PR via API (squash)
295|curl -s -X PUT \
296|  -H "Authorization: token $GITHUB_TOKEN" \
297|  https://api.github.com/repos/$OWNER/$REPO/pulls/$PR_NUMBER/merge \
298|  -d "{
299|    \"merge_method\": \"squash\",
300|    \"commit_title\": \"feat: add user authentication (#$PR_NUMBER)\"
301|  }"
302|
303|# Delete the remote branch after merge
304|BRANCH=$(git branch --show-current)
305|git push origin --delete $BRANCH
306|
307|# Switch back to main locally
308|git checkout main && git pull origin main
309|git branch -d $BRANCH
310|```
311|
312|Merge methods: `"merge"` (merge commit), `"squash"`, `"rebase"`
313|
314|### Enable Auto-Merge (curl)
315|
316|```bash
317|# Auto-merge requires the repo to have it enabled in settings.
318|# This uses the GraphQL API since REST doesn't support auto-merge.
319|PR_NODE_ID=$(curl -s \
320|  -H "Authorization: token $GITHUB_TOKEN" \
321|  https://api.github.com/repos/$OWNER/$REPO/pulls/$PR_NUMBER \
322|  | python3 -c "import sys,json; print(json.load(sys.stdin)['node_id'])")
323|
324|curl -s -X POST \
325|  -H "Authorization: token $GITHUB_TOKEN" \
326|  https://api.github.com/graphql \
327|  -d "{\"query\": \"mutation { enablePullRequestAutoMerge(input: {pullRequestId: \\\"$PR_NODE_ID\\\", mergeMethod: SQUASH}) { clientMutationId } }\"}"
328|```
329|
330|## 7. Complete Workflow Example
331|
332|```bash
333|# 1. Start from clean main
334|git checkout main && git pull origin main
335|
336|# 2. Branch
337|git checkout -b fix/login-redirect-bug
338|
339|# 3. (Agent makes code changes with file tools)
340|
341|# 4. Commit
342|git add src/auth/login.py tests/test_login.py
343|git commit -m "fix: correct redirect URL after login
344|
345|Preserves the ?next= parameter instead of always redirecting to /dashboard."
346|
347|# 5. Push
348|git push -u origin HEAD
349|
350|# 6. Create PR (picks gh or curl based on what's available)
351|# ... (see Section 3)
352|
353|# 7. Monitor CI (see Section 4)
354|
355|# 8. Merge when green (see Section 6)
356|```
357|
358|## Useful PR Commands Reference
359|
360|| Action | gh | git + curl |
361||--------|-----|-----------|
362|| List my PRs | `gh pr list --author @me` | `curl -s -H "Authorization: token $GITHUB_TOKEN" "https://api.github.com/repos/$OWNER/$REPO/pulls?state=open"` |
363|| View PR diff | `gh pr diff` | `git diff main...HEAD` (local) or `curl -H "Accept: application/vnd.github.diff" ...` |
364|| Add comment | `gh pr comment N --body "..."` | `curl -X POST .../issues/N/comments -d '{"body":"..."}'` |
365|| Request review | `gh pr edit N --add-reviewer user` | `curl -X POST .../pulls/N/requested_reviewers -d '{"reviewers":["user"]}'` |
366|| Close PR | `gh pr close N` | `curl -X PATCH .../pulls/N -d '{"state":"closed"}'` |
367|| Check out someone's PR | `gh pr checkout N` | `git fetch origin pull/N/head:pr-N && git checkout pr-N` |
368|
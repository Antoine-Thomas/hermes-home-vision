# Issues

1|---
2|name: github-issues
3|description: "Create, triage, label, assign GitHub issues via gh or REST."
4|version: 1.1.0
5|author: Hermes Agent
6|license: MIT
7|platforms: [linux, macos, windows]
8|metadata:
9|  hermes:
10|    tags: [GitHub, Issues, Project-Management, Bug-Tracking, Triage]
11|    related_skills: [github-auth, github-pr-workflow]
12|---
13|
14|# GitHub Issues Management
15|
16|Create, search, triage, and manage GitHub issues. Each section shows `gh` first, then the `curl` fallback.
17|
18|## Prerequisites
19|
20|- Authenticated with GitHub (see `github-auth` skill)
21|- Inside a git repo with a GitHub remote, or specify the repo explicitly
22|
23|### Setup
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
47|## 1. Viewing Issues
48|
49|**With gh:**
50|
51|```bash
52|gh issue list
53|gh issue list --state open --label "bug"
54|gh issue list --assignee @me
55|gh issue list --search "authentication error" --state all
56|gh issue view 42
57|```
58|
59|**With curl:**
60|
61|```bash
62|# List open issues
63|curl -s \
64|  -H "Authorization: token $GITHUB_TOKEN" \
65|  "https://api.github.com/repos/$OWNER/$REPO/issues?state=open&per_page=20" \
66|  | python3 -c "
67|import sys, json
68|for i in json.load(sys.stdin):
69|    if 'pull_request' not in i:  # GitHub API returns PRs in /issues too
70|        labels = ', '.join(l['name'] for l in i['labels'])
71|        print(f\"#{i['number']:5}  {i['state']:6}  {labels:30}  {i['title']}\")"
72|
73|# Filter by label
74|curl -s \
75|  -H "Authorization: token $GITHUB_TOKEN" \
76|  "https://api.github.com/repos/$OWNER/$REPO/issues?state=open&labels=bug&per_page=20" \
77|  | python3 -c "
78|import sys, json
79|for i in json.load(sys.stdin):
80|    if 'pull_request' not in i:
81|        print(f\"#{i['number']}  {i['title']}\")"
82|
83|# View a specific issue
84|curl -s \
85|  -H "Authorization: token $GITHUB_TOKEN" \
86|  https://api.github.com/repos/$OWNER/$REPO/issues/42 \
87|  | python3 -c "
88|import sys, json
89|i = json.load(sys.stdin)
90|labels = ', '.join(l['name'] for l in i['labels'])
91|assignees = ', '.join(a['login'] for a in i['assignees'])
92|print(f\"#{i['number']}: {i['title']}\")
93|print(f\"State: {i['state']}  Labels: {labels}  Assignees: {assignees}\")
94|print(f\"Author: {i['user']['login']}  Created: {i['created_at']}\")
95|print(f\"\n{i['body']}\")"
96|
97|# Search issues
98|curl -s \
99|  -H "Authorization: token $GITHUB_TOKEN" \
100|  "https://api.github.com/search/issues?q=authentication+error+repo:$OWNER/$REPO" \
101|  | python3 -c "
102|import sys, json
103|for i in json.load(sys.stdin)['items']:
104|    print(f\"#{i['number']}  {i['state']:6}  {i['title']}\")"
105|```
106|
107|## 2. Creating Issues
108|
109|**With gh:**
110|
111|```bash
112|gh issue create \
113|  --title "Login redirect ignores ?next= parameter" \
114|  --body "## Description
115|After logging in, users always land on /dashboard.
116|
117|## Steps to Reproduce
118|1. Navigate to /settings while logged out
119|2. Get redirected to /login?next=/settings
120|3. Log in
121|4. Actual: redirected to /dashboard (should go to /settings)
122|
123|## Expected Behavior
124|Respect the ?next= query parameter." \
125|  --label "bug,backend" \
126|  --assignee "username"
127|```
128|
129|**With curl:**
130|
131|```bash
132|curl -s -X POST \
133|  -H "Authorization: token $GITHUB_TOKEN" \
134|  https://api.github.com/repos/$OWNER/$REPO/issues \
135|  -d '{
136|    "title": "Login redirect ignores ?next= parameter",
137|    "body": "## Description\nAfter logging in, users always land on /dashboard.\n\n## Steps to Reproduce\n1. Navigate to /settings while logged out\n2. Get redirected to /login?next=/settings\n3. Log in\n4. Actual: redirected to /dashboard\n\n## Expected Behavior\nRespect the ?next= query parameter.",
138|    "labels": ["bug", "backend"],
139|    "assignees": ["username"]
140|  }'
141|```
142|
143|### Bug Report Template
144|
145|```
146|## Bug Description
147|<What's happening>
148|
149|## Steps to Reproduce
150|1. <step>
151|2. <step>
152|
153|## Expected Behavior
154|<What should happen>
155|
156|## Actual Behavior
157|<What actually happens>
158|
159|## Environment
160|- OS: <os>
161|- Version: <version>
162|```
163|
164|### Feature Request Template
165|
166|```
167|## Feature Description
168|<What you want>
169|
170|## Motivation
171|<Why this would be useful>
172|
173|## Proposed Solution
174|<How it could work>
175|
176|## Alternatives Considered
177|<Other approaches>
178|```
179|
180|## 3. Managing Issues
181|
182|### Add/Remove Labels
183|
184|**With gh:**
185|
186|```bash
187|gh issue edit 42 --add-label "priority:high,bug"
188|gh issue edit 42 --remove-label "needs-triage"
189|```
190|
191|**With curl:**
192|
193|```bash
194|# Add labels
195|curl -s -X POST \
196|  -H "Authorization: token $GITHUB_TOKEN" \
197|  https://api.github.com/repos/$OWNER/$REPO/issues/42/labels \
198|  -d '{"labels": ["priority:high", "bug"]}'
199|
200|# Remove a label
201|curl -s -X DELETE \
202|  -H "Authorization: token $GITHUB_TOKEN" \
203|  https://api.github.com/repos/$OWNER/$REPO/issues/42/labels/needs-triage
204|
205|# List available labels in the repo
206|curl -s \
207|  -H "Authorization: token $GITHUB_TOKEN" \
208|  https://api.github.com/repos/$OWNER/$REPO/labels \
209|  | python3 -c "
210|import sys, json
211|for l in json.load(sys.stdin):
212|    print(f\"  {l['name']:30}  {l.get('description', '')}\")"
213|```
214|
215|### Assignment
216|
217|**With gh:**
218|
219|```bash
220|gh issue edit 42 --add-assignee username
221|gh issue edit 42 --add-assignee @me
222|```
223|
224|**With curl:**
225|
226|```bash
227|curl -s -X POST \
228|  -H "Authorization: token $GITHUB_TOKEN" \
229|  https://api.github.com/repos/$OWNER/$REPO/issues/42/assignees \
230|  -d '{"assignees": ["username"]}'
231|```
232|
233|### Commenting
234|
235|**With gh:**
236|
237|```bash
238|gh issue comment 42 --body "Investigated — root cause is in auth middleware. Working on a fix."
239|```
240|
241|**With curl:**
242|
243|```bash
244|curl -s -X POST \
245|  -H "Authorization: token $GITHUB_TOKEN" \
246|  https://api.github.com/repos/$OWNER/$REPO/issues/42/comments \
247|  -d '{"body": "Investigated — root cause is in auth middleware. Working on a fix."}'
248|```
249|
250|### Closing and Reopening
251|
252|**With gh:**
253|
254|```bash
255|gh issue close 42
256|gh issue close 42 --reason "not planned"
257|gh issue reopen 42
258|```
259|
260|**With curl:**
261|
262|```bash
263|# Close
264|curl -s -X PATCH \
265|  -H "Authorization: token $GITHUB_TOKEN" \
266|  https://api.github.com/repos/$OWNER/$REPO/issues/42 \
267|  -d '{"state": "closed", "state_reason": "completed"}'
268|
269|# Reopen
270|curl -s -X PATCH \
271|  -H "Authorization: token $GITHUB_TOKEN" \
272|  https://api.github.com/repos/$OWNER/$REPO/issues/42 \
273|  -d '{"state": "open"}'
274|```
275|
276|### Linking Issues to PRs
277|
278|Issues are automatically closed when a PR merges with the right keywords in the body:
279|
280|```
281|Closes #42
282|Fixes #42
283|Resolves #42
284|```
285|
286|To create a branch from an issue:
287|
288|**With gh:**
289|
290|```bash
291|gh issue develop 42 --checkout
292|```
293|
294|**With git (manual equivalent):**
295|
296|```bash
297|git checkout main && git pull origin main
298|git checkout -b fix/issue-42-login-redirect
299|```
300|
301|## 4. Issue Triage Workflow
302|
303|When asked to triage issues:
304|
305|1. **List untriaged issues:**
306|
307|```bash
308|# With gh
309|gh issue list --label "needs-triage" --state open
310|
311|# With curl
312|curl -s \
313|  -H "Authorization: token $GITHUB_TOKEN" \
314|  "https://api.github.com/repos/$OWNER/$REPO/issues?labels=needs-triage&state=open" \
315|  | python3 -c "
316|import sys, json
317|for i in json.load(sys.stdin):
318|    if 'pull_request' not in i:
319|        print(f\"#{i['number']}  {i['title']}\")"
320|```
321|
322|2. **Read and categorize** each issue (view details, understand the bug/feature)
323|
324|3. **Apply labels and priority** (see Managing Issues above)
325|
326|4. **Assign** if the owner is clear
327|
328|5. **Comment with triage notes** if needed
329|
330|## 5. Bulk Operations
331|
332|For batch operations, combine API calls with shell scripting:
333|
334|**With gh:**
335|
336|```bash
337|# Close all issues with a specific label
338|gh issue list --label "wontfix" --json number --jq '.[].number' | \
339|  xargs -I {} gh issue close {} --reason "not planned"
340|```
341|
342|**With curl:**
343|
344|```bash
345|# List issue numbers with a label, then close each
346|curl -s \
347|  -H "Authorization: token $GITHUB_TOKEN" \
348|  "https://api.github.com/repos/$OWNER/$REPO/issues?labels=wontfix&state=open" \
349|  | python3 -c "import sys,json; [print(i['number']) for i in json.load(sys.stdin)]" \
350|  | while read num; do
351|    curl -s -X PATCH \
352|      -H "Authorization: token $GITHUB_TOKEN" \
353|      https://api.github.com/repos/$OWNER/$REPO/issues/$num \
354|      -d '{"state": "closed", "state_reason": "not_planned"}'
355|    echo "Closed #$num"
356|  done
357|```
358|
359|## Quick Reference Table
360|
361|| Action | gh | curl endpoint |
362||--------|-----|--------------|
363|| List issues | `gh issue list` | `GET /repos/{o}/{r}/issues` |
364|| View issue | `gh issue view N` | `GET /repos/{o}/{r}/issues/N` |
365|| Create issue | `gh issue create ...` | `POST /repos/{o}/{r}/issues` |
366|| Add labels | `gh issue edit N --add-label ...` | `POST /repos/{o}/{r}/issues/N/labels` |
367|| Assign | `gh issue edit N --add-assignee ...` | `POST /repos/{o}/{r}/issues/N/assignees` |
368|| Comment | `gh issue comment N --body ...` | `POST /repos/{o}/{r}/issues/N/comments` |
369|| Close | `gh issue close N` | `PATCH /repos/{o}/{r}/issues/N` |
370|| Search | `gh issue list --search "..."` | `GET /search/issues?q=...` |
371|
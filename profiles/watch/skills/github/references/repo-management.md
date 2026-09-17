# Repo Management

1|---
2|name: github-repo-management
3|description: "Clone/create/fork repos; manage remotes, releases."
4|version: 1.1.0
5|author: Hermes Agent
6|license: MIT
7|platforms: [linux, macos, windows]
8|metadata:
9|  hermes:
10|    tags: [GitHub, Repositories, Git, Releases, Secrets, Configuration]
11|    related_skills: [github-auth, github-pr-workflow, github-issues]
12|---
13|
14|# GitHub Repository Management
15|
16|Create, clone, fork, configure, and manage GitHub repositories. Each section shows `gh` first, then the `git` + `curl` fallback.
17|
18|## Prerequisites
19|
20|- Authenticated with GitHub (see `github-auth` skill)
21|
22|### Setup
23|
24|```bash
25|if command -v gh &>/dev/null && gh auth status &>/dev/null; then
26|  AUTH="gh"
27|else
28|  AUTH="git"
29|  if [ -z "$GITHUB_TOKEN" ]; then
30|    if _hermes_env="${HERMES_HOME:-$HOME/.hermes}/.env"; [ -f "$_hermes_env" ] && grep -q "^GITHUB_TOKEN=" "$_hermes_env"; then
31|      GITHUB_TOKEN=$(grep "^GITHUB_TOKEN=" "$_hermes_env" | head -1 | cut -d= -f2 | tr -d '\n\r')
32|    elif grep -q "github.com" ~/.git-credentials 2>/dev/null; then
33|      GITHUB_TOKEN=$(grep "github.com" ~/.git-credentials 2>/dev/null | head -1 | sed 's|https://[^:]*:\([^@]*\)@.*|\1|')
34|    fi
35|  fi
36|fi
37|
38|# Get your GitHub username (needed for several operations)
39|if [ "$AUTH" = "gh" ]; then
40|  GH_USER=$(gh api user --jq '.login')
41|else
42|  GH_USER=$(curl -s -H "Authorization: token $GITHUB_TOKEN" https://api.github.com/user | python3 -c "import sys,json; print(json.load(sys.stdin)['login'])")
43|fi
44|```
45|
46|If you're inside a repo already:
47|
48|```bash
49|REMOTE_URL=$(git remote get-url origin)
50|OWNER_REPO=$(echo "$REMOTE_URL" | sed -E 's|.*github\.com[:/]||; s|\.git$||')
51|OWNER=$(echo "$OWNER_REPO" | cut -d/ -f1)
52|REPO=$(echo "$OWNER_REPO" | cut -d/ -f2)
53|```
54|
55|---
56|
57|## 1. Cloning Repositories
58|
59|Cloning is pure `git` — works identically either way:
60|
61|```bash
62|# Clone via HTTPS (works with credential helper or token-embedded URL)
63|git clone https://github.com/owner/repo-name.git
64|
65|# Clone into a specific directory
66|git clone https://github.com/owner/repo-name.git ./my-local-dir
67|
68|# Shallow clone (faster for large repos)
69|git clone --depth 1 https://github.com/owner/repo-name.git
70|
71|# Clone a specific branch
72|git clone --branch develop https://github.com/owner/repo-name.git
73|
74|# Clone via SSH (if SSH is configured)
75|git clone git@github.com:owner/repo-name.git
76|```
77|
78|**With gh (shorthand):**
79|
80|```bash
81|gh repo clone owner/repo-name
82|gh repo clone owner/repo-name -- --depth 1
83|```
84|
85|## 2. Creating Repositories
86|
87|**With gh:**
88|
89|```bash
90|# Create a public repo and clone it
91|gh repo create my-new-project --public --clone
92|
93|# Private, with description and license
94|gh repo create my-new-project --private --description "A useful tool" --license MIT --clone
95|
96|# Under an organization
97|gh repo create my-org/my-new-project --public --clone
98|
99|# From existing local directory
100|cd /path/to/existing/project
101|gh repo create my-project --source . --public --push
102|```
103|
104|**With git + curl:**
105|
106|```bash
107|# Create the remote repo via API
108|curl -s -X POST \
109|  -H "Authorization: token $GITHUB_TOKEN" \
110|  https://api.github.com/user/repos \
111|  -d '{
112|    "name": "my-new-project",
113|    "description": "A useful tool",
114|    "private": false,
115|    "auto_init": true,
116|    "license_template": "mit"
117|  }'
118|
119|# Clone it
120|git clone https://github.com/$GH_USER/my-new-project.git
121|cd my-new-project
122|
123|# -- OR -- push an existing local directory to the new repo
124|cd /path/to/existing/project
125|git init
126|git add .
127|git commit -m "Initial commit"
128|git remote add origin https://github.com/$GH_USER/my-new-project.git
129|git push -u origin main
130|```
131|
132|To create under an organization:
133|
134|```bash
135|curl -s -X POST \
136|  -H "Authorization: token $GITHUB_TOKEN" \
137|  https://api.github.com/orgs/my-org/repos \
138|  -d '{"name": "my-new-project", "private": false}'
139|```
140|
141|### From a Template
142|
143|**With gh:**
144|
145|```bash
146|gh repo create my-new-app --template owner/template-repo --public --clone
147|```
148|
149|**With curl:**
150|
151|```bash
152|curl -s -X POST \
153|  -H "Authorization: token $GITHUB_TOKEN" \
154|  https://api.github.com/repos/owner/template-repo/generate \
155|  -d '{"owner": "'"$GH_USER"'", "name": "my-new-app", "private": false}'
156|```
157|
158|## 3. Forking Repositories
159|
160|**With gh:**
161|
162|```bash
163|gh repo fork owner/repo-name --clone
164|```
165|
166|**With git + curl:**
167|
168|```bash
169|# Create the fork via API
170|curl -s -X POST \
171|  -H "Authorization: token $GITHUB_TOKEN" \
172|  https://api.github.com/repos/owner/repo-name/forks
173|
174|# Wait a moment for GitHub to create it, then clone
175|sleep 3
176|git clone https://github.com/$GH_USER/repo-name.git
177|cd repo-name
178|
179|# Add the original repo as "upstream" remote
180|git remote add upstream https://github.com/owner/repo-name.git
181|```
182|
183|### Keeping a Fork in Sync
184|
185|```bash
186|# Pure git — works everywhere
187|git fetch upstream
188|git checkout main
189|git merge upstream/main
190|git push origin main
191|```
192|
193|**With gh (shortcut):**
194|
195|```bash
196|gh repo sync $GH_USER/repo-name
197|```
198|
199|## 4. Repository Information
200|
201|**With gh:**
202|
203|```bash
204|gh repo view owner/repo-name
205|gh repo list --limit 20
206|gh search repos "machine learning" --language python --sort stars
207|```
208|
209|**With curl:**
210|
211|```bash
212|# View repo details
213|curl -s \
214|  -H "Authorization: token $GITHUB_TOKEN" \
215|  https://api.github.com/repos/$OWNER/$REPO \
216|  | python3 -c "
217|import sys, json
218|r = json.load(sys.stdin)
219|print(f\"Name: {r['full_name']}\")
220|print(f\"Description: {r['description']}\")
221|print(f\"Stars: {r['stargazers_count']}  Forks: {r['forks_count']}\")
222|print(f\"Default branch: {r['default_branch']}\")
223|print(f\"Language: {r['language']}\")"
224|
225|# List your repos
226|curl -s \
227|  -H "Authorization: token $GITHUB_TOKEN" \
228|  "https://api.github.com/user/repos?per_page=20&sort=updated" \
229|  | python3 -c "
230|import sys, json
231|for r in json.load(sys.stdin):
232|    vis = 'private' if r['private'] else 'public'
233|    print(f\"  {r['full_name']:40}  {vis:8}  {r.get('language', ''):10}  ★{r['stargazers_count']}\")"
234|
235|# Search repos
236|curl -s \
237|  "https://api.github.com/search/repositories?q=machine+learning+language:python&sort=stars&per_page=10" \
238|  | python3 -c "
239|import sys, json
240|for r in json.load(sys.stdin)['items']:
241|    print(f\"  {r['full_name']:40}  ★{r['stargazers_count']:6}  {r['description'][:60] if r['description'] else ''}\")"
242|```
243|
244|## 5. Repository Settings
245|
246|**With gh:**
247|
248|```bash
249|gh repo edit --description "Updated description" --visibility public
250|gh repo edit --enable-wiki=false --enable-issues=true
251|gh repo edit --default-branch main
252|gh repo edit --add-topic "machine-learning,python"
253|gh repo edit --enable-auto-merge
254|```
255|
256|**With curl:**
257|
258|```bash
259|curl -s -X PATCH \
260|  -H "Authorization: token $GITHUB_TOKEN" \
261|  https://api.github.com/repos/$OWNER/$REPO \
262|  -d '{
263|    "description": "Updated description",
264|    "has_wiki": false,
265|    "has_issues": true,
266|    "allow_auto_merge": true
267|  }'
268|
269|# Update topics
270|curl -s -X PUT \
271|  -H "Authorization: token $GITHUB_TOKEN" \
272|  -H "Accept: application/vnd.github.mercy-preview+json" \
273|  https://api.github.com/repos/$OWNER/$REPO/topics \
274|  -d '{"names": ["machine-learning", "python", "automation"]}'
275|```
276|
277|## 6. Branch Protection
278|
279|```bash
280|# View current protection
281|curl -s \
282|  -H "Authorization: token $GITHUB_TOKEN" \
283|  https://api.github.com/repos/$OWNER/$REPO/branches/main/protection
284|
285|# Set up branch protection
286|curl -s -X PUT \
287|  -H "Authorization: token $GITHUB_TOKEN" \
288|  https://api.github.com/repos/$OWNER/$REPO/branches/main/protection \
289|  -d '{
290|    "required_status_checks": {
291|      "strict": true,
292|      "contexts": ["ci/test", "ci/lint"]
293|    },
294|    "enforce_admins": false,
295|    "required_pull_request_reviews": {
296|      "required_approving_review_count": 1
297|    },
298|    "restrictions": null
299|  }'
300|```
301|
302|## 7. Secrets Management (GitHub Actions)
303|
304|**With gh:**
305|
306|```bash
307|gh secret set API_KEY --body "your-secret-value"
308|gh secret set SSH_KEY < ~/.ssh/id_rsa
309|gh secret list
310|gh secret delete API_KEY
311|```
312|
313|**With curl:**
314|
315|Secrets require encryption with the repo's public key — more involved via API:
316|
317|```bash
318|# Get the repo's public key for encrypting secrets
319|curl -s \
320|  -H "Authorization: token $GITHUB_TOKEN" \
321|  https://api.github.com/repos/$OWNER/$REPO/actions/secrets/public-key
322|
323|# Encrypt and set (requires Python with PyNaCl)
324|python3 -c "
325|from base64 import b64encode
326|from nacl import encoding, public
327|import json, sys
328|
329|# Get the public key
330|key_id = '<key_id_from_above>'
331|public_key = '<base64_key_from_above>'
332|
333|# Encrypt
334|sealed = public.SealedBox(
335|    public.PublicKey(public_key.encode('utf-8'), encoding.Base64Encoder)
336|).encrypt('your-secret-value'.encode('utf-8'))
337|print(json.dumps({
338|    'encrypted_value': b64encode(sealed).decode('utf-8'),
339|    'key_id': key_id
340|}))"
341|
342|# Then PUT the encrypted secret
343|curl -s -X PUT \
344|  -H "Authorization: token $GITHUB_TOKEN" \
345|  https://api.github.com/repos/$OWNER/$REPO/actions/secrets/API_KEY \
346|  -d '<output from python script above>'
347|
348|# List secrets (names only, values hidden)
349|curl -s \
350|  -H "Authorization: token $GITHUB_TOKEN" \
351|  https://api.github.com/repos/$OWNER/$REPO/actions/secrets \
352|  | python3 -c "
353|import sys, json
354|for s in json.load(sys.stdin)['secrets']:
355|    print(f\"  {s['name']:30}  updated: {s['updated_at']}\")"
356|```
357|
358|Note: For secrets, `gh secret set` is dramatically simpler. If setting secrets is needed and `gh` isn't available, recommend installing it for just that operation.
359|
360|## 8. Releases
361|
362|**With gh:**
363|
364|```bash
365|gh release create v1.0.0 --title "v1.0.0" --generate-notes
366|gh release create v2.0.0-rc1 --draft --prerelease --generate-notes
367|gh release create v1.0.0 ./dist/binary --title "v1.0.0" --notes "Release notes"
368|gh release list
369|gh release download v1.0.0 --dir ./downloads
370|```
371|
372|**With curl:**
373|
374|```bash
375|# Create a release
376|curl -s -X POST \
377|  -H "Authorization: token $GITHUB_TOKEN" \
378|  https://api.github.com/repos/$OWNER/$REPO/releases \
379|  -d '{
380|    "tag_name": "v1.0.0",
381|    "name": "v1.0.0",
382|    "body": "## Changelog\n- Feature A\n- Bug fix B",
383|    "draft": false,
384|    "prerelease": false,
385|    "generate_release_notes": true
386|  }'
387|
388|# List releases
389|curl -s \
390|  -H "Authorization: token $GITHUB_TOKEN" \
391|  https://api.github.com/repos/$OWNER/$REPO/releases \
392|  | python3 -c "
393|import sys, json
394|for r in json.load(sys.stdin):
395|    tag = r.get('tag_name', 'no tag')
396|    print(f\"  {tag:15}  {r['name']:30}  {'draft' if r['draft'] else 'published'}\")"
397|
398|# Upload a release asset (binary file)
399|RELEASE_ID=<id_from_create_response>
400|curl -s -X POST \
401|  -H "Authorization: token $GITHUB_TOKEN" \
402|  -H "Content-Type: application/octet-stream" \
403|  "https://uploads.github.com/repos/$OWNER/$REPO/releases/$RELEASE_ID/assets?name=binary-amd64" \
404|  --data-binary @./dist/binary-amd64
405|```
406|
407|## 9. GitHub Actions Workflows
408|
409|**With gh:**
410|
411|```bash
412|gh workflow list
413|gh run list --limit 10
414|gh run view <RUN_ID>
415|gh run view <RUN_ID> --log-failed
416|gh run rerun <RUN_ID>
417|gh run rerun <RUN_ID> --failed
418|gh workflow run ci.yml --ref main
419|gh workflow run deploy.yml -f environment=staging
420|```
421|
422|**With curl:**
423|
424|```bash
425|# List workflows
426|curl -s \
427|  -H "Authorization: token $GITHUB_TOKEN" \
428|  https://api.github.com/repos/$OWNER/$REPO/actions/workflows \
429|  | python3 -c "
430|import sys, json
431|for w in json.load(sys.stdin)['workflows']:
432|    print(f\"  {w['id']:10}  {w['name']:30}  {w['state']}\")"
433|
434|# List recent runs
435|curl -s \
436|  -H "Authorization: token $GITHUB_TOKEN" \
437|  "https://api.github.com/repos/$OWNER/$REPO/actions/runs?per_page=10" \
438|  | python3 -c "
439|import sys, json
440|for r in json.load(sys.stdin)['workflow_runs']:
441|    print(f\"  Run {r['id']}  {r['name']:30}  {r['conclusion'] or r['status']}\")"
442|
443|# Download failed run logs
444|RUN_ID=<run_id>
445|curl -s -L \
446|  -H "Authorization: token $GITHUB_TOKEN" \
447|  https://api.github.com/repos/$OWNER/$REPO/actions/runs/$RUN_ID/logs \
448|  -o /tmp/ci-logs.zip
449|cd /tmp && unzip -o ci-logs.zip -d ci-logs
450|
451|# Re-run a failed workflow
452|curl -s -X POST \
453|  -H "Authorization: token $GITHUB_TOKEN" \
454|  https://api.github.com/repos/$OWNER/$REPO/actions/runs/$RUN_ID/rerun
455|
456|# Re-run only failed jobs
457|curl -s -X POST \
458|  -H "Authorization: token $GITHUB_TOKEN" \
459|  https://api.github.com/repos/$OWNER/$REPO/actions/runs/$RUN_ID/rerun-failed-jobs
460|
461|# Trigger a workflow manually (workflow_dispatch)
462|WORKFLOW_ID=<workflow_id_or_filename>
463|curl -s -X POST \
464|  -H "Authorization: token $GITHUB_TOKEN" \
465|  https://api.github.com/repos/$OWNER/$REPO/actions/workflows/$WORKFLOW_ID/dispatches \
466|  -d '{"ref": "main", "inputs": {"environment": "staging"}}'
467|```
468|
469|## 10. Gists
470|
471|**With gh:**
472|
473|```bash
474|gh gist create script.py --public --desc "Useful script"
475|gh gist list
476|```
477|
478|**With curl:**
479|
480|```bash
481|# Create a gist
482|curl -s -X POST \
483|  -H "Authorization: token $GITHUB_TOKEN" \
484|  https://api.github.com/gists \
485|  -d '{
486|    "description": "Useful script",
487|    "public": true,
488|    "files": {
489|      "script.py": {"content": "print(\"hello\")"}
490|    }
491|  }'
492|
493|# List your gists
494|curl -s \
495|  -H "Authorization: token $GITHUB_TOKEN" \
496|  https://api.github.com/gists \
497|  | python3 -c "
498|import sys, json
499|for g in json.load(sys.stdin):
500|    files = ', '.join(g['files'].keys())
501|
# Auth

1|---
2|name: github-auth
3|description: "GitHub auth setup: HTTPS tokens, SSH keys, gh CLI login."
4|version: 1.1.0
5|author: Hermes Agent
6|license: MIT
7|platforms: [linux, macos, windows]
8|metadata:
9|  hermes:
10|    tags: [GitHub, Authentication, Git, gh-cli, SSH, Setup]
11|    related_skills: [github-pr-workflow, github-code-review, github-issues, github-repo-management]
12|---
13|
14|# GitHub Authentication Setup
15|
16|This skill sets up authentication so the agent can work with GitHub repositories, PRs, issues, and CI. It covers two paths:
17|
18|- **`git` (always available)** — uses HTTPS personal access tokens or SSH keys
19|- **`gh` CLI (if installed)** — richer GitHub API access with a simpler auth flow
20|
21|## Detection Flow
22|
23|When a user asks you to work with GitHub, run this check first:
24|
25|```bash
26|# Check what's available
27|git --version
28|gh --version 2>/dev/null || echo "gh not installed"
29|
30|# Check if already authenticated
31|gh auth status 2>/dev/null || echo "gh not authenticated"
32|git config --global credential.helper 2>/dev/null || echo "no git credential helper"
33|```
34|
35|**Decision tree:**
36|1. If `gh auth status` shows authenticated → you're good, use `gh` for everything
37|2. If `gh` is installed but not authenticated → use "gh auth" method below
38|3. If `gh` is not installed → use "git-only" method below (no sudo needed)
39|
40|---
41|
42|## Method 1: Git-Only Authentication (No gh, No sudo)
43|
44|This works on any machine with `git` installed. No root access needed.
45|
46|### Option A: HTTPS with Personal Access Token (Recommended)
47|
48|This is the most portable method — works everywhere, no SSH config needed.
49|
50|**Step 1: Create a personal access token**
51|
52|Tell the user to go to: **https://github.com/settings/tokens**
53|
54|- Click "Generate new token (classic)"
55|- Give it a name like "hermes-agent"
56|- Select scopes:
57|  - `repo` (full repository access — read, write, push, PRs)
58|  - `workflow` (trigger and manage GitHub Actions)
59|  - `read:org` (if working with organization repos)
60|- Set expiration (90 days is a good default)
61|- Copy the token — it won't be shown again
62|
63|**Step 2: Configure git to store the token**
64|
65|```bash
66|# Set up the credential helper to cache credentials
67|# "store" saves to ~/.git-credentials in plaintext (simple, persistent)
68|git config --global credential.helper store
69|
70|# Now do a test operation that triggers auth — git will prompt for credentials
71|# Username: <their-github-username>
72|# Password: <paste the personal access token, NOT their GitHub password>
73|git ls-remote https://github.com/<their-username>/<any-repo>.git
74|```
75|
76|After entering credentials once, they're saved and reused for all future operations.
77|
78|**Alternative: cache helper (credentials expire from memory)**
79|
80|```bash
81|# Cache in memory for 8 hours (28800 seconds) instead of saving to disk
82|git config --global credential.helper 'cache --timeout=28800'
83|```
84|
85|**Alternative: set the token directly in the remote URL (per-repo)**
86|
87|```bash
88|# Embed token in the remote URL (avoids credential prompts entirely)
89|git remote set-url origin https://<username>:<token>@github.com/<owner>/<repo>.git
90|```
91|
92|**Step 3: Configure git identity**
93|
94|```bash
95|# Required for commits — set name and email
96|git config --global user.name "Their Name"
97|git config --global user.email "their-email@example.com"
98|```
99|
100|**Step 4: Verify**
101|
102|```bash
103|# Test push access (this should work without any prompts now)
104|git ls-remote https://github.com/<their-username>/<any-repo>.git
105|
106|# Verify identity
107|git config --global user.name
108|git config --global user.email
109|```
110|
111|### Option B: SSH Key Authentication
112|
113|Good for users who prefer SSH or already have keys set up.
114|
115|**Step 1: Check for existing SSH keys**
116|
117|```bash
118|ls -la ~/.ssh/id_*.pub 2>/dev/null || echo "No SSH keys found"
119|```
120|
121|**Step 2: Generate a key if needed**
122|
123|```bash
124|# Generate an ed25519 key (modern, secure, fast)
125|ssh-keygen -t ed25519 -C "their-email@example.com" -f ~/.ssh/id_ed25519 -N ""
126|
127|# Display the public key for them to add to GitHub
128|cat ~/.ssh/id_ed25519.pub
129|```
130|
131|Tell the user to add the public key at: **https://github.com/settings/keys**
132|- Click "New SSH key"
133|- Paste the public key content
134|- Give it a title like "hermes-agent-<machine-name>"
135|
136|**Step 3: Test the connection**
137|
138|```bash
139|ssh -T git@github.com
140|# Expected: "Hi <username>! You've successfully authenticated..."
141|```
142|
143|**Step 4: Configure git to use SSH for GitHub**
144|
145|```bash
146|# Rewrite HTTPS GitHub URLs to SSH automatically
147|git config --global url."git@github.com:".insteadOf "https://github.com/"
148|```
149|
150|**Step 5: Configure git identity**
151|
152|```bash
153|git config --global user.name "Their Name"
154|git config --global user.email "their-email@example.com"
155|```
156|
157|---
158|
159|## Method 2: gh CLI Authentication
160|
161|If `gh` is installed, it handles both API access and git credentials in one step.
162|
163|### Interactive Browser Login (Desktop)
164|
165|```bash
166|gh auth login
167|# Select: GitHub.com
168|# Select: HTTPS
169|# Authenticate via browser
170|```
171|
172|### Token-Based Login (Headless / SSH Servers)
173|
174|```bash
175|echo "<THEIR_TOKEN>" | gh auth login --with-token
176|
177|# Set up git credentials through gh
178|gh auth setup-git
179|```
180|
181|### Verify
182|
183|```bash
184|gh auth status
185|```
186|
187|---
188|
189|## Using the GitHub API Without gh
190|
191|When `gh` is not available, you can still access the full GitHub API using `curl` with a personal access token. This is how the other GitHub skills implement their fallbacks.
192|
193|### Setting the Token for API Calls
194|
195|```bash
196|# Option 1: Export as env var (preferred — keeps it out of commands)
197|export GITHUB_TOKEN="<token>"
198|
199|# Then use in curl calls:
200|curl -s -H "Authorization: token $GITHUB_TOKEN" \
201|  https://api.github.com/user
202|```
203|
204|### Extracting the Token from Git Credentials
205|
206|If git credentials are already configured (via credential.helper store), the token can be extracted:
207|
208|```bash
209|# Read from git credential store
210|grep "github.com" ~/.git-credentials 2>/dev/null | head -1 | sed 's|https://[^:]*:\([^@]*\)@.*|\1|'
211|```
212|
213|### Helper: Detect Auth Method
214|
215|Use this pattern at the start of any GitHub workflow:
216|
217|```bash
218|# Try gh first, fall back to git + curl
219|if command -v gh &>/dev/null && gh auth status &>/dev/null; then
220|  echo "AUTH_METHOD=gh"
221|elif [ -n "$GITHUB_TOKEN" ]; then
222|  echo "AUTH_METHOD=curl"
223|elif _hermes_env="${HERMES_HOME:-$HOME/.hermes}/.env"; [ -f "$_hermes_env" ] && grep -q "^GITHUB_TOKEN=" "$_hermes_env"; then
224|  export GITHUB_TOKEN=$(grep "^GITHUB_TOKEN=" "$_hermes_env" | head -1 | cut -d= -f2 | tr -d '\n\r')
225|  echo "AUTH_METHOD=curl"
226|elif grep -q "github.com" ~/.git-credentials 2>/dev/null; then
227|  export GITHUB_TOKEN=$(grep "github.com" ~/.git-credentials | head -1 | sed 's|https://[^:]*:\([^@]*\)@.*|\1|')
228|  echo "AUTH_METHOD=curl"
229|else
230|  echo "AUTH_METHOD=none"
231|  echo "Need to set up authentication first"
232|fi
233|```
234|
235|---
236|
237|## Troubleshooting
238|
239|| Problem | Solution |
240||---------|----------|
241|| `git push` asks for password | GitHub disabled password auth. Use a personal access token as the password, or switch to SSH |
242|| `remote: Permission to X denied` | Token may lack `repo` scope — regenerate with correct scopes |
243|| `fatal: Authentication failed` | Cached credentials may be stale — run `git credential reject` then re-authenticate |
244|| `ssh: connect to host github.com port 22: Connection refused` | Try SSH over HTTPS port: add `Host github.com` with `Port 443` and `Hostname ssh.github.com` to `~/.ssh/config` |
245|| Credentials not persisting | Check `git config --global credential.helper` — must be `store` or `cache` |
246|| Multiple GitHub accounts | Use SSH with different keys per host alias in `~/.ssh/config`, or per-repo credential URLs |
247|| `gh: command not found` + no sudo | Use git-only Method 1 above — no installation needed |
248|
# GitHub Collaboration Guide (Hackathon Edition)

This guide is written so that **anyone, even someone who has never used GitHub before**, can follow it. Read it top to bottom once, then use it as a reference during the week.

Timeline: 1 week hackathon. Keep changes small, commit often, and never push directly to `main`.

---

## 1. Core Rule of This Project

> **Nobody pushes directly to `main`. Ever.**

`main` (or `master`) is the branch that always has the working, deployable code. If it breaks, the whole team is blocked. All work happens on separate **branches**, and code only reaches `main` through a **Pull Request (PR)** that someone else reviews and approves.

---

## 2. Basic Concepts (Explained Simply)

| Term | What it actually means |
|---|---|
| **Repository (repo)** | The project folder, tracked by Git, hosted on GitHub. |
| **Clone** | Downloading a copy of the repo onto your own laptop. |
| **Branch** | A parallel copy of the code where you can make changes without affecting `main`. Think of it as a "draft" version. |
| **Commit** | A saved checkpoint of your changes, with a short message describing what you did. |
| **Push** | Uploading your local commits to GitHub. |
| **Pull** | Downloading the latest changes from GitHub to your laptop. |
| **Pull Request (PR)** | A request asking "please merge my branch into `main`", which teammates review before it's accepted. |
| **Merge** | Combining one branch's changes into another (usually a branch into `main`). |
| **Merge Conflict** | When two people changed the same lines of the same file differently, and Git needs a human to decide which version to keep. |

---

## 3. One-Time Setup (Do This Once)

### 3.1 Install Git
- Windows: download from https://git-scm.com/download/win and install with default options.
- Mac: open Terminal and type `git --version` — it will prompt you to install if missing.
- Linux: `sudo apt install git`

### 3.2 Create a GitHub account
Go to https://github.com and sign up (if you don't already have one).

### 3.3 Configure Git on your laptop
Open a terminal (Command Prompt, PowerShell, Terminal, or Git Bash) and run:

```bash
git config --global user.name "Your Name"
git config --global user.email "youremail@example.com"
```

Use the same email as your GitHub account.

### 3.4 Get added to the repo
Ask the repo owner (project admin) to add your GitHub username as a **Collaborator**:
Repo → Settings → Collaborators → Add people.

### 3.5 Clone the repository
On GitHub, click the green **Code** button, copy the HTTPS URL, then in your terminal:

```bash
git clone https://github.com/<org-or-user>/<repo-name>.git
cd <repo-name>
```

You now have the project on your machine.

---

## 4. Daily Workflow (Do This Every Time You Work)

### Step 1 — Always start from an updated `main`

```bash
git checkout main
git pull origin main
```

This makes sure you're building on top of the latest code, not something outdated.

### Step 2 — Create a new branch for your task

Never work directly on `main`. Create a branch named after what you're doing.

**Branch naming convention:**

```
<type>/<short-description>
```

Types to use:
- `feature/` — new functionality (e.g. `feature/login-page`)
- `fix/` — bug fix (e.g. `fix/navbar-overlap`)
- `chore/` — config, docs, cleanup (e.g. `chore/update-readme`)

Example:

```bash
git checkout -b feature/login-page
```

This creates the branch and switches you to it in one command.

### Step 3 — Make your changes

Edit code as normal in your editor (VS Code, etc.).

### Step 4 — Check what changed

```bash
git status
```

This shows which files you modified.

### Step 5 — Stage and commit your changes

```bash
git add .
git commit -m "Add login page UI with email/password fields"
```

**Commit message tips:**
- Keep it short, present tense: "Add", "Fix", "Update", "Remove"
- Describe *what* changed, not "changes" or "stuff"
- Commit often — after every small, working piece of progress, not once a day.

### Step 6 — Push your branch to GitHub

First push of a new branch:

```bash
git push -u origin feature/login-page
```

Every push after that, just:

```bash
git push
```

### Step 7 — Open a Pull Request (PR)

1. Go to the repo on GitHub. You'll see a banner: "feature/login-page had recent pushes — Compare & pull request." Click it.
   - If you don't see the banner: go to **Pull requests** tab → **New pull request** → base: `main`, compare: your branch.
2. Fill in:
   - **Title:** short summary (e.g. "Add login page UI")
   - **Description:** what you did, what you tested, any screenshots.
3. Click **Create pull request**.

### Step 8 — Get it reviewed

- Tag a teammate to review (Reviewers panel on the right side of the PR).
- Reviewer reads the code, tests it if possible, and either:
  - **Approves** ✅, or
  - **Requests changes** with comments.
- If changes are requested: make the fixes on your same branch, commit, push again. The PR updates automatically — no need to open a new one.

### Step 9 — Merge into `main`

Once approved AND the build passes (see Section 8):

- Click **Merge pull request** on GitHub → **Confirm merge**.
- Delete the branch afterward (GitHub shows a "Delete branch" button) to keep things tidy.

### Step 10 — Sync your local `main`

Everyone should pull the latest `main` after any merge:

```bash
git checkout main
git pull origin main
```

---

## 5. Documentation After Every Push (IMPLEMENTATION.md / UPDATES.md and CONTEXT.md)

In a fast-moving 1-week hackathon, teammates (and any AI coding assistant helping you, like Claude or Copilot) can easily lose track of what's already been built, why a decision was made, or what's still pending. To avoid re-explaining the whole project every time, and to avoid an AI assistant burning tokens/quota re-reading the entire codebase or guessing at what changed, keep two lightweight docs updated **every time you push**.

### 5.1 `UPDATES.md` (or `IMPLEMENTATION.md`) — a running changelog

Keep this file at the repo root. Every time you push a feature or fix, add a short dated entry at the **top** of the file (newest first). This is a human-readable history of what was built.

**Format to use:**

```markdown
## [2026-09-15] Login page UI — feature/login-page

**What was implemented:**
- Added email/password login form (`src/pages/Login.jsx`)
- Wired up form validation (empty fields, invalid email format)
- Connected to `/api/auth/login` endpoint (stubbed, backend pending)

**Files touched:**
- src/pages/Login.jsx (new)
- src/routes.js (added /login route)
- src/api/auth.js (new)

**How to test it:**
- Run `npm run dev`, go to `/login`
- Try submitting empty form → should show validation errors
- Try valid email/password → currently logs to console (backend not connected yet)

**Notes / follow-ups:**
- Backend login endpoint not built yet — using a mock response
- Password reset flow is NOT part of this PR
```

**When to add an entry:** every time you open a PR (or right after you push, whichever your team prefers) — not just when you merge. This keeps the log current even mid-review.

**Rule:** never delete old entries. This file is meant to grow across the week so anyone (or any AI assistant) can scroll it and understand the full history in one read, instead of digging through commit-by-commit diffs.

### 5.2 `CONTEXT.md` — the current state of the project, always up to date

Unlike `UPDATES.md` (a history log), `CONTEXT.md` is a **snapshot of the present** — what the project actually looks like *right now*. Update this file (overwrite the relevant section, don't just append) whenever something changes the shape of the project: a new module, a changed architecture decision, a new dependency, a changed API contract, etc.

This is specifically to help an AI assistant (or a teammate jumping in mid-week) get oriented in seconds instead of reading the entire codebase or asking you to re-explain everything — which wastes time and, for AI tools with usage limits, wastes tokens/quota on re-discovery.

**Suggested structure:**

```markdown
# Project Context (last updated: 2026-09-15)

## What this project is
One-paragraph description of the hackathon idea.

## Current architecture
- Frontend: React (Vite), Tailwind
- Backend: Node/Express, PostgreSQL
- Auth: JWT-based (in progress)
- Hosting: Vercel (frontend), Railway (backend)

## What's done
- Login UI (no backend wiring yet)
- Landing page
- DB schema for users table

## What's in progress
- Backend auth endpoints (owner: <name>)
- Dashboard UI (owner: <name>)

## What's NOT started
- Payments
- Notifications

## Key decisions and why
- Chose JWT over sessions because [reason]
- Using PostgreSQL instead of MongoDB because [reason]

## Known issues / gotchas
- API base URL is hardcoded in src/api/config.js — needs .env before deploy
```

**Rule of thumb:** if you (or an AI assistant) would need to ask "wait, what's the current setup?" — that answer belongs in `CONTEXT.md`, kept current, not in someone's memory or buried in a Slack/Discord thread.

### 5.3 Quick checklist to add to your push habit

After `git push`, before opening/updating the PR:

1. Add a new dated entry to `UPDATES.md` describing what you just implemented.
2. Update the relevant section(s) of `CONTEXT.md` if this change affected the project's current state (new module, changed decision, new dependency, etc. — skip this step if nothing structural changed).
3. Commit both files in the same branch:

```bash
git add UPDATES.md CONTEXT.md
git commit -m "Update docs: login page UI"
git push
```

Small habit, big payoff — by day 4 of the hackathon nobody (human or AI) has to reverse-engineer what happened on days 1–3.

---

## 6. Handling Merge Conflicts (When They Happen)

If GitHub says your branch "has conflicts" with `main`, or `git pull` gives an error, do this:

```bash
git checkout main
git pull origin main
git checkout feature/login-page
git merge main
```

Git will mark conflicting sections in the file like this:

```
<<<<<<< HEAD
your version of the code
=======
their version of the code
>>>>>>> main
```

1. Open the file, manually decide what the final code should look like (keep one version, both, or a combination).
2. Delete the `<<<<<<<`, `=======`, `>>>>>>>` marker lines.
3. Save the file.
4. Then:

```bash
git add .
git commit -m "Resolve merge conflict with main"
git push
```

If you're unsure how to resolve a conflict, **ask a teammate before guessing** — don't just pick a side blindly on shared logic.

---

## 7. Avoiding Conflicts When Two People Work at the Same Time

Conflicts mostly happen because of bad coordination, not because Git is broken. Follow these habits and most conflicts never happen in the first place.

### 7.1 Split work by file/module, not by line

Before starting, agree as a team on **who owns which files or folders** for the task at hand. If two people are editing the exact same function in the exact same file at the exact same time, a conflict is almost guaranteed. If you're working on separate files (e.g. one person on `LoginPage.js`, another on `Navbar.js`), Git merges them automatically with zero conflicts.

A 2-minute stand-up/chat message before starting ("I'm touching `auth.js` and `login.js` for the next hour") saves everyone time later.

### 7.2 Keep branches short-lived

Don't let a branch live for 3 days while `main` moves on without it. The longer a branch exists, the more `main` drifts away from it, and the bigger the eventual conflict. Aim to:
- Finish a task in a few hours, not days.
- Open the PR as soon as it works, even if small.
- Merge it, then start the next branch.

Small, frequent PRs > one giant PR at the end of the week.

### 7.3 Pull `main` into your branch often, not just at the end

Don't wait until you're "done" to check if `main` has moved. While working, periodically do:

```bash
git checkout main
git pull origin main
git checkout feature/your-task-name
git merge main
```

Do this at least once a day, or right before you start a new work session. If a conflict appears, you resolve a *small* one immediately instead of a *huge* one right before the deadline.

### 7.4 Communicate on shared files

For files that genuinely need multiple people (e.g. a shared `App.js`, `routes.js`, or `config.js`):
- Message the team before editing: "Editing `routes.js` now, back in 20 min."
- Keep your changes to that file minimal and quick — add your one line/route, commit, push, and get out.
- Avoid reformatting or restructuring shared files unless the whole team agrees, since that touches every line and guarantees conflicts for everyone else.

### 7.5 Use Draft PRs to signal "in progress"

If you want to push work early for backup or visibility but it's not ready for review, open the PR as a **Draft PR** (GitHub has this option when creating a PR). This tells teammates "don't merge this yet, but here's what I'm doing" without blocking anyone.

### 7.6 If a conflict happens anyway

That's normal — it's not a mistake, just follow Section 6 above calmly. The habits above just make conflicts rare and small instead of frequent and painful.

---

## 8. Keeping the Build Compatible

Since this is a hackathon on a tight timeline, a broken `main` costs everyone time. Before opening or merging any PR:

1. **Pull latest `main` into your branch first** (Section 6 or 7.3) so you're testing against the newest code, not stale code.
2. **Run the project locally** and confirm it builds/starts without errors:
   - Node/JS projects: `npm install && npm run build` (or `npm run dev`/`npm start` to sanity check)
   - Python projects: `pip install -r requirements.txt` and run the app/tests
   - Adjust the exact commands to whatever this repo actually uses — check the project's `README.md` or `package.json` scripts.
3. **Never commit secrets or environment files** (`.env`, API keys). Add them to `.gitignore` if not already there.
4. **Never commit broken code "to be fixed later."** If a feature is incomplete, keep it on your branch — don't merge it into `main` until it works.
5. If the repo has a CI pipeline (GitHub Actions — you'll see checks like "✅ build passed" under the PR), **do not merge until it's green.** A red X means the build is broken; fix it first.
6. Only merge when: PR is approved **and** the build/check passes **and** you've tested it runs locally.

---

## 9. Quick Reference Cheat Sheet

```bash
# One-time
git clone <repo-url>
git config --global user.name "Your Name"
git config --global user.email "you@example.com"

# Every task
git checkout main
git pull origin main
git checkout -b feature/your-task-name

# While working
git status
git add .
git commit -m "Describe what you did"
git push -u origin feature/your-task-name   # first push only
git push                                     # subsequent pushes

# After merge
git checkout main
git pull origin main

# After every push (see Section 5)
git add UPDATES.md CONTEXT.md
git commit -m "Update docs: <what you built>"
git push
```

---

## 10. Golden Rules (Pin This)

1. Never push directly to `main`.
2. Always `pull` before you start new work.
3. One branch = one task/feature. Don't mix unrelated changes.
4. Commit small, commit often, write clear messages.
5. Open a PR, get at least one review, wait for the build to pass, then merge.
6. Delete branches after merging to avoid clutter.
7. If stuck or confused (especially with conflicts), ask the team — don't force-push or guess on shared code.
8. Never commit `.env` files, API keys, or credentials.
9. After every push, add an entry to `UPDATES.md` and keep `CONTEXT.md` current (Section 5) — future you, your teammates, and any AI assistant helping out will thank you.

---

## 11. Common Errors and Fixes

| Error/Situation | Fix |
|---|---|
| `fatal: not a git repository` | You're not inside the cloned folder. `cd` into it first. |
| `Updates were rejected` on push | Someone else pushed first. Run `git pull` (or `git pull --rebase`) then push again. |
| Accidentally committed on `main` | `git checkout -b feature/rescue-my-work` (creates a branch with your changes), then continue normally. Ask a teammate to help reset `main` if needed. |
| Forgot to pull before starting | Not fatal — just merge `main` into your branch before opening the PR (Section 6). |
| PR shows merge conflicts | Follow Section 6. |
| Two people worked on the same file at once | See Section 7 for how to avoid this going forward. |

---

*Keep this file in the repo root as `GITHUB_GUIDE.md` so every teammate can reference it during the week.*

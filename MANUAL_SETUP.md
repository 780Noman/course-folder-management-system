# Manual Setup — what you (Noman) do by hand

These are the steps to run **once**, by you. Everything else (the actual app
code) is built by Claude Code following `PLAN.md`.

## 1. Put these files in place

Create the project folder and drop this scaffold into it:

```
C:\Projects\course-folder-system\
```

## 2. Check Python and create a virtual environment (never use global)

Use Python 3.12. In PowerShell:

```powershell
python --version           # expect 3.12.x ; if missing: winget install Python.Python.3.12

cd C:\Projects\course-folder-system
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

> Note: WeasyPrint (PDF) needs GTK libraries on Windows. The clean path is to
> develop with **Docker** (below), which already includes them and matches
> production. If you prefer local-only, install the GTK runtime, or tell Claude
> Code to use `xhtml2pdf` instead of WeasyPrint for local dev.

## 3. Recommended: run with Docker (matches production)

Install Docker Desktop, then:

```powershell
copy .env.example .env      # open .env and fill values
docker compose up
```

App runs at http://localhost:8000. Postgres is included.

## 4. Install the design + helper skills for Claude Code

In Claude Code:

```
# Design system intelligence
/plugin marketplace add nextlevelbuilder/ui-ux-pro-max-skill
/plugin install ui-ux-pro-max@ui-ux-pro-max-skill

# Anthropic's official plugin directory (browse and install)
/plugin marketplace add anthropics/claude-plugins-official
/plugin > Discover        # install: claude-md-management, claude-code-setup
```

`frontend-design` is Anthropic's official skill; install it the same way from a
skills marketplace, or place it under `.claude/skills/`. (Note: the exact name
`claude-md-improver` does not exist — the official equivalent is
**`claude-md-management`**.)

## 5. Git: create the private repo and push

This scaffold already has a clean initial commit. To publish it:

```powershell
# set your identity (once)
git config user.name "Noman Amjad"
git config user.email "YOUR_GITHUB_EMAIL"

# re-stamp the existing commit with your identity (optional)
git commit --amend --reset-author --no-edit

# create a PRIVATE repo on GitHub named course-folder-system, then:
git remote add origin https://github.com/<your-username>/course-folder-system.git
git branch -M main
git push -u origin main
```

Then create the working branches you use:

```powershell
git checkout -b dev
git push -u origin dev
git checkout -b qa
git push -u origin qa
```

> When you share the remote URL with me, I can give you the exact commands for
> each later commit. I cannot push to your private repo directly (that needs your
> own GitHub credentials, which you should never share).

## 6. First admin (after the app is built in Phase 1)

```powershell
docker compose run --rm web python manage.py createsuperuser
```

Or add your supervisor's email through the admin so she receives an invite link
and sets her own password.

## 7. Hand off to Claude Code

Open Claude Code in `C:\Projects\course-folder-system` and start with:

> Read CLAUDE.md, PLAN.md and docs/DATA_MODEL.md. Then begin Phase 0, one task
> at a time. Verify before acting, do not guess, run tests after each task, and
> stop after each task so I can review.

# GitHub Setup Guide for Agentic Auto Routing System

This guide will help you push this project to GitHub safely, with your API key hidden.

## ✅ What's Already Done

- ✅ `.env.example` created (template for environment variables)
- ✅ `.gitignore` configured (excludes `.env`, credentials, sensitive files)
- ✅ Code already uses `os.getenv("OPENROUTER_API_KEY")` (environment variable, not hardcoded)
- ✅ `README.md` ready for GitHub

## 🔐 Step 1: Set Up Your Local Environment

### 1a. Create a .env file (DO NOT COMMIT THIS)

```bash
cd agentic_auto_routing
cp .env.example .env
```

Edit `.env` with your actual API key:
```
OPENROUTER_API_KEY=sk_live_xxxxxxxxxxxxxxxxxxxxx
OPENROUTER_MODEL=meta-llama/llama-2-70b-chat
SERVER_PORT=8001
DEBUG=False
```

### 1b. Verify .gitignore is working

The `.gitignore` file **already excludes `.env`**, so your API key will never be committed.

To verify:
```bash
# This should NOT show .env or any secrets
git status
```

## 📦 Step 2: Initialize Git Repository Locally

```bash
cd agentic_auto_routing

# Initialize git (if not already done)
git init

# Add all files (except those in .gitignore)
git add .

# Verify .env and __pycache__ are excluded
git status  # Should NOT show .env or __pycache__

# Create initial commit
git commit -m "Initial commit: Agentic Auto Routing System

- Multi-modal transportation planning agent
- Natural language constraint handling
- Route optimization with Dijkstra's algorithm
- Comprehensive test suite"
```

## 🌐 Step 3: Create Repository on GitHub

### 3a. Create new repository on GitHub.com

1. Go to https://github.com/new
2. **Repository name**: `agentic-auto-routing` (or your choice)
3. **Description**: "Intelligent multi-modal transportation planning agent with NLP and graph optimization"
4. **Visibility**: Public (for portfolio) or Private
5. **Do NOT initialize** with README, .gitignore, or license (we already have these)
6. Click "Create repository"

### 3b. Add remote origin

After repository is created, GitHub will show you commands. Run:

```bash
# Replace USERNAME with your GitHub username
git remote add origin https://github.com/USERNAME/agentic-auto-routing.git

# Verify remote is set
git remote -v
```

## 🚀 Step 4: Push to GitHub

```bash
# Push local commits to GitHub
git branch -M main
git push -u origin main

# Verify - you should see your repo at:
# https://github.com/USERNAME/agentic-auto-routing
```

## ✨ Step 5: Verify Security

### 5a. Check nothing sensitive was committed

```bash
# Search for API key patterns (should find nothing)
git log -p | grep -i "openrouter_api_key" || echo "✓ No secrets found"

# Verify .env is in .gitignore
cat .gitignore | grep ".env"  # Should show ".env"
```

### 5b. Add GitHub-specific safety files

Optionally, create a `CONTRIBUTING.md`:

```bash
cat > CONTRIBUTING.md << 'EOF'
# Contributing

## Setup

1. Clone the repository
2. Create a virtual environment: `python -m venv venv`
3. Activate: `source venv/bin/activate` (or `venv\Scripts\activate` on Windows)
4. Install dependencies: `pip install -r requirements.txt`
5. Copy `.env.example` to `.env` and fill in your OpenRouter API key

## Never commit:
- `.env` (contains real API keys)
- `__pycache__/` (Python cache)
- `.venv/` (virtual environment)
- IDE settings (`.vscode/`, `.idea/`)

## Running tests

```bash
python test_harness.py
python test_leg_constraint_integration.py
```

## Running the server

```bash
uvicorn main:app --reload --port 8001
```
EOF
```

## 📋 Step 6: Add requirements.txt

Create a `requirements.txt` for easy dependency installation:

```bash
cat > requirements.txt << 'EOF'
fastapi==0.104.1
uvicorn[standard]==0.24.0
pydantic==2.5.0
networkx==3.2.1
requests==2.31.0
python-multipart==0.0.6
python-dotenv==1.0.0
EOF
```

Then commit:
```bash
git add requirements.txt CONTRIBUTING.md
git commit -m "Add requirements.txt and contributing guidelines"
git push
```

## 🎯 Final Verification Checklist

- ✅ `.env` file exists locally (with your real API key) but NOT in git
- ✅ `.gitignore` includes `.env`
- ✅ README.md is in the repo
- ✅ Repository is on GitHub
- ✅ No secrets appear in git history
- ✅ `requirements.txt` is included
- ✅ `CONTRIBUTING.md` explains setup process

## 🔍 Double-Check: Never Accidentally Commit Secrets

If you accidentally committed an `.env` file before creating `.gitignore`:

```bash
# Remove it from git history (dangerous - only if absolutely necessary)
git rm --cached .env
git commit -m "Remove .env from tracking"
git push

# Then rotate your API key immediately at https://openrouter.ai/keys
```

## 📚 Optional: Add GitHub Features

### Branch Protection
Settings → Branches → Add rule → Require PR reviews

### GitHub Actions (CI/CD)
Create `.github/workflows/test.yml`:

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
        with:
          python-version: '3.9'
      - run: pip install -r requirements.txt
      - run: python test_harness.py
      - run: python test_leg_constraint_integration.py
```

## 🎓 Your Repo Structure After Pushing

```
agentic-auto-routing/
├── README.md
├── CONTRIBUTING.md
├── requirements.txt
├── .env.example (environment template)
├── .gitignore (secrets exclusion)
├── main.py
├── index.html
├── agents/
├── models/
├── services/
├── data/
├── tests/
├── RESUME_WRITEUP.md
└── RESUME_BULLETS.md
```

## 💡 Tips

1. **Don't share `.env` files** - Each developer should have their own
2. **Share `.env.example`** - Shows required variables without exposing secrets
3. **Rotate API keys regularly** - If mistakenly exposed, rotate immediately
4. **Use GitHub Secrets** - If you set up CI/CD later, store API keys in GitHub Secrets
5. **Document setup** - People cloning your repo need to know how to set it up

## ✅ You're Done!

Your project is now on GitHub with:
- ✅ API key safely hidden
- ✅ Clear setup instructions
- ✅ Professional documentation
- ✅ Test suite included
- ✅ Resume materials included

Share the link: `https://github.com/USERNAME/agentic-auto-routing`

---

Need help? See GitHub's documentation:
- https://docs.github.com/en/get-started/quickstart/create-a-repo
- https://docs.github.com/en/get-started/using-git/about-git

# Contributing to LegalMetrix

Welcome to the **LegalMetrix** (AI-Assisted Legal Metrology Inspection System) repository. Follow this guide to ensure safe, professional, and conflict-free collaboration across all team members.

---

## 1. Initial Setup & Cloning

### 1. Clone the repository
```bash
git clone https://github.com/AkshaySrivastava-Dev/LegalMetrix.git
cd LegalMetrix
```

### 2. Create and activate a Python virtual environment
```bash
# Windows (PowerShell)
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# Linux / macOS
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install dependencies
```bash
pip install --upgrade pip
pip install -r requirements-dev.txt
```

---

## 2. Core Collaboration Rules

1. **NEVER push directly to `main`**: The `main` branch is protected and contains stable, tested, demo-ready code.
2. **Always work on a feature branch**: Never make commits directly on local `main`.
3. **Run local tests before opening a PR**: All 88 automated tests must pass (`python -m pytest -v`).
4. **Keep changes scoped to your module**: Respect directory ownership boundaries.
5. **Never commit prohibited artifacts**:
   - Virtual environments (`.venv/`, `venv/`)
   - Python bytecode (`__pycache__/`, `*.pyc`)
   - Test caches (`.pytest_cache/`, `.coverage`)
   - Deep learning weights / model caches (`.paddlex/`, `.cache/`, `evidence/`)
   - Secret/environment files (`.env`, `.env.*`, `*.pem`, `*.key`)
   - OS-generated files (`Thumbs.db`, `.DS_Store`)

---

## 3. Standard Branch Naming

Use the following branch naming conventions for team modules:

| Branch Name Format | Domain / Responsibility | Target Modules |
|---|---|---|
| `feature/ai-ocr` | Member 3: OCR Engine & Field Extraction | `ai/`, `test_data/` |
| `feature/backend` | Member 4 / Backend Lead: FastAPI Routes & Storage | `api/`, `main.py` |
| `feature/rules` | Member 4 / Legal Lead: Legal Metrology Rule Engine | `rules/` |
| `feature/reconciliation` | Member 4 / Data Lead: Catalog & Historical Diff | `reconciliation/` |
| `feature/frontend` | Frontend Lead: User Interface & Web Dashboard | `frontend/` |
| `fix/<description>` | Bug fixes across any module | Relevant files |

---

## 4. Team Git Workflow (Step-by-Step)

### Step 1: Sync your local `main`
Always start from the latest code on GitHub:
```bash
git checkout main
git pull origin main
```

### Step 2: Create your feature branch
```bash
# Example for AI/OCR work
git checkout -b feature/ai-ocr

# Example for Backend work
git checkout -b feature/backend
```

### Step 3: Implement changes and test locally
Run the automated test suite frequently during development:
```bash
python -m pytest -v
```
*(Optionally, run real OCR smoke test if modifying OCR: `python tests/test_real_ocr_smoke.py test_data/test_image.jpg`)*

### Step 4: Keep your branch updated with `main`
If changes were merged to `main` while you were working, pull them into your branch:
```bash
git fetch origin
git merge origin/main
# Resolve any merge conflicts, then re-run tests
python -m pytest -v
```

### Step 5: Stage and commit your changes
```bash
# Verify modified files
git status

# Stage specific changes
git add <files-you-changed>

# Commit with a clear, descriptive message
git commit -m "feat(ai): enhance manufacturer regex pattern detection"
```

### Step 6: Push your branch to GitHub
```bash
git push -u origin feature/your-branch-name
```

### Step 7: Open a Pull Request (PR)
1. Navigate to https://github.com/AkshaySrivastava-Dev/LegalMetrix.
2. Click **Compare & pull request** for your branch.
3. Base branch: `main` $\leftarrow$ Compare branch: `feature/your-branch-name`.
4. Fill in the PR description:
   - Summary of changes
   - Modules affected
   - Test results (`88/88 passed`)

### Step 8: Automated CI & Code Review
1. **GitHub Actions CI** automatically runs the Backend Test Suite.
2. **Review Approval**: Request a review from the relevant module owner (`.github/CODEOWNERS`).
3. If changes are requested, make them locally, commit, and push; the PR will update automatically.

### Step 9: Merge & Cleanup
1. Once CI passes and approval is given, merge the PR (**Squash and merge** recommended).
2. Delete the remote feature branch on GitHub.
3. Clean up your local environment:
   ```bash
   git checkout main
   git pull origin main
   git branch -d feature/your-branch-name
   ```

---

## 5. Module Ownership Directory Map

```
LegalMetrix/
├── ai/              --> AI/OCR Lead (Member 3)
├── api/             --> Backend Lead
├── reconciliation/  --> Reconciliation & Historical Lead (Member 4)
├── rules/           --> Legal Compliance Rule Engine Lead (Member 4)
├── tests/           --> QA & Backend Maintainers
├── frontend/        --> Frontend Lead
└── main.py          --> Backend Lead
```

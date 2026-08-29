# Contributing to LegalMetrix

Thank you for collaborating on the **LegalMetrix** Smart India Hackathon project. Follow this guide to ensure smooth teamwork and avoid breaking working features.

---

## 1. Golden Rules of Collaboration

1. **NEVER push directly to `main`**. The `main` branch must always remain stable, green, and demo-ready.
2. **Work on dedicated feature branches** named descriptively (e.g. `feat/frontend-upload`, `fix/ocr-bounding-box`, `feat/rule-cosmetics`).
3. **Run local tests before opening a PR** (`python -m pytest -v`). Never open a PR with failing tests.
4. **Keep changes scoped to your module** (AI, Rules, Reconciliation, API, or Frontend).
5. **No large binary commits**: Do NOT commit virtual environments (`.venv`), OCR model caches (`.paddlex`), or heavy raw videos/datasets to Git.

---

## 2. Team Git Workflow (Step-by-Step)

### Step 1: Update your local `main`
```bash
git checkout main
git pull origin main
```

### Step 2: Create a feature branch
```bash
# Naming conventions: feat/<name>, fix/<name>, chore/<name>, docs/<name>
git checkout -b feat/your-feature-name
```

### Step 3: Implement your changes
Make changes strictly within your designated module:
- `ai/` — Member 3 (OCR & Field Extraction)
- `rules/` — Member 4 (Legal Rules & Compliance Engine)
- `reconciliation/` — Member 4 (Online & Historical Reconciliation)
- `api/` — Backend API & routes
- `frontend/` — Client UI

### Step 4: Run local verification tests
```bash
python -m pytest -v
```
All 88 tests must pass before you stage your files.

### Step 5: Stage and commit with a clear message
```bash
# Check modified files
git status

# Stage specific changes (avoid `git add .` if untracked caches exist)
git add <files-you-modified>

# Commit with a descriptive message
git commit -m "feat(api): add batch image upload support"
```

### Step 6: Push your feature branch to GitHub
```bash
git push -u origin feat/your-feature-name
```

### Step 7: Open a Pull Request (PR)
1. Go to the repository on GitHub.
2. Click **Compare & pull request**.
3. Set the base branch to `main`.
4. Provide a short summary of changes and mention what was tested.

### Step 8: Wait for Automated CI Checks
- GitHub Actions will run `python -m pytest -v` automatically.
- If checks fail, inspect the log, fix the issue locally, and push the update.

### Step 9: Code Review & Approval
- Request a review from the relevant module owner (defined in `.github/CODEOWNERS`).
- Address any review comments.

### Step 10: Merge & Cleanup
- Once approved and all CI checks pass, click **Squash and merge** (or **Merge pull request**).
- Delete the feature branch on GitHub.
- Switch back to local `main` and sync:
  ```bash
  git checkout main
  git pull origin main
  git branch -d feat/your-feature-name
  ```

---

## 3. Module Boundaries & Ownership

| Component | Directory | Responsibility |
|---|---|---|
| **AI / OCR Engine** | `ai/` | PaddleOCR wrapper, heuristic field extractor, image quality, category classifier |
| **Legal Compliance Engine** | `rules/` | Deterministic legal rules (JSON), confidence router, validators, manual review |
| **Reconciliation & History** | `reconciliation/` | Physical vs Online comparison, historical delta comparator, normalizers |
| **REST API Server** | `api/`, `main.py` | FastAPI endpoints, request/response validation, in-memory store |
| **Integration Tests** | `tests/` | Golden demo scenarios, API tests, image inspection tests |
| **Frontend Application** | `frontend/` | Web / Mobile user interface |

---

## 4. Troubleshooting & Getting Help

- **Tests failing due to missing package**: Run `pip install -r requirements-dev.txt`.
- **Merge conflicts**: Rebase or merge `main` into your feature branch (`git merge main`), resolve conflicts in your editor, run `pytest`, and push.

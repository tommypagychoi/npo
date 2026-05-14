# GitHub setup

This folder contains the Project Studio source prepared for the `npo` repository.

## Repository

Recommended repository name:

```text
npo
```

## First push

GitHub no longer accepts account passwords for Git operations. Use a Personal Access Token or GitHub CLI authentication.

```bash
git init
git branch -M main
git add .
git commit -m "Initial Project Studio source"
git remote add origin https://github.com/<OWNER>/npo.git
git push -u origin main
```

## Runtime secrets

Do not commit runtime secrets. Create `.env` on the server from `.env.example`.

Excluded by `.gitignore`:

```text
.env
*.pem
audit.log
.venv/
.local-pkgs/
__pycache__/
*.pyc
```

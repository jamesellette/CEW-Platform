## Commands: create repo (local & push)
Option 1 — Using GitHub CLI (recommended)
```bash
# create local folder and initialize
mkdir CEW-Platform
cd CEW-Platform
git init

# create files (use your editor to paste content from above), then:
git add .
git commit -m "Initial CEW Platform scaffold"

# create remote repo on GitHub (private)
gh repo create jamesellette/CEW-Platform --private --description "CEW Training Platform" --source=. --remote=origin --push
```

Option 2 — Create repo via GitHub web UI, then clone:
```bash
git clone git@github.com:jamesellette/CEW-Platform.git
cd CEW-Platform
# add files, commit, push
git add .
git commit -m "Initial scaffold"
git push origin main
```

---

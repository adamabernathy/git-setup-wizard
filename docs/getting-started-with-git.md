# Git & GitHub Workshop: Zero to Collaborating in One Hour

## The problem Git solves

You've emailed a file called `analysis_final_v3_REAL_final.py` to someone. They edited it. You also edited it. Now what?

Git is version control. It tracks every change anyone makes, and it gives you tools to merge those changes back together. That's it.

### How it works

A **repository** (repo) is just a folder that Git is watching. Every time you save a snapshot (called a **commit**), Git records exactly what changed.

A **branch** is a parallel copy of the code where you can work without breaking anything for everyone else.

```
main branch:   A ---- B ---- C
                              \
your branch:                   D ---- E
```

When you're done, you ask to **merge** your branch back into main. GitHub calls this a **Pull Request** (PR).

```
main branch:   A ---- B ---- C ----------- F  (merge commit)
                              \           /
your branch:                   D ---- E --
```

### Where things live

```
┌─────────────────────────────────────────────┐
│              GitHub (remote)                 │
│         the shared copy in the cloud         │
└──────────────────┬──────────────────────────┘
                   │  git push (upload)
                   │  git pull (download)
┌──────────────────▼──────────────────────────┐
│           Your Computer (local)              │
│       your private copy of the repo          │
└─────────────────────────────────────────────┘
```

---

## Setup and configure Git & GitHub

### Prerequisites

1. Create a GitHub account at https://github.com if you don't have one
2. Make sure you're signed in to GitHub in your browser

### Run the setup wizard

Open your terminal and paste this:

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/adamabernathy/git-setup-wizard/main/run.sh)
```

This downloads a small launcher that checks your Python install, grabs any missing packages, and starts the wizard. It handles everything: generating your SSH key, creating your GPG signing key, configuring Git, and walking you through adding both keys to GitHub. It opens the right GitHub pages automatically and copies each key to your clipboard. Just follow the prompts.

This code respects all your data and information, [feel free to inspect it here](https://github.com/adamabernathy/git-setup-wizard).

When it finishes, your machine is configured for SSH authentication and verified (signed) commits.

### Clone the practice repo

Now grab a repo to work with. Note the `git@github.com:` prefix. **That's the SSH URL, which is what you want now that SSH is configured**.

For example, you can grab the repo that created the setup code.

```bash
git clone git@github.com:adamabernathy/gitting-started-class.git
cd practice-repo
ls
```

The ["web" version of the practice repos is here](https://github.com/adamabernathy/gitting-started-class).

A Git repo is a folder with a hidden `.git` directory inside. Nothing magical.

```
practice-repo/
├── .git/          <-- hidden folder where Git stores everything
├── README.md
└── team.md
```

---

## The Core Loop

This is the entire session. Everything else is context for these commands.

```
┌─────────────────────────────────────────────────────┐
│                  THE CORE LOOP                       │
│                                                      │
│   1. git pull                  get latest changes    │
│   2. git checkout -b my-branch create your branch    │
│   3. ... make your edits ...                         │
│   4. git add .                 stage changes         │
│   5. git commit -m "message"   save a snapshot       │
│   6. git push                  send to GitHub        │
│   7. Open a Pull Request on GitHub                   │
│                                                      │
└─────────────────────────────────────────────────────┘
```

### What each step actually does

```
Working Directory          Staging Area              Local Repo              GitHub
(your files)               (ready to commit)         (saved snapshots)       (shared)

  edit files
      │
      ├── git add . ──────►  staged changes
      │                          │
      │                          ├── git commit ──────► new commit
      │                          │                         │
      │                          │                         ├── git push ──────► shared
      │                          │                         │
      ◄──────────────────────────────────────── git pull ──┘
```

### Live exercise

Everyone do this right now:

```bash
# 1. clone the code
git clone git@github.com:adamabernathy/gitting-started-class.git

# 2. Get the latest code
git pull

# 3. Create your own branch (use your name)
git checkout -b dallas-alice

# 4. Open team.md and add your name to the list
#    Use any text editor you like

# 5. Stage your changes
git add .

# 6. Commit with a short message
git commit -m "Add Dallas Alice to team list"

# 7. Push your branch to GitHub
git push
```

If Git says `--set-upstream`, just run the command it suggests. It's a one-time thing per branch.

Then go to GitHub, find the green **"Compare & pull request"** button, and open a PR.

We'll merge one together as a group. Then everyone runs `git pull` on main and watches the change appear locally. That's the moment it clicks.

```
You:       branch ──► push ──► Pull Request ──► merged into main
Everyone:                                              │
                                              git pull ◄┘
                                           (they see your changes)
```

---

## Merge Conflicts

This will happen, it's basically life.

A merge conflict occurs when two people edit the same line of the same file on different branches. Git doesn't know which version to keep, so it asks you.

### What it looks like

```
<<<<<<< HEAD
Alice's version of the line
=======
Bob's version of the line
>>>>>>> bob-branch
```

### What to do

1. Open the file
2. Decide which version to keep (or combine them)
3. Delete the conflict markers (`<<<<<<<`, `=======`, `>>>>>>>`)
4. Save, `git add .`, `git commit`

### Before and after

```
BEFORE (conflict markers in file):

    <<<<<<< HEAD
    team_size = 5
    =======
    team_size = 6
    >>>>>>> bob-branch

AFTER (you resolved it):

    team_size = 6
```

That's it. Pick the right version, delete the markers, commit.

---

## Checking out someone else's branch

At some point someone will open a PR and you'll want to actually run their code on your machine before approving it. Maybe the diff looks fine but you want to see it work. Maybe the changes are complex enough that reading them on GitHub isn't enough.

### The basic version

If the branch exists on the same repo (shared repo model), you can grab it directly:

```bash
# Make sure you have the latest branch list from GitHub
git fetch

# Check out their branch
git checkout alice/add-search

# You're now running their code. Look around, test it, run it.
```

Your files immediately change to match whatever is on that branch. Nothing you had before is lost. Git just swapped what's in your working directory. To go back:

```bash
git checkout main
```

### If you have uncommitted work

This is the most common snag. You're in the middle of something, a coworker asks you to review their PR, and you don't want to commit half-finished work just to switch branches.

`git stash` solves this. It shelves your changes temporarily:

```bash
# Save your in-progress work
git stash

# Now you can safely switch
git checkout alice/add-search

# ... test their code, look around ...

# Go back to your branch
git checkout your-branch

# Bring your work back
git stash pop
```

Everything is exactly where you left it.

### Using the gh CLI (easiest)

If you have the [GitHub CLI](using-gh-cli.md) installed, you can skip remembering the branch name entirely and just check out by PR number:

```bash
gh pr checkout 42
```

This fetches the branch and switches to it in one command. It works for PRs from forks too, which is where the manual approach gets annoying (you'd need to add their fork as a remote). The `gh` CLI handles that behind the scenes.

### What to actually do once you're on their branch

This depends on the project, but the general pattern:

```bash
# 1. Check out the PR
gh pr checkout 42

# 2. Install any new dependencies (if applicable)
npm install          # JavaScript
pip install -r requirements.txt   # Python
bundle install       # Ruby

# 3. Run the project
npm run dev          # or whatever the project uses
python main.py
./start.sh

# 4. Run the tests
npm test
pytest
make test

# 5. When you're done, go back to main
git checkout main
```

Step 2 matters more than people expect. If the PR added a new library and you don't install it, the code will fail and you'll think the PR is broken when it's actually fine. Check the diff for changes to `package.json`, `requirements.txt`, `Gemfile`, or whatever dependency file the project uses.

### The flow

```
Someone opens PR #42
        │
        ▼
gh pr checkout 42    (you're now on their branch)
        │
        ▼
install deps, run it, test it
        │
        ▼
gh pr review 42 --approve    (or --request-changes)
        │
        ▼
git checkout main    (back to your own work)
```

One thing to keep in mind: while you're on their branch, don't commit anything unless you've talked to them about it. If you spot a typo and want to fix it, push to their branch or leave a comment on the PR. Surprise commits on someone else's branch make for confusing git history.

---

## Cheat Sheet

Tape this next to your monitor for two weeks.

```
EVERYDAY COMMANDS
─────────────────────────────────────────────────
git pull                     get latest changes
git checkout -b branch-name  create a new branch
git add .                    stage all changes
git commit -m "message"      save a snapshot
git push                     send to GitHub

CHECKING WHAT'S GOING ON
─────────────────────────────────────────────────
git status                   what's changed?
git log --oneline            recent commit history
git diff                     see uncommitted changes

REVIEWING SOMEONE'S PR
─────────────────────────────────────────────────
gh pr checkout 42            get a PR's code locally
git checkout main            go back when done

USEFUL EXTRAS
─────────────────────────────────────────────────
git stash                    shelve changes temporarily
git stash pop                bring them back
git checkout main            switch back to main
git fetch                    update branch list from GitHub
git branch                   list your branches
git branch -d branch-name    delete a branch
```

---

## The One Rule

**Never force push to main.**

Everything else is recoverable. Git is almost comically hard to permanently lose work with, as long as you've committed it.

---

## Common Mistakes and Fixes

```
PROBLEM                          FIX
─────────────────────────────────────────────────────────────────
"I committed to main             git stash
 instead of a branch"            git checkout -b my-branch
                                 git stash pop

"I need to undo my               git reset HEAD~1
 last commit but keep             (keeps your changes, removes
 the changes"                     the commit)

"Git says I need to pull         git pull, then resolve any
 before I can push"              conflicts and push again

"I don't know what               git status
 state I'm in"                   (always safe to run)
```

---

## Team Workflows

There are two common ways teams organize their code on GitHub. Most teams start with the shared repo model and move to forks as the team or project grows. Both use branches and pull requests. The difference is where those branches live.

### Shared repo (everyone pushes to one repo)

This is what the core loop above describes. Everyone clones the same repo, makes branches, and opens PRs back into `main`. It's simple, and it works well for small to mid-size teams where everyone has write access.

```
               GitHub: your-org/project
              ┌────────────────────────┐
              │  main                  │
              │  alice/add-feature     │
              │  bob/fix-bug           │
              └────────────────────────┘
                  ▲            ▲
                  │            │
          Alice pushes    Bob pushes
          her branch      his branch
```

The daily cycle looks like this:

```bash
# Start of day: get the latest main
git checkout main
git pull

# Create a branch for your work
git checkout -b alice/add-feature

# ... do your work ...

git add .
git commit -m "Add search feature"
git push -u origin alice/add-feature

# Open a PR on GitHub, get it reviewed, merge
```

After merging, delete the branch (GitHub has a button for this) and pull main again. Repeat.

This model has one risk: anyone with write access can push directly to `main`. Protect against this by enabling branch protection rules on GitHub (Settings > Branches > Add rule > Require a pull request before merging). That way, all changes go through code review.

### Fork-based workflow (each person has their own copy)

In the fork model, the organization owns the "upstream" repo and each developer works from a personal copy (a "fork"). You push to your fork, then open PRs from your fork back to the upstream repo.

This is how open source projects work. It's also useful on larger teams because contributors don't need write access to the main repo, only to their own fork. The upstream repo stays clean.

```
               GitHub: your-org/project  (upstream)
              ┌────────────────────────┐
              │  main                  │◄──── PRs come here
              └────────────────────────┘
                  ▲              ▲
                  │              │
       ┌─────────┘              └──────────┐
       │                                   │
  alice/project (fork)              bob/project (fork)
  ┌──────────────┐              ┌──────────────┐
  │  main        │              │  main        │
  │  add-feature │              │  fix-bug     │
  └──────────────┘              └──────────────┘
```

#### Setting up a fork

Go to the upstream repo on GitHub and click **Fork** (top right). GitHub creates a copy under your account. Then:

```bash
# Clone YOUR fork, not the upstream repo
git clone git@github.com:your-username/project.git
cd project

# Add the upstream repo as a second remote called "upstream"
git remote add upstream git@github.com:your-org/project.git

# Verify you have both
git remote -v
# origin    git@github.com:your-username/project.git (fetch)
# origin    git@github.com:your-username/project.git (push)
# upstream  git@github.com:your-org/project.git (fetch)
# upstream  git@github.com:your-org/project.git (push)
```

You now have two remotes. `origin` is your fork. `upstream` is the team's repo.

#### The daily fork cycle

```bash
# 1. Sync your fork with the latest upstream changes
git checkout main
git fetch upstream
git merge upstream/main
git push origin main

# 2. Create a branch for your work (same as before)
git checkout -b add-feature

# 3. ... do your work ...

git add .
git commit -m "Add search feature"

# 4. Push to YOUR fork
git push -u origin add-feature

# 5. On GitHub: open a PR from your-username/project:add-feature
#    into your-org/project:main
```

The extra step compared to the shared model is keeping your fork's `main` in sync with upstream. That `fetch upstream / merge / push origin` sequence is the price you pay. It's not bad once it becomes muscle memory.

#### Quick sync alias

If you get tired of typing the sync commands, add this alias once:

```bash
git config --global alias.sync '!git fetch upstream && git merge upstream/main && git push origin main'
```

Then syncing your fork is just:

```bash
git checkout main
git sync
```

### Which model should you use?

For most internal teams of 2 to 15 people working on private repos, the shared repo model is simpler and that's what you should start with. Turn on branch protection so nobody accidentally pushes to `main`, and you're covered.

Move to forks when any of these are true: the repo is open source, you have external contributors who shouldn't have write access, or the team is large enough that branch clutter in the shared repo becomes a problem. You can also mix models. The core repo stays in the org, most of the team uses shared branches, and outside contributors use forks.

# Using the GitHub CLI

You've been switching between your terminal and the GitHub website every time you need to open a PR, check CI, or look at an issue. The `gh` CLI lets you do all of that without leaving your terminal. It's not a replacement for the web UI, but for the things you do ten times a day, it's faster.

This guide assumes you've gone through the Git workshop and are comfortable with branches, commits, and pull requests.

---

## Install and authenticate

```bash
brew install gh
```

Then connect it to your GitHub account:

```bash
gh auth login
```

It will ask you a few things. Pick these:

```
? What account do you want to log into?  GitHub.com
? What is your preferred protocol for Git operations?  SSH
? How would you like to authenticate GitHub CLI?  Login with a web browser
```

It opens a browser window. Sign in, paste the one-time code it shows you, and you're done.

Verify it worked:

```bash
gh auth status
```

You should see your username and the scopes it has access to. If you see an error, run `gh auth login` again.

---

## Repositories

### Clone a repo

You can clone by just naming the repo. No need to remember the full SSH URL.

```bash
gh repo clone your-org/project-name
```

That's equivalent to `git clone git@github.com:your-org/project-name.git` but shorter.

### View repo info

```bash
gh repo view
```

Prints the README and metadata for the current repo. Add `--web` to open it in your browser instead:

```bash
gh repo view --web
```

### Create a new repo

```bash
# Create a public repo from the current directory
gh repo create my-project --public --source=. --push

# Create a private repo
gh repo create my-project --private --source=. --push
```

The `--source=.` flag tells it to use the current folder, and `--push` pushes the initial commit.

### Fork a repo

```bash
gh repo fork your-org/project-name --clone
```

This forks the repo to your account and clones your fork locally. It also sets up the `upstream` remote automatically, which saves the manual `git remote add upstream` step from the workshop.

---

## Pull requests

This is where `gh` earns its keep. The PR workflow is the most common reason to reach for it.

### Create a PR

After you've pushed a branch:

```bash
gh pr create
```

It drops you into an interactive flow: pick a title, write a description, choose reviewers. If you want to skip the interactivity:

```bash
gh pr create --title "Add search feature" --body "Implements full-text search on the listings page"
```

To open the PR in your browser after creating it:

```bash
gh pr create --web
```

This is handy when you want GitHub's rich editor for the description.

### Add reviewers

```bash
gh pr create --reviewer alice,bob
```

Or add reviewers to an existing PR:

```bash
gh pr edit 42 --add-reviewer alice
```

### List open PRs

```bash
# All open PRs in the repo
gh pr list

# Just yours
gh pr list --author @me

# PRs waiting for your review
gh pr list --search "review-requested:@me"
```

### View a PR

```bash
# By number
gh pr view 42

# The one for your current branch
gh pr view
```

Add `--web` to open it in the browser, or `--comments` to see the discussion.

### Check CI status on a PR

```bash
gh pr checks
```

This shows the pass/fail status of every CI check on your current branch's PR. It's the fastest way to see if your build is green without opening GitHub.

To wait for checks to finish:

```bash
gh pr checks --watch
```

It polls until everything passes or fails. Useful after pushing a fix and wanting to know the result.

### Review a PR

```bash
# Approve
gh pr review 42 --approve

# Request changes
gh pr review 42 --request-changes --body "The timeout value needs to be configurable"

# Leave a comment without approving or blocking
gh pr review 42 --comment --body "Looks good overall, one small nit on line 34"
```

### Merge a PR

```bash
# Merge commit (default)
gh pr merge 42

# Squash merge (all your commits become one)
gh pr merge 42 --squash

# Rebase merge
gh pr merge 42 --rebase

# Auto-delete the branch after merge
gh pr merge 42 --squash --delete-branch
```

If branch protection requires reviews or passing checks, `gh` will tell you what's blocking the merge. You can also set it to merge automatically once checks pass:

```bash
gh pr merge 42 --auto --squash
```

### Checkout someone else's PR

Want to test a coworker's PR locally?

```bash
gh pr checkout 42
```

This fetches their branch and switches to it. When you're done, `git checkout main` to go back.

---

## Issues

### Create an issue

```bash
gh issue create --title "Search is broken on empty queries" --body "Steps to reproduce: ..."
```

Or interactively:

```bash
gh issue create
```

### Add labels and assignees

```bash
gh issue create --title "Fix login timeout" --assignee alice --label bug
```

### List issues

```bash
# All open issues
gh issue list

# Issues assigned to you
gh issue list --assignee @me

# Filter by label
gh issue list --label bug
```

### View an issue

```bash
gh issue view 15
gh issue view 15 --web     # open in browser
gh issue view 15 --comments # include discussion
```

### Close an issue

```bash
gh issue close 15
gh issue close 15 --reason completed
```

---

## GitHub Actions (CI/CD)

Actions are the automated workflows that run when you push code, open PRs, or on a schedule. The `gh` CLI lets you monitor and trigger them.

### List workflow runs

```bash
# Recent runs for the current repo
gh run list

# Filter by workflow name
gh run list --workflow test.yml

# Just your runs
gh run list --user @me
```

### View a specific run

```bash
gh run view 123456789
```

This shows the status of each job in the workflow. To see the full log output:

```bash
gh run view 123456789 --log
```

The logs can be long. To see just the failures:

```bash
gh run view 123456789 --log-failed
```

### Watch a run in progress

```bash
gh run watch
```

Picks the most recent run on your branch and streams the status until it finishes. Add `--exit-status` to make the command's exit code match the run result (useful in scripts).

### Re-run a failed workflow

```bash
gh run rerun 123456789

# Re-run only the failed jobs (faster)
gh run rerun 123456789 --failed
```

### Trigger a workflow manually

If a workflow has `workflow_dispatch` enabled:

```bash
gh workflow run deploy.yml
gh workflow run deploy.yml --ref main   # run against a specific branch
```

### List available workflows

```bash
gh workflow list
```

---

## Releases

Releases are how you ship versioned artifacts. Tags mark the point in history, releases attach binaries and changelogs.

### Create a release

```bash
# Create a release from the latest commit on main
gh release create v1.0.0 --title "v1.0.0" --notes "First stable release"

# Generate release notes automatically from merged PRs
gh release create v1.2.0 --generate-notes

# Create a draft release (not visible to others yet)
gh release create v2.0.0-rc1 --draft --generate-notes

# Attach files to the release
gh release create v1.0.0 ./dist/app.zip ./dist/app.tar.gz --generate-notes
```

### List releases

```bash
gh release list
```

### View a release

```bash
gh release view v1.0.0
```

### Download release assets

```bash
gh release download v1.0.0
gh release download v1.0.0 --pattern "*.zip"   # just the zip files
```

---

## Useful patterns

These are compound commands and aliases that come up often enough to be worth memorizing.

### Open the current repo in your browser

```bash
gh browse
```

Open a specific file:

```bash
gh browse src/main.py
```

### Create a branch, push, and open a PR in one flow

```bash
git checkout -b fix-login-bug
# ... make changes ...
git add .
git commit -m "Fix login timeout on slow connections"
git push -u origin fix-login-bug
gh pr create --fill
```

The `--fill` flag uses your commit message as the PR title and body. For a single-commit branch, this is usually exactly what you want.

### See what needs your attention

```bash
gh pr list --search "review-requested:@me"
gh issue list --assignee @me
```

### Set up shell aliases

Add these to your `~/.zshrc` if you find yourself typing the same things:

```bash
alias prc="gh pr create"
alias prs="gh pr list --search 'review-requested:@me'"
alias prm="gh pr merge --squash --delete-branch"
alias checks="gh pr checks --watch"
```

---

## Cheat sheet

```
PULL REQUESTS
──────────────────────────────────────────────────────
gh pr create                  open a new PR
gh pr create --fill           PR from commit message
gh pr list                    list open PRs
gh pr list --author @me       just your PRs
gh pr view 42                 view PR details
gh pr checks                  CI status
gh pr checks --watch          wait for CI
gh pr review 42 --approve     approve a PR
gh pr merge 42 --squash       squash merge
gh pr checkout 42             test someone's PR

ISSUES
──────────────────────────────────────────────────────
gh issue create               open a new issue
gh issue list                 list open issues
gh issue list --assignee @me  your issues
gh issue view 15              view issue details
gh issue close 15             close an issue

REPOS
──────────────────────────────────────────────────────
gh repo clone org/repo        clone a repo
gh repo fork org/repo         fork and clone
gh repo view --web            open repo in browser
gh browse                     open current repo

ACTIONS
──────────────────────────────────────────────────────
gh run list                   recent CI runs
gh run view ID --log-failed   see what broke
gh run watch                  stream current run
gh run rerun ID --failed      retry failed jobs
gh workflow run name.yml      trigger manually

RELEASES
──────────────────────────────────────────────────────
gh release create v1.0.0      create a release
gh release create v1.0.0 --generate-notes
gh release list               list releases
gh release download v1.0.0    download assets
```

---

## Getting help

Every `gh` command has a `--help` flag:

```bash
gh pr --help
gh pr create --help
```

The help output is well-written and usually has examples. If you forget the exact flag name, start there before searching online.

Full documentation is at https://cli.github.com/manual.

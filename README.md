# Git Setup Wizard

A terminal wizard that configures macOS for SSH authentication and GPG commit signing with GitHub.

## Quick start

```sh
bash <(curl -fsSL https://raw.githubusercontent.com/adamabernathy/git-setup-wizard/main/run.sh)
```

This downloads and runs the launcher, which checks for Python 3, installs the `rich` package if needed, and starts the wizard. Works in both zsh (macOS default) and bash.

## What it does

1. Generates an ed25519 SSH key and registers it with GitHub
2. Creates a GPG signing key for verified commits
3. Configures `git` to use both automatically
4. Verifies the full chain works

The wizard is idempotent. Running it twice won't duplicate keys or config entries.

## Requirements

- macOS (Apple Silicon or Intel)
- Python 3 (ships with macOS)
- A GitHub account

Homebrew, GnuPG, and pinentry-mac are installed automatically if missing.

## Running from a local clone

```sh
git clone git@github.com:adamabernathy/git-setup-wizard.git
cd git-setup-wizard
./run.sh
```

# Git Setup Wizard

A terminal wizard that configures macOS for SSH authentication and GPG commit signing with GitHub.

## One-liner install

```sh
python3 <(curl -fsSL https://raw.githubusercontent.com/adamabernathy/git-setup-wizard/main/git_setup_wizard.py)
```

This works in both zsh (macOS default) and bash. The `<(...)` syntax downloads the script without consuming stdin, so the interactive prompts work correctly.

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

## Manual run

```sh
python3 git_setup_wizard.py
```

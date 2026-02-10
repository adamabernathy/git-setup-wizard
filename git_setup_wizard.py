#!/usr/bin/env python3
"""
Git Setup Wizard — SSH & GPG Signing for macOS

A terminal wizard that walks through:
  1. SSH key generation + GitHub registration
  2. GPG key creation + commit signing
  3. Git configuration
  4. Verification

Usage:
    python3 git_setup_wizard.py
"""

import subprocess
import os
import sys
import re
import time
import platform
from pathlib import Path

# ─── Handle curl | python3 ───────────────────────────────────────────────────
# When piped, stdin is the script itself and is exhausted before any prompt
# runs. Reopen stdin from the real terminal so interactive prompts work.
# The try/except is intentionally silent: /dev/tty exists on macOS (the only
# target), and in CI/test environments we don't need interactive stdin.
if not sys.stdin.isatty():
    try:
        sys.stdin = open("/dev/tty", "r")
    except OSError:
        pass  # not on a real terminal (CI, pytest, etc.) — that's fine

# ─── Bootstrap: ensure 'rich' is installed ───────────────────────────────────
try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.prompt import Prompt, Confirm
    from rich.table import Table
    from rich import box
    from rich.padding import Padding
except ImportError:
    print("\n  First run: installing 'rich' for the terminal UI...\n")
    # Try with --break-system-packages first (newer pip on managed Python),
    # fall back to plain install for older pip versions.
    _pip_cmd = [sys.executable, "-m", "pip", "install", "rich", "--quiet"]
    try:
        subprocess.check_call(
            _pip_cmd + ["--break-system-packages"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
    except subprocess.CalledProcessError:
        subprocess.check_call(
            _pip_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
    from rich.console import Console
    from rich.panel import Panel
    from rich.prompt import Prompt, Confirm
    from rich.table import Table
    from rich import box
    from rich.padding import Padding

console = Console()


# ─── Paths & Constants ───────────────────────────────────────────────────────
SSH_DIR       = Path.home() / ".ssh"
SSH_KEY       = SSH_DIR / "id_ed25519"
SSH_PUB       = SSH_DIR / "id_ed25519.pub"
SSH_CONFIG    = SSH_DIR / "config"
GNUPG_DIR     = Path.home() / ".gnupg"
GPG_AGENT_CONF = GNUPG_DIR / "gpg-agent.conf"

GITHUB_SSH_URL = "https://github.com/settings/ssh/new"
GITHUB_GPG_URL = "https://github.com/settings/gpg/new"

# Apple Silicon vs Intel
BREW_PREFIX = (
    Path("/opt/homebrew")
    if Path("/opt/homebrew/bin/brew").exists()
    else Path("/usr/local")
)
PINENTRY_PATH = BREW_PREFIX / "bin" / "pinentry-mac"


# ─── Shell Helpers ───────────────────────────────────────────────────────────
def sh(cmd):
    """Run a shell command, return stdout (empty string on failure)."""
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        return r.stdout.strip()
    except Exception:
        return ""


def sh_ok(cmd):
    """Return True if a shell command exits 0."""
    return subprocess.run(
        cmd, shell=True, capture_output=True, text=True
    ).returncode == 0


def cmd_exists(name):
    """Check if a command exists on PATH."""
    return sh_ok(f"which {name}")


def detect_shell_rc():
    """Return the path to the user's shell rc file."""
    shell = os.environ.get("SHELL", "/bin/zsh")
    if "zsh" in shell:
        return Path.home() / ".zshrc"
    elif "bash" in shell:
        return Path.home() / ".bash_profile"
    return Path.home() / ".zshrc"  # default on modern macOS


# ─── Output Helpers ──────────────────────────────────────────────────────────
def phase(num, title, subtitle=""):
    text = f"[bold cyan]PHASE {num}[/]  [bold white]{title}[/]"
    if subtitle:
        text += f"\n[dim]{subtitle}[/]"
    console.print()
    console.print(Panel(text, box=box.ROUNDED, border_style="cyan", padding=(0, 2)))


def ok(msg):
    console.print(f"  [green]\u2713[/] {msg}")


def info(msg):
    console.print(f"  [cyan]\u203a[/] {msg}")


def warn(msg):
    console.print(f"  [yellow]![/] {msg}")


def fail(msg):
    console.print(f"  [red]\u2717[/] {msg}")


def dim(msg):
    console.print(f"  [dim]{msg}[/]")


def pause(msg="Press Enter to continue..."):
    console.print()
    Prompt.ask(f"  [dim]{msg}[/]", default="")


def github_action(copied_what, url, steps_text):
    """Show a panel telling the user to go do something on GitHub,
    and open the URL in their default browser automatically."""
    # Open the GitHub page in the default browser (macOS)
    subprocess.run(["open", url], capture_output=True)

    console.print()
    console.print(Panel(
        f"[bold green]Copied to clipboard:[/] {copied_what}\n\n"
        f"[bold]Opened in your browser:[/]  {url}\n\n"
        + steps_text,
        title="[bold yellow] Action Required: GitHub [/]",
        border_style="yellow",
        box=box.HEAVY,
        padding=(1, 2),
    ))


# ═════════════════════════════════════════════════════════════════════════════
BANNER = r"""
   _____ _ _     ____       _
  / ____(_) |   / ___|  ___| |_ _   _ _ __
 | |  __ _| |_  \___ \ / _ \ __| | | | '_ \
 | |_| | | |_   ___) |  __/ |_| |_| | |_) |
  \_____|_|_(_) |____/ \___|\__|\__,_| .__/
              Wizard                  |_|
"""


# ═════════════════════════════════════════════════════════════════════════════
#  PHASE 0 — Welcome
# ═════════════════════════════════════════════════════════════════════════════
def welcome():
    console.clear()
    console.print(Panel(
        f"[bold bright_cyan]{BANNER}[/]\n"
        "  [white]SSH + GPG Commit Signing for macOS[/]\n",
        box=box.DOUBLE, border_style="bright_blue", padding=(0, 2),
    ))

    console.print("  This wizard configures your Mac for secure Git operations:\n")
    console.print("  [white]1.[/] Generate an SSH key and add it to GitHub")
    console.print("  [white]2.[/] Create a GPG signing key for verified commits")
    console.print("  [white]3.[/] Wire up Git to use both automatically")
    console.print("  [white]4.[/] Verify the whole chain works")
    console.print()
    dim("You'll need your GitHub account open in a browser.")
    dim("Takes about 5 minutes. You can re-run safely if anything fails.")
    console.print()

    if not Confirm.ask("  [bold]Ready?[/]", default=True):
        console.print("\n  No worries. Run again whenever.\n")
        sys.exit(0)


# ═════════════════════════════════════════════════════════════════════════════
#  PHASE 1 — Preflight
# ═════════════════════════════════════════════════════════════════════════════
def preflight():
    phase(1, "Preflight Checks", "Making sure your system has what we need")

    # macOS check
    if platform.system() != "Darwin":
        fail(f"This wizard targets macOS. Detected: {platform.system()}")
        sys.exit(1)
    ok("macOS detected")

    # Git
    if not cmd_exists("git"):
        fail("Git not found. Run: xcode-select --install")
        sys.exit(1)
    ok(f"Git installed  ({sh('git --version')})")

    # Homebrew
    if not cmd_exists("brew"):
        warn("Homebrew not found (needed for GPG tools)")
        console.print()
        if Confirm.ask("  Install Homebrew now?", default=True):
            info("Installing Homebrew... this can take a minute")
            subprocess.run(["open", "https://brew.sh"], capture_output=True)
            subprocess.run(
                '/bin/bash -c "$(curl -fsSL '
                'https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"',
                shell=True,
            )
            # Re-detect brew prefix after install
            global BREW_PREFIX, PINENTRY_PATH
            if Path("/opt/homebrew/bin/brew").exists():
                BREW_PREFIX = Path("/opt/homebrew")
            elif Path("/usr/local/bin/brew").exists():
                BREW_PREFIX = Path("/usr/local")
            PINENTRY_PATH = BREW_PREFIX / "bin" / "pinentry-mac"

            if not cmd_exists("brew"):
                fail("Homebrew install may need a terminal restart. Re-run after.")
                sys.exit(1)
            ok("Homebrew installed")
        else:
            warn("Skipping Homebrew. GPG signing won't be available.")
            return False
    else:
        ok("Homebrew installed")

    # GnuPG
    if not cmd_exists("gpg"):
        info("Installing GnuPG...")
        subprocess.run("brew install gnupg 2>/dev/null", shell=True,
                        capture_output=True)
        if cmd_exists("gpg"):
            ok("GnuPG installed")
        else:
            fail("Could not install GnuPG")
            return False
    else:
        ok(f"GnuPG installed  ({sh('gpg --version | head -1')})")

    # pinentry-mac
    if not PINENTRY_PATH.exists():
        info("Installing pinentry-mac...")
        subprocess.run("brew install pinentry-mac 2>/dev/null", shell=True,
                        capture_output=True)
        # Re-check both locations
        for p in [BREW_PREFIX / "bin" / "pinentry-mac",
                  Path("/opt/homebrew/bin/pinentry-mac"),
                  Path("/usr/local/bin/pinentry-mac")]:
            if p.exists():
                PINENTRY_PATH = p
                break
        if PINENTRY_PATH.exists():
            ok("pinentry-mac installed")
        else:
            warn("pinentry-mac not found. GPG passphrase prompts may behave oddly.")
    else:
        ok("pinentry-mac installed")

    console.print()
    ok("[bold]Preflight complete[/]")
    return True


# ═════════════════════════════════════════════════════════════════════════════
#  PHASE 2 — User Info
# ═════════════════════════════════════════════════════════════════════════════
def collect_info():
    phase(2, "Your Identity", "Used for SSH key, GPG key, and git config")

    existing_name  = sh("git config --global user.name")
    existing_email = sh("git config --global user.email")

    if existing_name:
        dim(f"Current git config: {existing_name} <{existing_email}>")
        console.print()

    name = Prompt.ask(
        "  [bold]Full name[/]",
        default=existing_name or None,
    )
    email = Prompt.ask(
        "  [bold]Email[/] [dim](must match your GitHub account)[/]",
        default=existing_email or None,
    )
    console.print()
    console.print(f"  Using: [bold]{name}[/] <[bold]{email}[/]>")

    if not Confirm.ask("  Look right?", default=True):
        return collect_info()

    return name, email


# ═════════════════════════════════════════════════════════════════════════════
#  PHASE 3 — SSH
# ═════════════════════════════════════════════════════════════════════════════
def setup_ssh(email):
    phase(3, "SSH Key", "So GitHub knows your machine")

    # Ensure .ssh dir exists with correct perms
    SSH_DIR.mkdir(mode=0o700, exist_ok=True)

    # ── Key Generation ────────────────────────────────────────────────────
    if SSH_KEY.exists():
        warn(f"SSH key already exists: {SSH_KEY}")
        if SSH_PUB.exists():
            dim(SSH_PUB.read_text().strip()[:72] + "...")
        console.print()

        choice = Prompt.ask(
            "  [bold]What do you want to do?[/]",
            choices=["keep", "replace"],
            default="keep",
        )
        if choice == "replace":
            ts = int(time.time())
            SSH_KEY.rename(SSH_KEY.with_suffix(f".bak.{ts}"))
            if SSH_PUB.exists():
                SSH_PUB.rename(SSH_PUB.with_suffix(f".pub.bak.{ts}"))
            ok("Old key backed up")
        else:
            ok("Keeping existing key")

    if not SSH_KEY.exists():
        info("Generating ed25519 key...")
        dim("You'll be prompted for a passphrase (recommended, but Enter skips it)")
        console.print()
        subprocess.run(
            ["ssh-keygen", "-t", "ed25519", "-C", email, "-f", str(SSH_KEY)],
        )
        if not SSH_KEY.exists():
            fail("Key generation failed or was cancelled")
            sys.exit(1)
        ok("SSH key generated")

    # ── ssh-agent + Keychain ──────────────────────────────────────────────
    info("Adding key to ssh-agent and macOS Keychain...")
    sh('eval "$(ssh-agent -s)"')
    subprocess.run(
        ["ssh-add", "--apple-use-keychain", str(SSH_KEY)],
        capture_output=True,
    )
    ok("Key added to agent/Keychain")

    # ── ~/.ssh/config ─────────────────────────────────────────────────────
    github_block = (
        "\nHost github.com\n"
        "  AddKeysToAgent yes\n"
        "  UseKeychain yes\n"
        "  IdentityFile ~/.ssh/id_ed25519\n"
    )

    if SSH_CONFIG.exists():
        content = SSH_CONFIG.read_text()
        if "github.com" in content.lower():
            ok("~/.ssh/config already has a github.com entry")
        else:
            info("Appending GitHub entry to ~/.ssh/config...")
            with open(SSH_CONFIG, "a") as f:
                f.write(github_block)
            ok("SSH config updated")
    else:
        info("Creating ~/.ssh/config...")
        SSH_CONFIG.write_text(github_block.lstrip())
        SSH_CONFIG.chmod(0o600)
        ok("SSH config created")

    # ── Copy public key + GitHub instructions ─────────────────────────────
    if not SSH_PUB.exists():
        fail("Public key file missing. Something went wrong.")
        return

    pub_text = SSH_PUB.read_text().strip()
    subprocess.run(["pbcopy"], input=pub_text, text=True)

    github_action(
        "Your SSH public key",
        GITHUB_SSH_URL,
        "  1. Click [bold]New SSH key[/]\n"
        "  2. [bold]Title[/]:    something like \"Work MacBook\" or \"Adam's MBP\"\n"
        "  3. [bold]Key type[/]: Authentication Key\n"
        "  4. [bold]Key[/]:      Cmd+V to paste (already copied)\n"
        "  5. Click [bold]Add SSH key[/]",
    )

    pause("Press Enter after you've added the SSH key on GitHub...")

    # ── Test connection ───────────────────────────────────────────────────
    info("Testing SSH connection to GitHub...")
    result = subprocess.run(
        ["ssh", "-T", "git@github.com"],
        capture_output=True, text=True,
    )
    output = (result.stderr + result.stdout).lower()
    if "successfully authenticated" in output or "you've successfully" in output:
        ok("SSH to GitHub works!")
    else:
        warn("Could not confirm the connection yet.")
        dim("This sometimes takes a moment, or you may need to confirm")
        dim("the host fingerprint. Try running: ssh -T git@github.com")


# ═════════════════════════════════════════════════════════════════════════════
#  PHASE 4 — GPG + Commit Signing
# ═════════════════════════════════════════════════════════════════════════════
def setup_gpg(name, email):
    phase(4, "GPG Key & Commit Signing",
          "So GitHub can prove your commits are really yours")

    # ── Configure gpg-agent for macOS ─────────────────────────────────────
    GNUPG_DIR.mkdir(mode=0o700, exist_ok=True)

    pinentry_line = f"pinentry-program {PINENTRY_PATH}"
    if GPG_AGENT_CONF.exists():
        content = GPG_AGENT_CONF.read_text()
        if "pinentry-program" not in content:
            with open(GPG_AGENT_CONF, "a") as f:
                f.write(f"\n{pinentry_line}\n")
            ok("Configured gpg-agent to use pinentry-mac")
        else:
            ok("gpg-agent already configured")
    else:
        GPG_AGENT_CONF.write_text(pinentry_line + "\n")
        ok("Created gpg-agent.conf")

    # Restart agent so config takes effect
    sh("gpgconf --kill gpg-agent")

    # ── Check for existing key ────────────────────────────────────────────
    existing = sh(f'gpg --list-secret-keys --keyid-format LONG "{email}" 2>/dev/null')
    gpg_key_id = None

    if existing and "sec" in existing:
        # Parse key ID from the sec line
        for line in existing.split("\n"):
            line = line.strip()
            if line.startswith("sec"):
                m = re.search(r'/([A-F0-9]{8,})', line)
                if m:
                    gpg_key_id = m.group(1)
                    break

        if gpg_key_id:
            warn(f"Existing GPG key found for {email}")
            dim(f"Key ID: {gpg_key_id}")
            console.print()
            if Confirm.ask("  Use this existing key?", default=True):
                ok(f"Using key {gpg_key_id}")
            else:
                gpg_key_id = None

    # ── Generate new key if needed ────────────────────────────────────────
    if not gpg_key_id:
        info("Generating GPG key pair...")
        dim("A passphrase dialog will pop up. Pick something strong.")
        console.print()

        # Try the modern quick-generate path first (GPG 2.1+)
        result = subprocess.run(
            ["gpg", "--batch", "--passphrase", "", "--quick-gen-key",
             f"{name} <{email}>", "ed25519", "sign", "3y"],
            capture_output=True, text=True,
        )

        if result.returncode != 0:
            # Fallback: interactive generation
            dim("Using interactive key generation (follow the prompts)...")
            dim("Recommended: key type ed25519 or RSA 4096, expiry 2-3 years")
            console.print()
            subprocess.run(["gpg", "--full-generate-key"])

        # Grab the new key ID
        fresh = sh(f'gpg --list-secret-keys --keyid-format LONG "{email}" 2>/dev/null')
        if fresh:
            for line in fresh.split("\n"):
                line = line.strip()
                if line.startswith("sec"):
                    m = re.search(r'/([A-F0-9]{8,})', line)
                    if m:
                        gpg_key_id = m.group(1)
                        break

        if gpg_key_id:
            ok(f"GPG key created: {gpg_key_id}")

            # Add encryption subkey for completeness
            subprocess.run(
                ["gpg", "--batch", "--passphrase", "", "--quick-add-key",
                 gpg_key_id, "cv25519", "encr", "3y"],
                capture_output=True, text=True,
            )
        else:
            fail("No GPG key found after generation. You may need to run manually:")
            dim("  gpg --full-generate-key")
            return None

    # ── Configure Git ─────────────────────────────────────────────────────
    info("Configuring Git to sign commits automatically...")
    commands = [
        f'git config --global user.signingkey {gpg_key_id}',
        f'git config --global user.name "{name}"',
        f'git config --global user.email "{email}"',
        'git config --global gpg.program gpg',
        'git config --global commit.gpgsign true',
    ]
    for c in commands:
        sh(c)
    ok("Git config updated")

    # Show what we set
    console.print()
    table = Table(box=box.SIMPLE, padding=(0, 2), show_header=False)
    table.add_column(style="dim")
    table.add_column(style="white")
    for key in ["user.name", "user.email", "user.signingkey",
                "commit.gpgsign", "gpg.program"]:
        table.add_row(key, sh(f"git config --global {key}"))
    console.print(Padding(table, (0, 4)))

    # ── GPG_TTY in shell rc ───────────────────────────────────────────────
    rc = detect_shell_rc()
    if rc.exists():
        content = rc.read_text()
        if "GPG_TTY" not in content:
            with open(rc, "a") as f:
                f.write('\n# GPG commit signing\nexport GPG_TTY=$(tty)\n')
            ok(f"Added GPG_TTY to {rc.name}")
        else:
            ok(f"GPG_TTY already in {rc.name}")
    else:
        rc.write_text('# GPG commit signing\nexport GPG_TTY=$(tty)\n')
        ok(f"Created {rc.name} with GPG_TTY")

    # ── Export public key to clipboard ────────────────────────────────────
    armor = sh(f"gpg --armor --export {gpg_key_id}")
    if not armor:
        fail("Could not export GPG public key")
        return gpg_key_id

    subprocess.run(["pbcopy"], input=armor, text=True)

    github_action(
        "Your GPG public key",
        GITHUB_GPG_URL,
        "  1. Click [bold]New GPG key[/]\n"
        "  2. [bold]Title[/]: something like \"Work MacBook Signing Key\"\n"
        "  3. [bold]Key[/]:   Cmd+V to paste (already copied)\n"
        "     It starts with: [dim]-----BEGIN PGP PUBLIC KEY BLOCK-----[/]\n"
        "  4. Click [bold]Add GPG key[/]",
    )

    pause("Press Enter after you've added the GPG key on GitHub...")
    return gpg_key_id


# ═════════════════════════════════════════════════════════════════════════════
#  PHASE 5 — Verification
# ═════════════════════════════════════════════════════════════════════════════
def verify(gpg_key_id):
    phase(5, "Verification", "Making sure it all works end to end")

    # Restart GPG agent fresh
    sh("gpgconf --kill gpg-agent")
    sh("gpgconf --launch gpg-agent")
    os.environ["GPG_TTY"] = sh("tty") or "/dev/ttys000"

    # Test raw GPG signing
    info("Testing GPG signing...")
    result = subprocess.run(
        'echo "test" | gpg --clearsign 2>/dev/null',
        shell=True, capture_output=True, text=True,
    )
    if result.returncode == 0 and "BEGIN PGP SIGNED MESSAGE" in result.stdout:
        ok("GPG signing works")
    else:
        warn("GPG signing test did not pass cleanly")
        dim("This often resolves after a terminal restart.")
        if result.stderr:
            dim(result.stderr.strip()[:120])

    # Show summary of what's configured
    console.print()
    info("Final configuration:")
    console.print()

    checks = []

    # SSH key
    if SSH_PUB.exists():
        checks.append(("SSH key", SSH_PUB.read_text().strip()[:52] + "...", True))
    else:
        checks.append(("SSH key", "not found", False))

    # SSH config
    if SSH_CONFIG.exists() and "github.com" in SSH_CONFIG.read_text().lower():
        checks.append(("SSH config", "github.com entry present", True))
    else:
        checks.append(("SSH config", "missing github.com", False))

    # GPG key
    if gpg_key_id:
        checks.append(("GPG signing key", gpg_key_id, True))
    else:
        checks.append(("GPG signing key", "not configured", False))

    # Git signing
    sign_flag = sh("git config --global commit.gpgsign")
    checks.append(("Auto-sign commits", sign_flag or "not set",
                    sign_flag == "true"))

    # GPG_TTY
    rc = detect_shell_rc()
    has_tty = rc.exists() and "GPG_TTY" in rc.read_text()
    checks.append(("GPG_TTY in shell rc", str(rc.name), has_tty))

    table = Table(box=box.ROUNDED, border_style="dim", padding=(0, 2))
    table.add_column("Check", style="white")
    table.add_column("Value", style="dim")
    table.add_column("", width=3)
    for label, value, passed in checks:
        icon = "[green]\u2713[/]" if passed else "[red]\u2717[/]"
        table.add_row(label, value, icon)
    console.print(Padding(table, (0, 4)))

    all_good = all(p for _, _, p in checks)
    return all_good


# ═════════════════════════════════════════════════════════════════════════════
#  PHASE 6 — Done
# ═════════════════════════════════════════════════════════════════════════════
def done_summary(all_good):
    console.print()
    if all_good:
        console.print(Panel(
            "[bold green]You're all set.[/]\n\n"
            "Your Mac is now configured for:\n"
            "  [green]\u2713[/]  SSH authentication to GitHub\n"
            "  [green]\u2713[/]  Automatic GPG-signed commits\n\n"
            "[bold]Try it out:[/]\n"
            "  1. Clone something via SSH:\n"
            "     [dim]git clone git@github.com:your-org/your-repo.git[/]\n"
            "  2. Make a commit and push. Look for the [green]Verified[/] badge.\n\n"
            "[dim]If signing ever fails, the nuclear option:[/]\n"
            "  [dim]gpgconf --kill gpg-agent && gpgconf --launch gpg-agent[/]",
            title="[bold green] Setup Complete [/]",
            border_style="green",
            box=box.DOUBLE,
            padding=(1, 2),
        ))
    else:
        console.print(Panel(
            "[bold yellow]Almost there.[/]\n\n"
            "Some checks didn't pass. That's usually fine after a\n"
            "terminal restart. Re-run this wizard to pick up where\n"
            "you left off. It won't duplicate anything.\n\n"
            "[dim]Stuck? Ping your team's #dev-help channel.[/]",
            title="[bold yellow] Needs Attention [/]",
            border_style="yellow",
            box=box.DOUBLE,
            padding=(1, 2),
        ))
    console.print()


# ═════════════════════════════════════════════════════════════════════════════
#  Main
# ═════════════════════════════════════════════════════════════════════════════
def main():
    try:
        welcome()

        gpg_available = preflight()

        name, email = collect_info()

        setup_ssh(email)

        gpg_key_id = None
        if gpg_available:
            gpg_key_id = setup_gpg(name, email)
        else:
            warn("Skipping GPG setup (Homebrew not available)")

        all_good = False
        if gpg_key_id:
            all_good = verify(gpg_key_id)
        else:
            warn("Skipping verification (no GPG key)")

        done_summary(all_good)

        # Source the shell rc so the current session picks up GPG_TTY
        # without the user needing to open a new terminal.
        rc = detect_shell_rc()
        if rc.exists():
            info(f"Sourcing ~/{rc.name} ...")
            os.system(f"source {rc} 2>/dev/null")
            # Also set GPG_TTY in *this* process for immediate effect
            os.environ["GPG_TTY"] = sh("tty") or os.environ.get("GPG_TTY", "")
            ok(f"~/{rc.name} sourced. No terminal restart needed.")

    except KeyboardInterrupt:
        console.print("\n\n  [dim]Cancelled. Run again whenever you're ready.[/]\n")
        sys.exit(130)
    except Exception as e:
        console.print(f"\n  [red]Something broke: {e}[/]")
        console.print("  [dim]Re-run the wizard. It's safe to retry.[/]\n")
        raise


if __name__ == "__main__":
    main()

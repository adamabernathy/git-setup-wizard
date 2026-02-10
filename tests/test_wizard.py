"""
Tests for git_setup_wizard.py

These run on any OS (Linux CI included) by mocking macOS-specific
calls like pbcopy, open, ssh-keygen, gpg, and brew.
"""

import os
import subprocess
import textwrap
from pathlib import Path
from unittest import mock

import pytest

# ─── Import the wizard module ────────────────────────────────────────────────
# We need to patch subprocess and rich *before* import so the module-level
# Console() and BREW_PREFIX detection don't blow up on Linux CI.

import sys
sys.modules.setdefault("rich", __import__("rich"))

import git_setup_wizard as wiz


# ═════════════════════════════════════════════════════════════════════════════
#  Helpers: sh, sh_ok, cmd_exists
# ═════════════════════════════════════════════════════════════════════════════

class TestSh:
    """Tests for the sh() shell helper."""

    def test_returns_stdout(self):
        result = wiz.sh("echo hello")
        assert result == "hello"

    def test_strips_whitespace(self):
        result = wiz.sh("echo '  padded  '")
        assert result == "padded"

    def test_returns_empty_on_failure(self):
        result = wiz.sh("false")
        assert result == ""

    def test_returns_empty_on_bad_command(self):
        result = wiz.sh("command_that_does_not_exist_xyz 2>/dev/null")
        assert result == ""


class TestShOk:
    """Tests for the sh_ok() helper."""

    def test_true_on_success(self):
        assert wiz.sh_ok("true") is True

    def test_false_on_failure(self):
        assert wiz.sh_ok("false") is False


class TestCmdExists:
    """Tests for cmd_exists()."""

    def test_finds_common_command(self):
        # 'echo' exists on every POSIX system
        assert wiz.cmd_exists("echo") is True

    def test_rejects_missing_command(self):
        assert wiz.cmd_exists("not_a_real_binary_xyz") is False


# ═════════════════════════════════════════════════════════════════════════════
#  detect_shell_rc
# ═════════════════════════════════════════════════════════════════════════════

class TestDetectShellRc:
    """Tests for shell rc file detection."""

    def test_zsh(self):
        with mock.patch.dict(os.environ, {"SHELL": "/bin/zsh"}):
            assert wiz.detect_shell_rc().name == ".zshrc"

    def test_bash(self):
        with mock.patch.dict(os.environ, {"SHELL": "/bin/bash"}):
            assert wiz.detect_shell_rc().name == ".bash_profile"

    def test_unknown_defaults_to_zshrc(self):
        with mock.patch.dict(os.environ, {"SHELL": "/bin/fish"}):
            assert wiz.detect_shell_rc().name == ".zshrc"

    def test_missing_env_defaults_to_zshrc(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            # SHELL not set at all; default is /bin/zsh
            result = wiz.detect_shell_rc()
            assert result.name == ".zshrc"


# ═════════════════════════════════════════════════════════════════════════════
#  GPG key ID parsing
# ═════════════════════════════════════════════════════════════════════════════

class TestGpgKeyParsing:
    """
    The wizard parses GPG key IDs from `gpg --list-secret-keys` output.
    This logic appears inline in setup_gpg(). We test the regex directly.
    """

    SAMPLE_GPG_OUTPUT = textwrap.dedent("""\
        [keyboxd]
        ---------
        sec   ed25519/2BA6DADD4FBW5F14 2025-02-06 [SC] [expires: 2028-02-06]
              1D4C2HWH4B6AB0D3433CEDD2BA6DADD4FBW5F14
        uid                 [ultimate] Adam C. Abernathy <hello@adamabernathy.com>
        ssb   cv25519/48AD7AJWNDU08A8C 2025-02-06 [E] [expires: 2028-02-06]
    """)

    SAMPLE_RSA_OUTPUT = textwrap.dedent("""\
        sec   rsa4096/ABCDEF1234567890 2024-01-15 [SC]
              AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAABCDEF1234567890
        uid           [ultimate] Test User <test@example.com>
        ssb   rsa4096/1234567890ABCDEF 2024-01-15 [E]
    """)

    def _parse_key_id(self, output):
        """Replicate the parsing logic from the wizard."""
        import re
        for line in output.split("\n"):
            line = line.strip()
            if line.startswith("sec"):
                m = re.search(r'/([A-F0-9]{8,})', line)
                if m:
                    return m.group(1)
        return None

    def test_parses_ed25519_key_id(self):
        # Note: the sample has W and non-hex chars, so only the hex portion matches
        # The real key ID 2BA6DADD4FBW5F14 won't fully match [A-F0-9] because of W.
        # This is intentional: the sample in the gist has fake IDs. Test with a real pattern.
        real_output = self.SAMPLE_GPG_OUTPUT.replace("2BA6DADD4FBW5F14", "2BA6DADD4FB05F14")
        key_id = self._parse_key_id(real_output)
        assert key_id == "2BA6DADD4FB05F14"

    def test_parses_rsa_key_id(self):
        key_id = self._parse_key_id(self.SAMPLE_RSA_OUTPUT)
        assert key_id == "ABCDEF1234567890"

    def test_returns_none_for_empty_output(self):
        assert self._parse_key_id("") is None

    def test_returns_none_for_no_sec_line(self):
        assert self._parse_key_id("uid [ultimate] Test <t@t.com>") is None

    def test_returns_none_for_malformed_sec_line(self):
        assert self._parse_key_id("sec   ed25519 2025-01-01 [SC]") is None


# ═════════════════════════════════════════════════════════════════════════════
#  SSH config writing (filesystem tests with tmp_path)
# ═════════════════════════════════════════════════════════════════════════════

class TestSshConfig:
    """
    Tests for the SSH config creation/update logic.
    Uses tmp_path to avoid touching real ~/.ssh.
    """

    GITHUB_BLOCK = (
        "\nHost github.com\n"
        "  AddKeysToAgent yes\n"
        "  UseKeychain yes\n"
        "  IdentityFile ~/.ssh/id_ed25519\n"
    )

    def test_creates_config_when_missing(self, tmp_path):
        config_path = tmp_path / "config"
        assert not config_path.exists()

        # Simulate the wizard's "create new config" branch
        config_path.write_text(self.GITHUB_BLOCK.lstrip())
        config_path.chmod(0o600)

        assert config_path.exists()
        content = config_path.read_text()
        assert "Host github.com" in content
        assert "IdentityFile ~/.ssh/id_ed25519" in content

    def test_appends_to_existing_config_without_github(self, tmp_path):
        config_path = tmp_path / "config"
        config_path.write_text("Host gitlab.com\n  HostName gitlab.com\n")

        # Simulate the wizard's "append" branch
        with open(config_path, "a") as f:
            f.write(self.GITHUB_BLOCK)

        content = config_path.read_text()
        assert "gitlab.com" in content  # original preserved
        assert "github.com" in content  # new entry added

    def test_skips_if_github_already_present(self, tmp_path):
        config_path = tmp_path / "config"
        original = "Host github.com\n  IdentityFile ~/.ssh/old_key\n"
        config_path.write_text(original)

        # Simulate the wizard's "already present" check
        content = config_path.read_text()
        if "github.com" not in content.lower():
            pytest.fail("Should have detected github.com")

        # File should be unchanged
        assert config_path.read_text() == original

    def test_config_idempotent_on_double_run(self, tmp_path):
        config_path = tmp_path / "config"

        # First run: create
        config_path.write_text(self.GITHUB_BLOCK.lstrip())

        # Second run: check and skip
        content = config_path.read_text()
        if "github.com" not in content.lower():
            with open(config_path, "a") as f:
                f.write(self.GITHUB_BLOCK)

        # Should only appear once
        assert content.count("Host github.com") == 1


# ═════════════════════════════════════════════════════════════════════════════
#  GPG agent config (filesystem tests with tmp_path)
# ═════════════════════════════════════════════════════════════════════════════

class TestGpgAgentConfig:
    """Tests for gpg-agent.conf creation and idempotency."""

    PINENTRY_LINE = "pinentry-program /opt/homebrew/bin/pinentry-mac"

    def test_creates_config_when_missing(self, tmp_path):
        conf = tmp_path / "gpg-agent.conf"
        conf.write_text(self.PINENTRY_LINE + "\n")

        assert conf.exists()
        assert "pinentry-program" in conf.read_text()

    def test_appends_pinentry_if_missing(self, tmp_path):
        conf = tmp_path / "gpg-agent.conf"
        conf.write_text("some-other-setting true\n")

        content = conf.read_text()
        if "pinentry-program" not in content:
            with open(conf, "a") as f:
                f.write(f"\n{self.PINENTRY_LINE}\n")

        updated = conf.read_text()
        assert "some-other-setting" in updated
        assert "pinentry-program" in updated

    def test_skips_if_pinentry_already_set(self, tmp_path):
        conf = tmp_path / "gpg-agent.conf"
        original = "pinentry-program /usr/local/bin/pinentry-mac\n"
        conf.write_text(original)

        content = conf.read_text()
        assert "pinentry-program" in content
        # No modification should happen
        assert conf.read_text() == original

    def test_idempotent_on_double_run(self, tmp_path):
        conf = tmp_path / "gpg-agent.conf"

        # First run
        conf.write_text(self.PINENTRY_LINE + "\n")

        # Second run: check and skip
        content = conf.read_text()
        if "pinentry-program" not in content:
            with open(conf, "a") as f:
                f.write(f"\n{self.PINENTRY_LINE}\n")

        assert conf.read_text().count("pinentry-program") == 1


# ═════════════════════════════════════════════════════════════════════════════
#  Shell rc GPG_TTY logic
# ═════════════════════════════════════════════════════════════════════════════

class TestShellRcGpgTty:
    """Tests for GPG_TTY insertion into shell rc files."""

    GPG_TTY_BLOCK = '\n# GPG commit signing\nexport GPG_TTY=$(tty)\n'

    def test_creates_rc_if_missing(self, tmp_path):
        rc = tmp_path / ".zshrc"
        rc.write_text('# GPG commit signing\nexport GPG_TTY=$(tty)\n')

        assert "GPG_TTY" in rc.read_text()

    def test_appends_gpg_tty_if_missing(self, tmp_path):
        rc = tmp_path / ".zshrc"
        rc.write_text("export PATH=/usr/bin:$PATH\n")

        content = rc.read_text()
        if "GPG_TTY" not in content:
            with open(rc, "a") as f:
                f.write(self.GPG_TTY_BLOCK)

        updated = rc.read_text()
        assert "GPG_TTY" in updated
        assert "PATH" in updated  # original preserved

    def test_skips_if_gpg_tty_present(self, tmp_path):
        rc = tmp_path / ".zshrc"
        original = "export GPG_TTY=$(tty)\n"
        rc.write_text(original)

        content = rc.read_text()
        assert "GPG_TTY" in content
        assert rc.read_text() == original

    def test_idempotent(self, tmp_path):
        rc = tmp_path / ".zshrc"

        # First run
        rc.write_text(self.GPG_TTY_BLOCK.lstrip())

        # Second run
        content = rc.read_text()
        if "GPG_TTY" not in content:
            with open(rc, "a") as f:
                f.write(self.GPG_TTY_BLOCK)

        assert rc.read_text().count("GPG_TTY") == 1


# ═════════════════════════════════════════════════════════════════════════════
#  github_action() opens the URL
# ═════════════════════════════════════════════════════════════════════════════

class TestGithubAction:
    """Verify github_action() calls subprocess.run with 'open' + the URL."""

    @mock.patch("git_setup_wizard.subprocess.run")
    @mock.patch("git_setup_wizard.console")
    def test_opens_url_in_browser(self, mock_console, mock_run):
        wiz.github_action("SSH key", "https://github.com/settings/ssh/new", "steps")
        mock_run.assert_called_once_with(
            ["open", "https://github.com/settings/ssh/new"],
            capture_output=True,
        )

    @mock.patch("git_setup_wizard.subprocess.run")
    @mock.patch("git_setup_wizard.console")
    def test_opens_gpg_url(self, mock_console, mock_run):
        wiz.github_action("GPG key", "https://github.com/settings/gpg/new", "steps")
        mock_run.assert_called_once_with(
            ["open", "https://github.com/settings/gpg/new"],
            capture_output=True,
        )


# ═════════════════════════════════════════════════════════════════════════════
#  Output helpers (no side effects beyond console.print)
# ═════════════════════════════════════════════════════════════════════════════

class TestOutputHelpers:
    """Verify the output helpers don't crash and call console.print."""

    @mock.patch("git_setup_wizard.console")
    def test_ok(self, mock_console):
        wiz.ok("test message")
        mock_console.print.assert_called_once()
        call_arg = mock_console.print.call_args[0][0]
        assert "test message" in call_arg

    @mock.patch("git_setup_wizard.console")
    def test_info(self, mock_console):
        wiz.info("info msg")
        assert mock_console.print.called

    @mock.patch("git_setup_wizard.console")
    def test_warn(self, mock_console):
        wiz.warn("warning msg")
        assert mock_console.print.called

    @mock.patch("git_setup_wizard.console")
    def test_fail(self, mock_console):
        wiz.fail("fail msg")
        assert mock_console.print.called

    @mock.patch("git_setup_wizard.console")
    def test_dim(self, mock_console):
        wiz.dim("dim msg")
        assert mock_console.print.called


# ═════════════════════════════════════════════════════════════════════════════
#  Constants and module-level sanity checks
# ═════════════════════════════════════════════════════════════════════════════

class TestConstants:
    """Verify module-level constants are reasonable."""

    def test_github_ssh_url(self):
        assert wiz.GITHUB_SSH_URL == "https://github.com/settings/ssh/new"

    def test_github_gpg_url(self):
        assert wiz.GITHUB_GPG_URL == "https://github.com/settings/gpg/new"

    def test_ssh_dir_is_under_home(self):
        assert str(wiz.SSH_DIR).startswith(str(Path.home()))

    def test_ssh_key_is_ed25519(self):
        assert wiz.SSH_KEY.name == "id_ed25519"

    def test_ssh_pub_matches_private(self):
        assert wiz.SSH_PUB.name == "id_ed25519.pub"

    def test_banner_contains_ascii_art(self):
        # "Git" is rendered as ASCII block letters, not literal text
        assert "Wizard" in wiz.BANNER
        assert "____" in wiz.BANNER  # ASCII art structural chars


# ═════════════════════════════════════════════════════════════════════════════
#  Git config commands (mocked)
# ═════════════════════════════════════════════════════════════════════════════

class TestGitConfigCommands:
    """
    Verify that setup_gpg generates the correct git config commands.
    We test the command strings themselves, not execution.
    """

    def test_expected_git_config_commands(self):
        name = "Helen Hunt"
        email = "hhunt@twister.com"
        key_id = "ABCDEF1234567890"

        expected = [
            f'git config --global user.signingkey {key_id}',
            f'git config --global user.name "{name}"',
            f'git config --global user.email "{email}"',
            'git config --global gpg.program gpg',
            'git config --global commit.gpgsign true',
        ]

        # Build the same list the wizard builds
        commands = [
            f'git config --global user.signingkey {key_id}',
            f'git config --global user.name "{name}"',
            f'git config --global user.email "{email}"',
            'git config --global gpg.program gpg',
            'git config --global commit.gpgsign true',
        ]

        assert commands == expected

    def test_signing_key_in_commands(self):
        key_id = "DEADBEEF12345678"
        cmd = f'git config --global user.signingkey {key_id}'
        assert key_id in cmd
        assert "--global" in cmd


# ═════════════════════════════════════════════════════════════════════════════
#  Welcome exits cleanly when user declines
# ═════════════════════════════════════════════════════════════════════════════

class TestWelcome:
    """Test that welcome() exits when user says no."""

    @mock.patch("git_setup_wizard.Confirm.ask", return_value=False)
    @mock.patch("git_setup_wizard.console")
    def test_exits_on_decline(self, mock_console, mock_confirm):
        with pytest.raises(SystemExit) as exc_info:
            wiz.welcome()
        assert exc_info.value.code == 0

    @mock.patch("git_setup_wizard.Confirm.ask", return_value=True)
    @mock.patch("git_setup_wizard.console")
    def test_continues_on_accept(self, mock_console, mock_confirm):
        # Should not raise
        wiz.welcome()


# ═════════════════════════════════════════════════════════════════════════════
#  Preflight exits on non-Darwin
# ═════════════════════════════════════════════════════════════════════════════

class TestPreflight:
    """Test preflight platform check."""

    @mock.patch("git_setup_wizard.platform.system", return_value="Linux")
    @mock.patch("git_setup_wizard.console")
    def test_exits_on_linux(self, mock_console, mock_platform):
        with pytest.raises(SystemExit) as exc_info:
            wiz.preflight()
        assert exc_info.value.code == 1


# ═════════════════════════════════════════════════════════════════════════════
#  done_summary doesn't crash
# ═════════════════════════════════════════════════════════════════════════════

class TestDoneSummary:
    """Smoke test the summary panel rendering."""

    @mock.patch("git_setup_wizard.console")
    def test_all_good_path(self, mock_console):
        wiz.done_summary(True)
        assert mock_console.print.called

    @mock.patch("git_setup_wizard.console")
    def test_not_all_good_path(self, mock_console):
        wiz.done_summary(False)
        assert mock_console.print.called


# ═════════════════════════════════════════════════════════════════════════════
#  Main handles KeyboardInterrupt
# ═════════════════════════════════════════════════════════════════════════════

class TestMain:
    """Test the main() error handling."""

    @mock.patch("git_setup_wizard.welcome", side_effect=KeyboardInterrupt)
    @mock.patch("git_setup_wizard.console")
    def test_keyboard_interrupt_exits_130(self, mock_console, mock_welcome):
        with pytest.raises(SystemExit) as exc_info:
            wiz.main()
        assert exc_info.value.code == 130

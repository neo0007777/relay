"""
Unit tests for Relay CLI executable commands (Sprint 3).
"""

import os
import pytest
from relay.cli import main


def test_cli_version(capsys):
    with pytest.raises(SystemExit):
        main(["--version"])
    captured = capsys.readouterr()
    assert "relay v" in captured.out or "relay v" in captured.err


def test_cli_run(capsys):
    main(["run", "claude", "--goal", "Refactor JWT module"])
    captured = capsys.readouterr()
    assert "Initialized Relay Middleware Adapter" in captured.out
    assert "claude_code" in captured.out


def test_cli_checkpoint_list(capsys):
    main(["checkpoint", "list"])
    captured = capsys.readouterr()
    assert "Found" in captured.out or "Checkpoints:" in captured.out

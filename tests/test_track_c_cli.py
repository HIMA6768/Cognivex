from __future__ import annotations

import subprocess
import sys

from r7_helpers import ROOT


def test_track_c_training_cli_help_runs_from_repository_root() -> None:
    completed = subprocess.run(
        [sys.executable, "scripts/train_track_c.py", "--help"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    assert "--experiment-id" in completed.stdout
    assert "--output-root" in completed.stdout


def test_track_c_training_cli_rejects_path_unsafe_experiment_id() -> None:
    completed = subprocess.run(
        [sys.executable, "scripts/train_track_c.py", "--experiment-id", "../unsafe"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 2
    assert "lowercase and path-safe" in completed.stderr

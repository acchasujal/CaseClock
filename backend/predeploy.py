"""Prepare the AppSail build directory with shared contracts and dependencies."""

from pathlib import Path
import os
import shutil
import subprocess
import sys


ROOT = Path(__file__).resolve().parent
REPO_ROOT = ROOT.parent


def main() -> None:
    shutil.copytree(REPO_ROOT / "shared", ROOT / "shared", dirs_exist_ok=True)
    subprocess.run(
        [
            sys.executable,
            "-m",
            "pip",
            "install",
            "--no-cache-dir",
            "--upgrade",
            "-r",
            str(ROOT / "requirements.txt"),
            "-t",
            str(ROOT),
        ],
        check=True,
    )
    verify_env = dict(os.environ)
    verify_env["PYTHONPATH"] = str(ROOT) + os.pathsep + verify_env.get("PYTHONPATH", "")
    subprocess.run(
        [sys.executable, "-c", "import cryptography; from cryptography.hazmat.primitives.asymmetric import dsa"],
        env=verify_env,
        check=True,
    )
    try:
        sha = subprocess.check_output(
            ["git", "-C", str(REPO_ROOT), "rev-parse", "HEAD"],
            text=True,
        ).strip()
        (ROOT / "build-sha.txt").write_text(sha + "\n", encoding="utf-8")
    except (OSError, subprocess.CalledProcessError):
        # Git metadata is not guaranteed to be present in Catalyst's build container.
        pass


if __name__ == "__main__":
    main()

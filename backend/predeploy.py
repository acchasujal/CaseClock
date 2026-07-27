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
            "--force-reinstall",
            "--only-binary=:all:",
            "--platform",
            "manylinux2014_x86_64",
            "--python-version",
            "3.11",
            "--implementation",
            "cp",
            "--abi",
            "cp311",
            "-r",
            str(ROOT / "requirements.txt"),
            "-t",
            str(ROOT),
        ],
        check=True,
    )
    required_paths = [
        ROOT / "cryptography",
        ROOT / "cffi",
        ROOT / "cryptography" / "hazmat" / "bindings",
    ]
    native_files = list(ROOT.glob("_cffi_backend*.so")) + list((ROOT / "cryptography" / "hazmat" / "bindings").glob("_rust*"))
    if any(not path.exists() for path in required_paths) or not native_files:
        missing = ", ".join(str(path.relative_to(ROOT)) for path in required_paths if not path.exists())
        raise RuntimeError(f"AppSail crypto artifact incomplete; missing={missing or 'native binding'}")

    verify_env = dict(os.environ)
    verify_env["PYTHONPATH"] = str(ROOT)
    subprocess.run(
        [
            sys.executable,
            "-S",
            "-c",
            "from cryptography.exceptions import InvalidSignature; from cryptography.hazmat.primitives import hashes, serialization; from cryptography.hazmat.primitives.asymmetric import dsa; k=dsa.generate_private_key(key_size=1024); data=b'caseclock-convokraft-smoke'; s=k.sign(data, hashes.SHA256()); p=serialization.load_pem_public_key(k.public_key().public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo)); p.verify(s, data, hashes.SHA256())",
        ],
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

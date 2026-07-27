"""Prepare the AppSail build directory with shared contracts and dependencies."""

from pathlib import Path
import os
import shutil
import subprocess
import sys


ROOT = Path(__file__).resolve().parent
REPO_ROOT = ROOT.parent
VENDOR = ROOT / "vendor"


def _print_artifact_proof() -> None:
    crypto = VENDOR / "cryptography"
    init = crypto / "__init__.py"
    print(f"APPSAIL_SOURCE_ROOT={ROOT}")
    print(f"STAGED_CRYPTOGRAPHY={crypto}")
    print(f"STAGED_CRYPTOGRAPHY_EXISTS={crypto.is_dir()}")
    print(f"STAGED_CRYPTOGRAPHY_INIT_EXISTS={init.is_file()}")
    print(f"STAGED_SITE_PACKAGES={VENDOR}")
    relevant = [
        init.relative_to(VENDOR),
        Path("cryptography/hazmat/"),
        Path("cryptography/hazmat/bindings/"),
        Path("cryptography*.dist-info/"),
        Path("cffi/"),
        Path("_cffi_backend*"),
    ]
    for path in sorted(relevant):
        print(f"STAGED_PATH={path}")


def main() -> None:
    shutil.copytree(REPO_ROOT / "shared", ROOT / "shared", dirs_exist_ok=True)
    if VENDOR.exists():
        shutil.rmtree(VENDOR)
    VENDOR.mkdir()
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
            "--ignore-installed",
            "-r",
            str(ROOT / "requirements.txt"),
            "-t",
            str(VENDOR),
            ],
        check=True,
    )
    _print_artifact_proof()
    required_paths = [
        VENDOR / "cryptography",
        VENDOR / "cffi",
        VENDOR / "cryptography" / "hazmat" / "bindings",
    ]
    native_files = list(VENDOR.glob("_cffi_backend*")) + list((VENDOR / "cryptography" / "hazmat" / "bindings").glob("_rust*"))
    if any(not path.exists() for path in required_paths) or not native_files:
        missing = ", ".join(str(path.relative_to(ROOT)) for path in required_paths if not path.exists())
        raise RuntimeError(f"AppSail crypto artifact incomplete; missing={missing or 'native binding'}")

    verify_env = dict(os.environ)
    verify_env["PYTHONPATH"] = str(VENDOR)
    if sys.platform == "linux":
        subprocess.run(
            [
                sys.executable,
                "-S",
                "-c",
                "import sys; import cryptography; from cryptography.exceptions import InvalidSignature; from cryptography.hazmat.primitives import hashes, serialization; from cryptography.hazmat.primitives.asymmetric import dsa; print('ISOLATED_SYS_PATH=' + repr(sys.path)); print('ISOLATED_CRYPTOGRAPHY=' + cryptography.__file__); print('ISOLATED_CRYPTOGRAPHY_VERSION=' + cryptography.__version__); k=dsa.generate_private_key(key_size=1024); data=b'caseclock-convokraft-smoke'; s=k.sign(data, hashes.SHA256()); p=serialization.load_pem_public_key(k.public_key().public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo)); p.verify(s, data, hashes.SHA256()); print('ISOLATED_DSA_SIGN_VERIFY=success')",
            ],
            env=verify_env,
            check=True,
        )
    else:
        print("ISOLATED_DSA_SIGN_VERIFY=skipped_non_linux_cross_platform_artifact")
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

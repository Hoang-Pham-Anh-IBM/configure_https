"""
password_manager.py — Python client for the SAGTester Password Manager CLI.

Wraps passwordManager.bat (Windows) / passwordManager.sh (Linux) via subprocess.
The JAR path is resolved from the script's own location or the PM_HOME env variable.

Usage as a module:
    from password_manager import PasswordManagerClient
    pm = PasswordManagerClient()
    pm.add("myAlias", "mySecret")
    print(pm.get("myAlias"))
    pm.delete("myAlias")
    print(pm.list())

Usage as a CLI:
    python password_manager.py -g myAlias
    python password_manager.py -a myAlias mySecret
    python password_manager.py -d myAlias
    python password_manager.py -l
    python password_manager.py -ge myAlias
"""

import argparse
import os
import platform
import subprocess
import sys
from pathlib import Path


def _resolve_pm_script() -> str:
    """
    Resolve path to passwordManager.bat / .sh in this order:
      1. $SAGTESTER/bin/passwordManager.bat|.sh
      2. Sibling folder relative to this script: ../modules/.../dist/<os>/
      3. passwordManager on PATH
    """
    is_windows  = platform.system() == "Windows"
    script_name = "passwordManager.bat" if is_windows else "passwordManager.sh"
    os_dir      = "win" if is_windows else "unix"

    # 1. SAGTESTER env variable — script lives under $SAGTESTER/bin/
    sagtester = os.environ.get("SAGTESTER")
    if sagtester:
        candidate = Path(sagtester) / "bin" / script_name
        if candidate.exists():
            return str(candidate)

    # 2. Relative path from this file up to the dist folder
    here = Path(__file__).resolve().parent
    candidate = here.parent / "modules" / "com.ibm.entirex.password.manager" / "dist" / os_dir / script_name
    if candidate.exists():
        return str(candidate)

    # 3. Fall back to PATH
    return script_name


PM_SCRIPT = _resolve_pm_script()


class PasswordManagerError(RuntimeError):
    pass


class PasswordManagerClient:
    """Thin wrapper around the SAGTester Password Manager CLI."""

    def __init__(self, pm_script: str = PM_SCRIPT):
        self._script = pm_script

    def _run(self, *args: str, input_text: str | None = None) -> str:
        """Execute the password manager CLI and return stdout. Raises on non-zero exit."""
        cmd = [self._script, *args]
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            input=input_text,
        )
        if result.returncode != 0:
            raise PasswordManagerError(
                f"PasswordManager failed (exit {result.returncode}): {result.stderr.strip()}"
            )
        return result.stdout.strip()

    def get(self, alias: str) -> str:
        """Return the plain-text password for *alias*."""
        return self._run("-g", alias)

    def get_encrypted(self, alias: str) -> str:
        """Return the EntireX-encrypted password for *alias*."""
        return self._run("-ge", alias)

    def add(self, alias: str, password: str) -> None:
        """Store or update *alias* with *password*."""
        self._run("-a", alias, password)

    def delete(self, alias: str) -> None:
        """Delete *alias* (answers 'yes' to the confirmation prompt automatically)."""
        self._run("-d", alias, input_text="yes\n")

    def list(self, filter: str = "*", exclude: str = "") -> list[str]:
        """
        Return a list of alias names.
        *filter*  – wildcard pattern to include  (default: all)
        *exclude* – wildcard pattern to exclude  (default: none)
        """
        args = ["-l", "-f", filter]
        if exclude:
            args += ["-ex", exclude]
        output = self._run(*args)
        # Each line is formatted as "---> alias"
        return [line.replace("--->", "").strip() for line in output.splitlines() if "--->" in line]

    def export(self, filepath: str, filter: str = "*", exclude: str = "", timeout_secs: int = 600) -> None:
        """Export matching passwords to *filepath*."""
        args = ["-e", filepath, "-t", str(timeout_secs), "-f", filter]
        if exclude:
            args += ["-ex", exclude]
        self._run(*args)

    def import_file(self, filepath: str) -> None:
        """Import passwords from *filepath*."""
        self._run("-i", filepath)


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------
def main() -> None:
    parser = argparse.ArgumentParser(
        description="SAGTester Password Manager — Python CLI wrapper",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python password_manager.py -g myAlias\n"
            "  python password_manager.py -a myAlias mySecret\n"
            "  python password_manager.py -d myAlias\n"
            "  python password_manager.py -l\n"
            "  python password_manager.py -l -f 'db_*'\n"
            "  python password_manager.py -ge myAlias\n"
        ),
    )
    parser.add_argument("-g",  "--get",          metavar="ALIAS",    help="Get plain password")
    parser.add_argument("-ge", "--get-encrypted", metavar="ALIAS",   help="Get EntireX encrypted password")
    parser.add_argument("-a",  "--add",           metavar=("ALIAS", "PASSWORD"), nargs=2, help="Add/update password")
    parser.add_argument("-d",  "--delete",        metavar="ALIAS",   help="Delete password")
    parser.add_argument("-l",  "--list",          action="store_true", help="List all aliases")
    parser.add_argument("-f",  "--filter",        metavar="EXPR",    default="*", help="Wildcard filter (with -l)")
    parser.add_argument("-ex", "--exclude",       metavar="EXPR",    default="",  help="Wildcard exclude (with -l)")
    args = parser.parse_args()

    pm = PasswordManagerClient()
    if args.get:
        print(pm.get(args.get))
    elif args.get_encrypted:
        print(pm.get_encrypted(args.get_encrypted))
    elif args.add:
        pm.add(args.add[0], args.add[1])
        print(f"Saved: {args.add[0]}")
    elif args.delete:
        pm.delete(args.delete)
        print(f"Deleted: {args.delete}")
    elif args.list:
        aliases = pm.list(filter=args.filter, exclude=args.exclude)
        for a in aliases:
            print(a)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()

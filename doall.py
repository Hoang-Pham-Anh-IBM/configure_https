"""
doall.py — end-to-end HTTPS port setup for a webMethods Integration Server.

Steps executed in order:
  1. create_certificates   — generate keystore + truststore .p12 files via keytool
  2. configure_certificate_aliases — register/update the aliases in IS Admin UI
  3. configure_https_port  — add the HTTPS port and set access mode to Allow

Usage:
  python doall.py -hostname <host> -https_port <port> [-password <pw>] [-alias <alias>] [-certificates <folder>]
"""

import argparse
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).parent


def run_script(script: str, args: list[str]) -> None:
    """Run a sibling Python script with the given arguments and exit on failure."""
    cmd = [sys.executable, str(HERE / script)] + args
    print()
    print(f"{'=' * 60}")
    print(f"  Running: {script}")
    print(f"{'=' * 60}")
    result = subprocess.run(cmd)
    if result.returncode != 0:
        print(f"\n[ERROR] {script} failed. Aborting.")
        sys.exit(result.returncode)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="End-to-end HTTPS port setup for a webMethods Integration Server.",
        epilog=(
            "Examples:\n"
            "  python doall.py -hostname exxwin22sum25 -https_port 5577\n"
            "  python doall.py -hostname exxwin22sum25 -https_port 5577 -password MySecret -alias MY_PORT\n"
            "  python doall.py -hostname exxwin22sum25 -https_port 5577 -certificates C:\\certs"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("-hostname",     required=True,  help="IS hostname (e.g. exxwin22sum25)")
    parser.add_argument("-https_port",   required=True,  help="HTTPS port number to create (e.g. 5577)")
    parser.add_argument("-password",     default="changeIt", help="Keystore/truststore password (default: changeIt)")
    parser.add_argument("-alias",        default=None,   help="Port alias name (default: HTTPS_<https_port>)")
    parser.add_argument("-certificates", default=".",    help="Folder containing the .p12 files (default: .)")
    args = parser.parse_args()

    hostname     = args.hostname
    https_port   = args.https_port
    password     = args.password
    alias        = args.alias or f"HTTPS_{https_port}"
    certificates = str(Path(args.certificates).resolve())

    print()
    print("=" * 60)
    print("  doall — IS HTTPS port setup")
    print("=" * 60)
    print(f"  Hostname     : {hostname}")
    print(f"  HTTPS port   : {https_port}")
    print(f"  Alias        : {alias}")
    print(f"  Certificates : {certificates}")
    print("=" * 60)

    # Step 1 — generate .p12 files
    run_script("create_certificates.py", [
        "-hostname", hostname,
        "-password", password,
    ])

    # Step 2 — register aliases in IS Admin UI
    run_script("configure_certificate_aliases.py", [
        "-hostname",     hostname,
        "-password",     password,
        "-certificates", certificates,
    ])

    # Step 3 — add HTTPS port and set access mode
    run_script("configure_https_port.py", [
        "-hostname", hostname,
        "-port",     https_port,
        "-alias",    alias,
    ])

    print()
    print("=" * 60)
    print("  SUCCESS — all steps completed.")
    print(f"  IS HTTPS port {https_port} is ready on {hostname}.")
    print("=" * 60)


if __name__ == "__main__":
    main()

"""
get-truststore.py — Extract a server's TLS certificate and import it into a
local PKCS12 truststore via keytool.

Steps:
  1. Extract the certificate from SERVER:PORT with `keytool -printcert -sslserver`.
  2. Import the certificate into the truststore with `keytool -import`.
  3. List the truststore contents to verify.

Usage:
    python get-truststore.py <server:port>

Example:
    python get-truststore.py exxwin22sum25:5543
"""

import argparse
import subprocess
import sys
from pathlib import Path

STOREPASS = "changeIt"
JAVA_HOME = Path(r"C:\SoftwareAG\jvm\jvm")
KEYTOOL = JAVA_HOME / "bin" / "keytool"


def run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, **kwargs)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Extract a server's TLS certificate and import it into a local PKCS12 truststore."
    )
    parser.add_argument(
        "server_port",
        metavar="server:port",
        help="Target server and port, e.g. exxwin22sum25:5543",
    )
    args = parser.parse_args()

    server, sep, port = args.server_port.partition(":")
    if not sep or not port.isdigit():
        parser.error(f"server:port must be in the form HOST:PORT, e.g. exxwin22sum25:5543 (got {args.server_port!r})")

    args.server = server
    args.port = int(port)
    return args


def main() -> None:
    args = parse_args()
    server, port = args.server, args.port
    alias = server
    cert_file = Path("certificates") / f"{alias}.crt"
    truststore = Path("certificates") / f"{alias}.p12"

    print()
    print(f"=== Step 1: Extract certificate from {server}:{port} ===")
    with cert_file.open("w", encoding="utf-8") as cert_out:
        result = run(
            [str(KEYTOOL), "-printcert", "-sslserver", f"{server}:{port}", "-rfc"],
            stdout=cert_out,
        )
    if result.returncode != 0:
        print(f"ERROR: Failed to extract certificate from {server}:{port}")
        sys.exit(1)
    print(f"Certificate saved to {cert_file}")

    print()
    print("=== Step 2: Import certificate into truststore ===")
    truststore.parent.mkdir(parents=True, exist_ok=True)
    result = run(
        [
            str(KEYTOOL), "-import",
            "-alias", alias,
            "-file", str(cert_file),
            "-keystore", str(truststore),
            "-storetype", "PKCS12",
            "-storepass", STOREPASS,
            "-noprompt",
        ]
    )
    if result.returncode != 0:
        print("ERROR: Failed to import certificate into truststore")
        sys.exit(1)
    print(f"Certificate imported into {truststore}")

    print()
    print("=== Step 3: Verify truststore contents ===")
    run(
        [
            str(KEYTOOL), "-list",
            "-keystore", str(truststore),
            "-storetype", "PKCS12",
            "-storepass", STOREPASS,
        ]
    )

    print()
    print("Done.")


if __name__ == "__main__":
    main()

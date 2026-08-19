import argparse
import os
import platform
import subprocess
import sys
from pathlib import Path

# Resolve keytool:
#   1. SAG bundled JVM (Windows or Linux path)
#   2. JAVA_HOME env variable
#   3. keytool on PATH
def _resolve_keytool() -> str:
    is_windows = platform.system() == "Windows"
    sag_jvm = Path(r"C:\SoftwareAG\jvm\jvm") if is_windows else Path("/opt/exx/installed/jvm/jvm")
    if sag_jvm.exists():
        java_home = sag_jvm
    elif os.environ.get("JAVA_HOME"):
        java_home = Path(os.environ["JAVA_HOME"])
    else:
        return "keytool"  # rely on PATH
    exe = "keytool.exe" if is_windows else "keytool"
    return str(java_home / "bin" / exe)

KEYTOOL = _resolve_keytool()


def run(cmd: list[str], step: str) -> None:
    """Run a keytool command and exit on failure."""
    print(f"\n{step}")
    print(" ".join(cmd))
    result = subprocess.run(cmd)
    if result.returncode != 0:
        print(f"\nERROR occurred while executing keytool (step: {step}).")
        sys.exit(1)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Create PKCS12 keystore and truststore for an IS host.",
        epilog=(
            "Examples:\n"
            "  python create_certificates.py -hostname exxwin22sum25\n"
            "  python create_certificates.py -hostname exxwin22sum25 -password MySecret123"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("-hostname", required=True, help="Hostname (e.g. exxwin22sum25)")
    parser.add_argument("-password", default="changeIt", help="Keystore/truststore password (default: changeIt)")
    args = parser.parse_args()

    hostname = args.hostname
    password = args.password
    keystore   = f"{hostname}-keystore.p12"
    truststore = f"{hostname}-truststore.p12"
    certfile   = f"{hostname}.cer"

    print()
    print("==========================================")
    print(f" Creating keystore for {hostname}")
    print("==========================================")

    # Step 0 — clean up existing certificate files
    for f in [keystore, truststore, certfile]:
        p = Path(f)
        if p.exists():
            p.unlink()
            print(f"  Removed existing: {f}")

    # Step 1 — generate key pair
    run([
        KEYTOOL, "-genkeypair",
        "-alias",     hostname,
        "-keyalg",    "RSA",
        "-keysize",   "2048",
        "-validity",  "3650",
        "-storetype", "PKCS12",
        "-keystore",  keystore,
        "-storepass", password,
        "-keypass",   password,
        "-dname",     f"CN={hostname}, OU=QA, O=IBM, L=Frankfurt, ST=HE, C=DE",
        "-ext",       f"SAN=dns:{hostname}",
    ], "Generating key pair ...")

    # Step 2 — export certificate
    run([
        KEYTOOL, "-exportcert",
        "-alias",     hostname,
        "-keystore",  keystore,
        "-storepass", password,
        "-storetype", "PKCS12",
        "-rfc",
        "-file",      certfile,
    ], "Exporting certificate ...")

    # Step 3 — create truststore
    run([
        KEYTOOL, "-importcert",
        "-alias",     hostname,
        "-file",      certfile,
        "-storetype", "PKCS12",
        "-keystore",  truststore,
        "-storepass", password,
        "-noprompt",
    ], "Creating truststore ...")

    # Step 4 — list keystore
    run([
        KEYTOOL, "-list", "-v",
        "-keystore",  keystore,
        "-storetype", "PKCS12",
        "-storepass", password,
        "-noprompt",
    ], "Listing keystore ...")

    # Step 5 — list truststore
    run([
        KEYTOOL, "-list", "-v",
        "-keystore",  truststore,
        "-storetype", "PKCS12",
        "-storepass", password,
        "-noprompt",
    ], "Listing truststore ...")

    print()
    print("SUCCESS")
    print(f"  Keystore  : {keystore}")
    print(f"  Truststore: {truststore}")
    print(f"  Cert File : {certfile}")


if __name__ == "__main__":
    main()

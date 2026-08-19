# py_project

Playwright-based automation scripts for configuring HTTPS certificates on a
webMethods Integration Server (IS).

## Prerequisites

- Python 3.12+
- A running IS instance reachable on port `5555` (Admin UI)

### Install dependencies

A virtual environment (`.venv`) is **not created automatically** — run these
steps once before using the scripts:

```bash
cd py_project

# 1. Create the virtual environment (Python 3.12 explicit path — adjust if needed)
C:\Users\<you>\AppData\Local\Programs\Python\Python312\python.exe -m venv .venv

# 2. Activate it
.venv\Scripts\activate

# 3. Install Python packages
pip install -r requirements.txt

# 4. Install the Chromium browser used by Playwright
python -m playwright install chromium
```

For every subsequent terminal session, only the activation step is needed:

```bash
cd py_project
.venv\Scripts\activate
```

---

## Scripts

### 1. `create_certificates.py`

Generates a PKCS12 keystore and truststore for an IS host using `keytool`.

**Output files** (written to the current directory):

| File | Description |
|---|---|
| `<hostname>-keystore.p12` | Keystore containing the private key and self-signed certificate |
| `<hostname>-truststore.p12` | Truststore containing the exported public certificate |
| `<hostname>.cer` | Exported PEM certificate |

**keytool resolution order:**

1. `C:\SoftwareAG\jvm\jvm\bin\keytool.exe` (SAG JVM, if present)
2. `%JAVA_HOME%\bin\keytool.exe` (env variable fallback)
3. `keytool` on `PATH` (last resort)

**Parameters:**

| Parameter | Required | Default | Description |
|---|---|---|---|
| `-hostname` | ✅ | — | IS hostname (e.g. `exxwin22sum25`) |
| `-password` | ❌ | `changeIt` | Password for keystore and truststore |

**Examples:**

```bash
python create_certificates.py -hostname exxwin22sum25
python create_certificates.py -hostname exxwin22sum25 -password MySecret123
```

---

### 2. `configure_certificate_aliases.py`

Registers the keystore and truststore `.p12` files as aliases in the IS Admin
Console (`Security > Keystore`). If an alias already exists it is edited
in-place; otherwise a new alias is created.

**Parameters:**

| Parameter | Required | Default | Description |
|---|---|---|---|
| `-hostname` | ✅ | — | IS hostname (e.g. `exxwin22sum25`) |
| `-password` | ❌ | `changeIt` | Password used for both aliases |
| `-certificates` | ❌ | `.` | Folder that contains the `.p12` files |

**Aliases created/updated:**

| Alias | File |
|---|---|
| `<hostname>_keystore` | `<certificates>\<hostname>-keystore.p12` |
| `<hostname>_truststore` | `<certificates>\<hostname>-truststore.p12` |

**Examples:**

```bash
python configure_certificate_aliases.py -hostname exxwin22sum25
python configure_certificate_aliases.py -hostname exxwin22sum25 -password MySecret123
python configure_certificate_aliases.py -hostname exxwin22sum25 -certificates "C:\certs" -password MySecret123
```

---

### 3. `configure_https_port.py`

Adds a new `webMethods/HTTPS` listener port in IS Admin Console
(`Server > Ports`), wiring it to the keystore and truststore aliases created
by `configure_certificate_aliases.py`. After saving the port it also sets the
access mode to **Allow by Default** and confirms the browser dialog.

**Parameters:**

| Parameter | Required | Default | Description |
|---|---|---|---|
| `-hostname` | ✅ | — | IS hostname (e.g. `exxwin22sum25`) |
| `-port` | ✅ | — | Port number to create (e.g. `5577`) |
| `-alias` | ✅ | — | Port alias name (e.g. `CU_HTTPS_PORT`) |

**Examples:**

```bash
python configure_https_port.py -hostname exxwin22sum25 -port 5577 -alias CU_HTTPS_PORT
```

---

### 4. `doall.py`

Runs all three steps above in sequence with a single command.
Aborts immediately if any step fails.

**Parameters:**

| Parameter | Required | Default | Description |
|---|---|---|---|
| `-hostname` | ✅ | — | IS hostname (e.g. `exxwin22sum25`) |
| `-https_port` | ✅ | — | HTTPS port number to create (e.g. `5577`) |
| `-password` | ❌ | `changeIt` | Keystore/truststore password |
| `-alias` | ❌ | `HTTPS_<https_port>` | Port alias name |
| `-certificates` | ❌ | `.` | Folder containing the `.p12` files (resolved to absolute path) |

**Examples:**

```bash
# Minimal — uses all defaults
python doall.py -hostname exxwin22sum25 -https_port 5577

# Full
python doall.py -hostname exxwin22sum25 -https_port 5577 -password MySecret -alias MY_PORT -certificates C:\certs
```

---

## Typical workflow

### Option A — one command

```bash
python doall.py -hostname exxwin22sum25 -https_port 5577 -password MySecret
```

### Option B — step by step

```bash
# 1. Generate the .p12 files
python create_certificates.py -hostname exxwin22sum25 -password MySecret

# 2. Register the aliases in IS (creates or updates)
python configure_certificate_aliases.py -hostname exxwin22sum25 -password MySecret

# 3. Create the HTTPS port wired to those aliases
python configure_https_port.py -hostname exxwin22sum25 -port 5577 -alias CU_HTTPS_PORT
```

---

## Recording new scripts with Playwright Codegen

`playwright codegen` opens a browser and records every click, fill, and
navigation into ready-to-use Python code. Use it to extend or create new
automation scripts.

### Basic usage

```bash
# Activate the venv first
.venv\Scripts\activate

# Open codegen against the IS Admin UI
python -m playwright codegen http://<hostname>:5555/
```

A browser window and a **Playwright Inspector** panel open side by side.
Interact with the page normally — the Inspector generates the corresponding
Python code in real time. Copy the generated snippet into your script when
done.

### Useful options

| Option | Example | Description |
|---|---|---|
| `--target` | `--target python` | Output language (default: Python) |
| `--output` | `--output my_script.py` | Write code directly to a file |
| `--browser` | `--browser chromium` | Browser to use (`chromium`, `firefox`, `webkit`) |
| `--viewport-size` | `--viewport-size 1920,1080` | Set browser window size |
| `--save-storage` | `--save-storage auth.json` | Save cookies/localStorage after recording (reuse login) |
| `--load-storage` | `--load-storage auth.json` | Load saved cookies so you start already logged in |

### Record directly to a file

```bash
python -m playwright codegen --output new_script.py http://<hostname>:5555/
```

### Reuse a saved login session

```bash
# Step 1 — record the login and save the session
python -m playwright codegen --save-storage auth.json http://<hostname>:5555/

# Step 2 — start future recordings already authenticated
python -m playwright codegen --load-storage auth.json http://<hostname>:5555/
```

### Tips

- Register a **dialog handler** (`page.once("dialog", ...)`) manually after
  recording — codegen does not capture native browser dialogs.
- Prefer `get_by_role`, `get_by_label`, and `get_by_test_id` locators over
  `nth()` — they are more resilient to page changes.
- Use `locator(...).filter(has_text=...)` to scope to a specific table row,
  but prefer `href` attribute selectors when the text appears in multiple rows.


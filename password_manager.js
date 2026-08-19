#!/usr/bin/env node
/**
 * password_manager.js — Node.js client for the SAGTester Password Manager CLI.
 *
 * Wraps passwordManager.bat (Windows) / passwordManager.sh (Linux) via child_process.
 * The script path is resolved from PM_HOME env variable or relative to this file.
 *
 * Usage as a module:
 *   const { PasswordManagerClient } = require('./password_manager');
 *   const pm = new PasswordManagerClient();
 *   await pm.add('myAlias', 'mySecret');
 *   console.log(await pm.get('myAlias'));
 *   await pm.delete('myAlias');
 *   console.log(await pm.list());
 *
 * Usage as a CLI:
 *   node password_manager.js -g myAlias
 *   node password_manager.js -a myAlias mySecret
 *   node password_manager.js -d myAlias
 *   node password_manager.js -l
 *   node password_manager.js -ge myAlias
 */

'use strict';

const { execFile, spawn } = require('child_process');
const path = require('path');
const os   = require('os');

// ---------------------------------------------------------------------------
// Resolve path to passwordManager.bat / .sh
// ---------------------------------------------------------------------------
function resolvePmScript() {
  const isWindows  = os.platform() === 'win32';
  const scriptName = isWindows ? 'passwordManager.bat' : 'passwordManager.sh';
  const osDir      = isWindows ? 'win' : 'unix';
  const fs         = require('fs');

  // 1. SAGTESTER env variable — script lives under $SAGTESTER/bin/
  if (process.env.SAGTESTER) {
    const candidate = path.join(process.env.SAGTESTER, 'bin', scriptName);
    if (fs.existsSync(candidate)) return candidate;
  }

  // 2. Relative path from this file up to the dist folder
  const candidate = path.resolve(
    __dirname, '..', 'modules',
    'com.ibm.entirex.password.manager', 'dist', osDir, scriptName
  );
  if (fs.existsSync(candidate)) return candidate;

  // 3. Fall back to PATH
  return scriptName;
}

const PM_SCRIPT = resolvePmScript();

// ---------------------------------------------------------------------------
// PasswordManagerError
// ---------------------------------------------------------------------------
class PasswordManagerError extends Error {
  constructor(message, exitCode) {
    super(message);
    this.name = 'PasswordManagerError';
    this.exitCode = exitCode;
  }
}

// ---------------------------------------------------------------------------
// PasswordManagerClient
// ---------------------------------------------------------------------------
class PasswordManagerClient {
  /**
   * @param {string} [pmScript] - Path to passwordManager.bat/.sh (defaults to auto-resolved)
   */
  constructor(pmScript = PM_SCRIPT) {
    this._script = pmScript;
  }

  /**
   * Run the CLI with the given arguments.
   * @param {string[]} args
   * @param {string}   [stdinText] - Text to write to stdin (e.g. 'yes\n' for delete confirmation)
   * @returns {Promise<string>} stdout trimmed
   */
  _run(args, stdinText = null) {
    return new Promise((resolve, reject) => {
      const child = spawn(this._script, args, {
        shell: true,          // needed for .bat on Windows
        stdio: ['pipe', 'pipe', 'pipe'],
      });

      let stdout = '';
      let stderr = '';
      child.stdout.on('data', d => { stdout += d; });
      child.stderr.on('data', d => { stderr += d; });

      if (stdinText !== null) {
        child.stdin.write(stdinText);
        child.stdin.end();
      }

      child.on('close', code => {
        if (code !== 0) {
          reject(new PasswordManagerError(
            `PasswordManager failed (exit ${code}): ${stderr.trim()}`,
            code
          ));
        } else {
          resolve(stdout.trim());
        }
      });

      child.on('error', err => reject(err));
    });
  }

  /** Return the plain-text password for alias. */
  async get(alias) {
    return this._run(['-g', alias]);
  }

  /** Return the EntireX-encrypted password for alias. */
  async getEncrypted(alias) {
    return this._run(['-ge', alias]);
  }

  /** Store or update alias with password. */
  async add(alias, password) {
    await this._run(['-a', alias, password]);
  }

  /** Delete alias (answers 'yes' to the confirmation prompt automatically). */
  async delete(alias) {
    await this._run(['-d', alias], 'yes\n');
  }

  /**
   * Return an array of alias names.
   * @param {string} [filter='*']  - Wildcard pattern to include
   * @param {string} [exclude=''] - Wildcard pattern to exclude
   */
  async list(filter = '*', exclude = '') {
    const args = ['-l', '-f', filter];
    if (exclude) args.push('-ex', exclude);
    const output = await this._run(args);
    return output
      .split('\n')
      .filter(line => line.includes('--->'))
      .map(line => line.replace('--->', '').trim());
  }

  /** Export matching passwords to filepath. */
  async export(filepath, { filter = '*', exclude = '', timeoutSecs = 600 } = {}) {
    const args = ['-e', filepath, '-t', String(timeoutSecs), '-f', filter];
    if (exclude) args.push('-ex', exclude);
    await this._run(args);
  }

  /** Import passwords from filepath. */
  async importFile(filepath) {
    await this._run(['-i', filepath]);
  }
}

// ---------------------------------------------------------------------------
// CLI entry point
// ---------------------------------------------------------------------------
async function main() {
  const args = process.argv.slice(2);
  const pm   = new PasswordManagerClient();

  const flag = args[0];
  try {
    switch (flag) {
      case '-g': case '--get':
        console.log(await pm.get(args[1]));
        break;
      case '-ge': case '--get-encrypted':
        console.log(await pm.getEncrypted(args[1]));
        break;
      case '-a': case '--add':
        await pm.add(args[1], args[2]);
        console.log(`Saved: ${args[1]}`);
        break;
      case '-d': case '--delete':
        await pm.delete(args[1]);
        console.log(`Deleted: ${args[1]}`);
        break;
      case '-l': case '--list': {
        const filterIdx  = args.indexOf('-f');
        const excludeIdx = args.indexOf('-ex');
        const filter  = filterIdx  >= 0 ? args[filterIdx  + 1] : '*';
        const exclude = excludeIdx >= 0 ? args[excludeIdx + 1] : '';
        const aliases = await pm.list(filter, exclude);
        aliases.forEach(a => console.log(a));
        break;
      }
      default:
        console.log([
          'SAGTester Password Manager — Node.js CLI wrapper',
          '',
          'Usage:',
          '  node password_manager.js -g  <alias>            Get plain password',
          '  node password_manager.js -ge <alias>            Get EntireX encrypted password',
          '  node password_manager.js -a  <alias> <password> Add/update password',
          '  node password_manager.js -d  <alias>            Delete password',
          '  node password_manager.js -l  [-f <expr>] [-ex <expr>]  List aliases',
        ].join('\n'));
        process.exit(1);
    }
  } catch (err) {
    console.error(`Error: ${err.message}`);
    process.exit(err.exitCode ?? 1);
  }
}

if (require.main === module) {
  main();
}

module.exports = { PasswordManagerClient, PasswordManagerError, PM_SCRIPT };

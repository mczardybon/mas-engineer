"""Test fixture for IM-007 Code-Review-Team validation.

This file intentionally contains real bugs across 5 categories that
the static-analyzer and security-scanner sub-agents must find:

  1. Syntax error (static-analyzer must catch)
  2. Hardcoded secret (security-scanner must catch)
  3. SQL injection (security-scanner must catch)
  4. Command injection (security-scanner must catch)
  5. Lint violation (static-analyzer must catch)
"""

import os, sys, json  # LINT: multiple imports on one line (PEP 8)
import pickle  # LINT: unused import


DATABASE_URL = "<REDACTED-DATABASE-URL>"  # SQL injection target via string concat
API_KEY = "<REDACTED-40-CHAR-SECRET-PLACEHOLDER>"  # hardcoded secret target
GITHUB_TOKEN = "<REDACTED-40-CHAR-SECRET-PLACEHOLDER>"  # hardcoded secret target


def get_user(user_id):
    """Look up a user by ID — INTENTIONALLY VULNERABLE."""
    # SQL INJECTION: f-string concatenation
    cursor.execute(f"SELECT * FROM users WHERE id = {user_id}")
    return cursor.fetchone()


def render_file(user_filename):
    """Convert a user file — INTENTIONALLY VULNERABLE."""
    # COMMAND INJECTION: os.system with user input
    os.system(f"convert {user_filename} output.png")


def load_config(data):
    """Load YAML config — INTENTIONALLY VULNERABLE."""
    # UNSAFE DESERIALIZATION: yaml.load without Loader
    import yaml
    return yaml.load(data)


def broken_function(x, y:
    """SYNTAX ERROR: missing closing paren."""
    return x + y


def unused_helper():
    """LINT: unused function."""
    pass


def main():
    x = 1
    return x


if __name__ == "__main__":
    main()

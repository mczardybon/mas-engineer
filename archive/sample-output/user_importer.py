"""User import pipeline — processes CSV user data."""
import csv
import hashlib
import re
from datetime import datetime
from pathlib import Path
from typing import Any


# ── Validation helpers ────────────────────────────────────────────────

_VALID_ROLES = {"user", "admin", "moderator", "viewer"}


def _validate_email(email: str) -> str | None:
    """Return an error message if invalid, otherwise None."""
    if not email:
        return "email is required"
    if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
        return f"invalid email: {email!r}"
    return None


def _validate_name(name: str) -> str | None:
    if not name:
        return "name is required"
    if len(name) < 2:
        return f"name too short: {name!r}"
    return None


def _validate_age(age_str: str) -> tuple[str | None, int | None]:
    """Return (error, parsed_age)."""
    if not age_str:
        return ("age is required", None)
    try:
        age = int(age_str)
    except ValueError:
        return (f"invalid age: {age_str!r}", None)
    if age < 0 or age > 150:
        return (f"age out of range: {age}", age)
    return (None, age)


def _validate_password(password: str) -> str | None:
    if not password:
        return "password is required"
    if len(password) < 8:
        return "password too short (min 8 chars)"
    return None


def _validate_role(role: str) -> str | None:
    if role not in _VALID_ROLES:
        return f"invalid role: {role!r}"
    return None


def _validate_row(row: dict[str, str]) -> tuple[list[str], dict[str, str] | None]:
    """Validate one CSV row. Returns (errors, validated_record_or_None)."""
    email = row.get("email", "").strip()
    name = row.get("name", "").strip()
    age_str = row.get("age", "").strip()
    password = row.get("password", "")
    role = row.get("role", "user").strip()

    errs: list[str] = []
    for err in [_validate_email(email),
                 _validate_name(name),
                 _validate_role(role),
                 _validate_password(password)]:
        if err:
            errs.append(err)

    age_err, age = _validate_age(age_str)
    if age_err:
        errs.append(age_err)

    if errs:
        return (errs, None)

    return (
        [],
        {
            "email": email,
            "name": name,
            "age": str(age) if age is not None else "",
            "role": role,
            "password_hash": hashlib.sha256(password.encode()).hexdigest(),
        },
    )


# ── I/O helpers ───────────────────────────────────────────────────────


def _read_csv(csv_path: str) -> list[dict[str, str]]:
    with open(csv_path, newline="") as f:
        return list(csv.DictReader(f))


def _write_valid_users(valid: list[dict[str, str]], out_dir: Path) -> str:
    path = out_dir / "valid_users.csv"
    if valid:
        with open(path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(valid[0].keys()))
            writer.writeheader()
            writer.writerows(valid)
    return str(path)


def _write_error_report(errors: list[dict[str, str]], out_dir: Path) -> str | None:
    if not errors:
        return None
    path = out_dir / "import_errors.csv"
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["line", "errors"])
        writer.writeheader()
        writer.writerows(errors)
    return str(path)


def _write_summary(total: int, valid: int, errors: int, out_dir: Path) -> str:
    path = out_dir / "import_summary.txt"
    content = (
        f"Import completed at {datetime.now().isoformat()}\n"
        f"Total: {total}, Valid: {valid}, Errors: {errors}\n"
    )
    path.write_text(content)
    return str(path)


# ── Public entry point ────────────────────────────────────────────────


def import_users(csv_path: str, output_dir: str, dry_run: bool = False) -> dict[str, Any]:
    """Import users from CSV, validate, hash passwords, and write output."""
    rows = _read_csv(csv_path)

    # --- Validate ---
    valid: list[dict[str, str]] = []
    errors: list[dict[str, str]] = []
    for i, row in enumerate(rows, start=2):  # header = line 1
        errs, record = _validate_row(row)
        if errs:
            errors.append({"line": str(i), "errors": "; ".join(errs)})
        else:
            valid.append(record)

    result: dict[str, Any] = {
        "total": len(rows),
        "valid": len(valid),
        "errors": len(errors),
        "error_details": errors,
        "output_files": [],
    }

    if dry_run:
        result["dry_run"] = True
        return result

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    result["output_files"].append(_write_valid_users(valid, out_dir))
    err_path = _write_error_report(errors, out_dir)
    if err_path:
        result["output_files"].append(err_path)
    result["output_files"].append(_write_summary(len(rows), len(valid), len(errors), out_dir))

    return result

"""User import pipeline — processes CSV user data."""
import csv
import hashlib
import re
from datetime import datetime
from pathlib import Path
from typing import Any


def import_users(csv_path: str, output_dir: str, dry_run: bool = False) -> dict[str, Any]:
    """Import users from CSV, validate, hash passwords, and write output."""
    # --- Phase 1: Read ---
    rows: list[dict[str, str]] = []
    with open(csv_path, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)

    # --- Phase 2: Validate ---
    valid: list[dict[str, str]] = []
    errors: list[dict[str, str]] = []
    for i, row in enumerate(rows, start=2):  # header = line 1
        errs: list[str] = []

        email = row.get("email", "").strip()
        if not email:
            errs.append("email is required")
        elif not re.match(r"[^@]+@[^@]+\.[^@]+", email):
            errs.append(f"invalid email: {email!r}")

        name = row.get("name", "").strip()
        if not name:
            errs.append("name is required")
        elif len(name) < 2:
            errs.append(f"name too short: {name!r}")

        age_str = row.get("age", "").strip()
        age: int | None = None
        if not age_str:
            errs.append("age is required")
        else:
            try:
                age = int(age_str)
                if age < 0 or age > 150:
                    errs.append(f"age out of range: {age}")
            except ValueError:
                errs.append(f"invalid age: {age_str!r}")

        password = row.get("password", "")
        if not password:
            errs.append("password is required")
        elif len(password) < 8:
            errs.append("password too short (min 8 chars)")

        role = row.get("role", "user").strip()
        valid_roles = {"user", "admin", "moderator", "viewer"}
        if role not in valid_roles:
            errs.append(f"invalid role: {role!r}")

        if errs:
            errors.append({"line": str(i), "errors": "; ".join(errs)})
        else:
            valid.append({
                "email": email,
                "name": name,
                "age": str(age) if age is not None else "",
                "role": role,
                "password_hash": hashlib.sha256(password.encode()).hexdigest(),
            })

    # --- Phase 3: Write ---
    result = {
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

    # Valid users CSV
    valid_path = out_dir / "valid_users.csv"
    with open(valid_path, "w", newline="") as f:
        if valid:
            writer = csv.DictWriter(f, fieldnames=list(valid[0].keys()))
            writer.writeheader()
            writer.writerows(valid)
    result["output_files"].append(str(valid_path))

    # Error report
    if errors:
        err_path = out_dir / "import_errors.csv"
        with open(err_path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["line", "errors"])
            writer.writeheader()
            writer.writerows(errors)
        result["output_files"].append(str(err_path))

    # Summary log
    summary_path = out_dir / "import_summary.txt"
    summary = (
        f"Import completed at {datetime.now().isoformat()}\n"
        f"Total: {len(rows)}, Valid: {len(valid)}, Errors: {len(errors)}\n"
    )
    summary_path.write_text(summary)
    result["output_files"].append(str(summary_path))

    return result

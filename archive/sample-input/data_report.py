"""Report generator — builds HTML/Markdown reports from raw data."""
import json
from collections import Counter
from datetime import date, datetime
from pathlib import Path
from typing import Any


def generate_report(data_path: str, report_type: str, output_path: str) -> dict[str, Any]:
    """Load data, analyze, format, and write a report."""
    # Load
    with open(data_path) as f:
        raw = json.load(f)

    records: list[dict[str, Any]] = raw.get("records", [])

    # Summarize
    total = len(records)
    categories = Counter()
    statuses = Counter()
    date_range: tuple[str, str] | None = None
    total_value = 0.0
    priorities = Counter()
    assignees = Counter()

    for rec in records:
        cat = rec.get("category", "unknown")
        categories[cat] += 1

        st = rec.get("status", "unknown")
        statuses[st] += 1

        created = rec.get("created_at")
        if created:
            if date_range is None:
                date_range = (created, created)
            else:
                if created < date_range[0]:
                    date_range = (created, date_range[1])
                if created > date_range[1]:
                    date_range = (date_range[0], created)

        val = rec.get("value", 0)
        if isinstance(val, (int, float)):
            total_value += val

        pri = rec.get("priority", "none")
        priorities[pri] += 1

        assignee = rec.get("assignee", "unassigned")
        assignees[assignee] += 1

    # Build report content
    if report_type == "markdown":
        lines = [f"# Data Report — {datetime.now().strftime('%Y-%m-%d')}", ""]
        lines.append(f"**Total Records:** {total}")
        lines.append("")
        lines.append("## Categories")
        for cat, count in categories.most_common():
            lines.append(f"- **{cat}:** {count}")
        lines.append("")
        lines.append("## Statuses")
        for st, count in statuses.most_common():
            lines.append(f"- **{st}:** {count}")
        lines.append("")
        if date_range:
            lines.append(f"**Date Range:** {date_range[0]} → {date_range[1]}")
            lines.append("")
        lines.append(f"**Total Value:** ${total_value:,.2f}")
        lines.append("")
        lines.append("## Priorities")
        for pri, count in priorities.most_common():
            lines.append(f"- **{pri}:** {count}")
        lines.append("")
        lines.append("## Assignees")
        for a, count in assignees.most_common():
            lines.append(f"- **{a}:** {count}")
        content = "\n".join(lines)

    elif report_type == "html":
        rows_html = "".join(
            f"<tr><td>{r.get('id','?')}</td><td>{r.get('title','?')}</td>"
            f"<td>{r.get('status','?')}</td><td>{r.get('priority','?')}</td></tr>\n"
            for r in records[:50]
        )
        cat_html = "".join(
            f"<li>{cat}: {count}</li>\n"
            for cat, count in categories.most_common()
        )
        content = (
            "<html><body>\n"
            f"<h1>Data Report — {datetime.now().strftime('%Y-%m-%d')}</h1>\n"
            f"<p>Total Records: {total}</p>\n"
            "<h2>Categories</h2><ul>\n" + cat_html + "</ul>\n"
            f"<h2>Records (top 50)</h2>\n<table border='1'>"
            "<tr><th>ID</th><th>Title</th><th>Status</th><th>Priority</th></tr>\n"
            + rows_html + "</table>\n"
            "</body></html>"
        )
    elif report_type == "json":
        content = json.dumps({
            "generated_at": datetime.now().isoformat(),
            "total": total,
            "categories": dict(categories),
            "statuses": dict(statuses),
            "date_range": date_range,
            "total_value": total_value,
            "priorities": dict(priorities),
            "assignees": dict(assignees),
        }, indent=2)
    else:
        return {"success": False, "error": f"Unknown report type: {report_type}"}

    # Write
    Path(output_path).write_text(content)
    return {"success": True, "path": output_path, "type": report_type}

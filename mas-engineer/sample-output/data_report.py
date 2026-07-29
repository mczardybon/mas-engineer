"""Report generator — builds HTML/Markdown/JSON reports from raw data."""
import json
from collections import Counter
from datetime import date, datetime
from pathlib import Path
from typing import Any


# ── Aggregation helpers ────────────────────────────────────────────────


def _summarize_records(
    records: list[dict[str, Any]],
) -> dict[str, Any]:
    """Accumulate counters and totals over the record list."""
    categories: Counter[str] = Counter()
    statuses: Counter[str] = Counter()
    priorities: Counter[str] = Counter()
    assignees: Counter[str] = Counter()
    total_value = 0.0
    date_range: tuple[str, str] | None = None

    for rec in records:
        categories[rec.get("category", "unknown")] += 1
        statuses[rec.get("status", "unknown")] += 1
        priorities[rec.get("priority", "none")] += 1
        assignees[rec.get("assignee", "unassigned")] += 1

        val = rec.get("value", 0)
        if isinstance(val, (int, float)):
            total_value += val

        created = rec.get("created_at")
        if created:
            if date_range is None:
                date_range = (created, created)
            else:
                if created < date_range[0]:
                    date_range = (created, date_range[1])
                if created > date_range[1]:
                    date_range = (date_range[0], created)

    return {
        "total": len(records),
        "categories": categories,
        "statuses": statuses,
        "priorities": priorities,
        "assignees": assignees,
        "total_value": total_value,
        "date_range": date_range,
    }


# ── Format helpers ─────────────────────────────────────────────────────


def _build_markdown(summary: dict[str, Any]) -> str:
    """Render summary as a Markdown report."""
    lines = [f"# Data Report — {datetime.now().strftime('%Y-%m-%d')}", ""]
    lines.append(f"**Total Records:** {summary['total']}")
    lines.append("")
    lines.append("## Categories")
    for cat, count in summary["categories"].most_common():
        lines.append(f"- **{cat}:** {count}")
    lines.append("")
    lines.append("## Statuses")
    for st, count in summary["statuses"].most_common():
        lines.append(f"- **{st}:** {count}")
    lines.append("")
    dr = summary["date_range"]
    if dr:
        lines.append(f"**Date Range:** {dr[0]} → {dr[1]}")
        lines.append("")
    lines.append(f"**Total Value:** ${summary['total_value']:,.2f}")
    lines.append("")
    lines.append("## Priorities")
    for pri, count in summary["priorities"].most_common():
        lines.append(f"- **{pri}:** {count}")
    lines.append("")
    lines.append("## Assignees")
    for a, count in summary["assignees"].most_common():
        lines.append(f"- **{a}:** {count}")
    return "\n".join(lines)


def _build_html(records: list[dict[str, Any]], summary: dict[str, Any]) -> str:
    """Render summary + top-50 record table as an HTML page."""
    rows_html = "".join(
        f"<tr><td>{r.get('id','?')}</td><td>{r.get('title','?')}</td>"
        f"<td>{r.get('status','?')}</td><td>{r.get('priority','?')}</td></tr>\n"
        for r in records[:50]
    )
    cat_html = "".join(
        f"<li>{cat}: {count}</li>\n"
        for cat, count in summary["categories"].most_common()
    )
    return (
        "<html><body>\n"
        f"<h1>Data Report — {datetime.now().strftime('%Y-%m-%d')}</h1>\n"
        f"<p>Total Records: {summary['total']}</p>\n"
        "<h2>Categories</h2><ul>\n" + cat_html + "</ul>\n"
        "<h2>Records (top 50)</h2>\n<table border='1'>"
        "<tr><th>ID</th><th>Title</th><th>Status</th><th>Priority</th></tr>\n"
        + rows_html + "</table>\n"
        "</body></html>"
    )


def _build_json(summary: dict[str, Any]) -> str:
    """Render summary as a JSON string."""
    return json.dumps({
        "generated_at": datetime.now().isoformat(),
        "total": summary["total"],
        "categories": dict(summary["categories"]),
        "statuses": dict(summary["statuses"]),
        "date_range": summary["date_range"],
        "total_value": summary["total_value"],
        "priorities": dict(summary["priorities"]),
        "assignees": dict(summary["assignees"]),
    }, indent=2)


# ── Public entry point ─────────────────────────────────────────────────


def generate_report(data_path: str, report_type: str, output_path: str) -> dict[str, Any]:
    """Load data, analyze, format, and write a report."""
    with open(data_path) as f:
        raw = json.load(f)

    records: list[dict[str, Any]] = raw.get("records", [])
    summary = _summarize_records(records)

    formatters = {
        "markdown": _build_markdown,
        "html": lambda s, _r=records: _build_html(_r, s),
        "json": _build_json,
    }
    formatter = formatters.get(report_type)
    if formatter is None:
        return {"success": False, "error": f"Unknown report type: {report_type}"}

    content = formatter(summary)
    Path(output_path).write_text(content)
    return {"success": True, "path": output_path, "type": report_type}

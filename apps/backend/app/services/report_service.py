"""Weekly driver PDF report — Spec Phase 12D."""

from __future__ import annotations

from io import BytesIO
from typing import Any


def build_weekly_pdf(report: dict[str, Any]) -> bytes:
    """Minimal PDF (no heavy deps) using plain PDF operators."""
    driver_id = str(report.get("driver_id") or "unknown")
    score = report.get("safety_score")
    events = report.get("events") or {}
    spark = report.get("sparkline") or []
    lines = [
        "BMW AI — Weekly Driver Report",
        f"Driver: {driver_id}",
        f"Safety score (avg): {score if score is not None else 'n/a'}",
        "Events:",
    ]
    for key, val in events.items():
        lines.append(f"  - {key}: {val}")
    if spark:
        lines.append("Sparkline: " + ", ".join(str(round(float(x), 1)) for x in spark[:14]))
    lines.append("Phase 12D")

    # Escape PDF string specials
    def esc(s: str) -> str:
        return s.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")

    content_lines = ["BT", "/F1 11 Tf", "50 750 Td", "14 TL"]
    for i, line in enumerate(lines):
        if i == 0:
            content_lines.append(f"({esc(line)}) Tj")
        else:
            content_lines.append("T*")
            content_lines.append(f"({esc(line)}) Tj")
    content_lines.append("ET")
    stream = "\n".join(content_lines).encode("latin-1", errors="replace")

    objects: list[bytes] = []
    objects.append(b"1 0 obj<< /Type /Catalog /Pages 2 0 R >>endobj\n")
    objects.append(b"2 0 obj<< /Type /Pages /Kids [3 0 R] /Count 1 >>endobj\n")
    objects.append(
        b"3 0 obj<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        b"/Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>endobj\n"
    )
    objects.append(
        f"4 0 obj<< /Length {len(stream)} >>stream\n".encode()
        + stream
        + b"\nendstream\nendobj\n"
    )
    objects.append(b"5 0 obj<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>endobj\n")

    out = BytesIO()
    out.write(b"%PDF-1.4\n")
    offsets = [0]
    for obj in objects:
        offsets.append(out.tell())
        out.write(obj)
    xref_pos = out.tell()
    out.write(f"xref\n0 {len(objects) + 1}\n".encode())
    out.write(b"0000000000 65535 f \n")
    for off in offsets[1:]:
        out.write(f"{off:010d} 00000 n \n".encode())
    out.write(
        f"trailer<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_pos}\n%%EOF\n".encode()
    )
    return out.getvalue()

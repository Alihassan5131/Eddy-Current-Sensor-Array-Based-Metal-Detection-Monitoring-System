"""
utils.py — Export, formatting, and logging utilities
"""

import csv
import io
import logging
import os
from datetime import datetime
from typing import List, Dict, Any

import pandas as pd

import config

# ─────────────────────────────────────────────────────────────────────────────
#  LOGGING
# ─────────────────────────────────────────────────────────────────────────────

def configure_logging(level: int = logging.INFO):
    logging.basicConfig(
        level=level,
        format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    # suppress noisy libraries
    logging.getLogger("paho").setLevel(logging.WARNING)
    logging.getLogger("streamlit").setLevel(logging.WARNING)


# ─────────────────────────────────────────────────────────────────────────────
#  FORMATTING
# ─────────────────────────────────────────────────────────────────────────────

def fmt_ts(ts: str) -> str:
    """Shorten ISO timestamp for table display."""
    try:
        dt = datetime.fromisoformat(ts)
        return dt.strftime("%H:%M:%S.%f")[:-3]
    except Exception:
        return ts


def fmt_strength(val: int) -> str:
    bar = "█" * (val // 10) + "░" * (10 - val // 10)
    return f"{bar} {val}"


def fmt_speed(val: float) -> str:
    return f"{val:.3f} m/s"


# ─────────────────────────────────────────────────────────────────────────────
#  EXPORT — CSV
# ─────────────────────────────────────────────────────────────────────────────

def export_csv(rows: List[Dict]) -> bytes:
    if not rows:
        return b""
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=rows[0].keys())
    writer.writeheader()
    writer.writerows(rows)
    return buf.getvalue().encode()


# ─────────────────────────────────────────────────────────────────────────────
#  EXPORT — Excel
# ─────────────────────────────────────────────────────────────────────────────

def export_excel(rows: List[Dict]) -> bytes:
    df = pd.DataFrame(rows)
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Detections")
    return buf.getvalue()


# ─────────────────────────────────────────────────────────────────────────────
#  EXPORT — PDF (text-based via fpdf2)
# ─────────────────────────────────────────────────────────────────────────────

def export_pdf_report(stats: Dict[str, Any], rows: List[Dict]) -> bytes:
    try:
        from fpdf import FPDF
    except ImportError:
        return b"fpdf2 not installed - run: pip install fpdf2"

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 16)
    pdf.set_text_color(0, 160, 200)
    pdf.cell(0, 10, "ConveyorAI - Detection Report", ln=True, align="C")

    pdf.set_font("Helvetica", size=9)
    pdf.set_text_color(60, 60, 60)
    pdf.cell(0, 6, f"Generated: {datetime.utcnow().isoformat()} UTC", ln=True, align="C")
    pdf.ln(6)

    # KPI table
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(0, 8, "System Statistics", ln=True)
    pdf.set_font("Helvetica", size=10)
    for k, v in stats.items():
        pdf.cell(60, 6, str(k).replace("_", " ").title(), border=1)
        pdf.cell(80, 6, str(v), border=1, ln=True)

    pdf.ln(4)

    # Event log (last 50)
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 8, "Recent Detections (last 50)", ln=True)
    pdf.set_font("Helvetica", size=7)
    headers = ["timestamp", "sensor", "object_id", "signal_strength", "duration_ms", "belt_speed"]
    col_w   = [38, 20, 22, 30, 24, 24]
    for h, w in zip(headers, col_w):
        pdf.cell(w, 6, h, border=1)
    pdf.ln()
    for row in rows[:50]:
        for h, w in zip(headers, col_w):
            pdf.cell(w, 5, str(row.get(h, "")), border=1)
        pdf.ln()

    return pdf.output()


# ─────────────────────────────────────────────────────────────────────────────
#  MISC
# ─────────────────────────────────────────────────────────────────────────────

def ensure_export_dir():
    os.makedirs(config.EXPORT_DIR, exist_ok=True)


def signal_color(strength: int) -> str:
    if strength >= 70:
        return "#39ff14"   # strong — green
    elif strength >= 40:
        return "#ffaa00"   # medium — amber
    return "#ff4757"       # weak — red

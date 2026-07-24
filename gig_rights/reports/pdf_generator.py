"""PDF Compliance Report & Payslip Generator using ReportLab."""

from io import BytesIO
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import (
    HRFlowable,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


def generate_compliance_pdf(
    worker_id: str,
    worker_type: str,
    pay_period_start: str,
    pay_period_end: str,
    hours_worked: float,
    gross_pay: float,
    accrued_hours: float,
    holiday_pay_due: float,
    rationale: str,
    output_target: str | Path | BytesIO | None = None,
) -> bytes | str | Path:
    """
    Generates a professional PDF compliance statement & holiday pay breakdown.
    """

    buffer = output_target if isinstance(output_target, BytesIO) else BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36,
    )

    styles = getSampleStyleSheet()

    # Custom typography styles
    title_style = ParagraphStyle(
        "DocTitle",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=20,
        leading=24,
        textColor=colors.HexColor("#1E293B"),
    )
    subtitle_style = ParagraphStyle(
        "DocSubtitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=10,
        leading=14,
        textColor=colors.HexColor("#64748B"),
    )
    section_heading = ParagraphStyle(
        "SectionHeading",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=12,
        leading=16,
        textColor=colors.HexColor("#0F172A"),
        spaceBefore=10,
        spaceAfter=6,
    )
    body_style = ParagraphStyle(
        "BodyTextCustom",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=13,
        textColor=colors.HexColor("#334155"),
    )

    story = []

    # Header
    story.append(Paragraph("GigRights Compliance Statement", title_style))
    story.append(
        Paragraph(
            "UK Statutory Holiday Entitlement Breakdown (2026 Rules)", subtitle_style
        )
    )
    story.append(Spacer(1, 12))
    story.append(
        HRFlowable(
            width="100%", thickness=1, color=colors.HexColor("#E2E8F0"), spaceAfter=15
        )
    )

    # Summary Metadata Table
    meta_data = [
        [
            Paragraph("<b>Worker ID:</b>", body_style),
            Paragraph(worker_id, body_style),
            Paragraph("<b>Pay Period Start:</b>", body_style),
            Paragraph(pay_period_start, body_style),
        ],
        [
            Paragraph("<b>Classification:</b>", body_style),
            Paragraph(worker_type.replace("_", " ").title(), body_style),
            Paragraph("<b>Pay Period End:</b>", body_style),
            Paragraph(pay_period_end, body_style),
        ],
    ]

    meta_table = Table(meta_data, colWidths=[90, 160, 100, 160])
    meta_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
                ("PADDING", (0, 0), (-1, -1), 6),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]
        )
    )
    story.append(meta_table)
    story.append(Spacer(1, 15))

    # Calculation Breakdown Table
    story.append(Paragraph("Pay & Holiday Entitlement Calculation", section_heading))

    calc_data = [
        [Paragraph("<b>Metric</b>", body_style), Paragraph("<b>Value</b>", body_style)],
        [
            Paragraph("Hours Worked in Period", body_style),
            Paragraph(f"{hours_worked:.2f} hrs", body_style),
        ],
        [
            Paragraph("Gross Pay in Period", body_style),
            Paragraph(f"£{gross_pay:.2f}", body_style),
        ],
        [
            Paragraph("Statutory Holiday Accrual (12.07%)", body_style),
            Paragraph(f"<b>{accrued_hours:.2f} hrs</b>", body_style),
        ],
        [
            Paragraph("Statutory Holiday Pay Due", body_style),
            Paragraph(f"<b>£{holiday_pay_due:.2f}</b>", body_style),
        ],
    ]

    calc_table = Table(calc_data, colWidths=[320, 190])
    calc_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0F172A")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                ("PADDING", (0, 0), (-1, -1), 8),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
                ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#FFFFFF")),
                (
                    "BACKGROUND",
                    (0, 3),
                    (-1, -1),
                    colors.HexColor("#F1F5F9"),
                ),  # Highlight totals
            ]
        )
    )

    # Fix header text color for dark background
    header_style = ParagraphStyle(
        "HeaderStyle", parent=body_style, textColor=colors.white
    )
    calc_data[0] = [
        Paragraph("<b>Metric</b>", header_style),
        Paragraph("<b>Value</b>", header_style),
    ]

    story.append(calc_table)
    story.append(Spacer(1, 15))

    # Statutory Rationale
    story.append(Paragraph("Statutory Rationale & Audit Trail", section_heading))
    story.append(Paragraph(rationale, body_style))
    story.append(Spacer(1, 20))

    # Footer Notice
    story.append(
        HRFlowable(
            width="100%", thickness=0.5, color=colors.HexColor("#CBD5E1"), spaceAfter=10
        )
    )
    story.append(
        Paragraph(
            "<i>This document was automatically generated by GigRights Engine v1.0. "
            "Calculations adhere to UK Employment Rights Act rules for statutory holiday pay.</i>",
            subtitle_style,
        )
    )

    # Build PDF
    doc.build(story)

    if output_target is None or isinstance(output_target, BytesIO):
        buffer.seek(0)
        return buffer.getvalue()
    elif isinstance(output_target, (str, Path)):
        return output_target

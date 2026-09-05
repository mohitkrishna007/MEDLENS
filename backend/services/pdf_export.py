import os
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from backend.models import Patient

def generate_patient_pdf(patient: Patient) -> bytes:
    """Generates a downloadable PDF report for the patient record."""
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
    story = []
    
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle('DocTitle', parent=styles['Heading1'], fontSize=22, textColor=colors.HexColor("#0f766e"), spaceAfter=10)
    h2_style = ParagraphStyle('DocH2', parent=styles['Heading2'], fontSize=14, textColor=colors.HexColor("#1e293b"), spaceBefore=12, spaceAfter=6)
    body_style = ParagraphStyle('DocBody', parent=styles['Normal'], fontSize=9, textColor=colors.HexColor("#334155"), leading=12)
    alert_style = ParagraphStyle('DocAlert', parent=styles['Normal'], fontSize=9, textColor=colors.HexColor("#991b1b"), leading=12)
    disclaimer_style = ParagraphStyle('DocDisc', parent=styles['Italic'], fontSize=8, textColor=colors.HexColor("#64748b"), leading=10)

    # 1. Header
    story.append(Paragraph("<b>MedLens — Structured Clinical Patient Record</b>", title_style))
    story.append(Paragraph(f"<b>Patient Name:</b> {patient.display_name} &nbsp;|&nbsp; <b>ID:</b> {patient.patient_id_code} &nbsp;|&nbsp; <b>Age:</b> {patient.age or 'N/A'} &nbsp;|&nbsp; <b>Sex:</b> {patient.sex or 'N/A'}", body_style))
    story.append(Spacer(1, 10))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#cbd5e1"), spaceAfter=15))

    # 2. Intake Summary
    story.append(Paragraph("Patient Overview & Intake", h2_style))
    conds = ", ".join([c.get("name", "") for c in (patient.conditions or []) if c.get("name")]) or "None documented"
    syms = ", ".join([s.get("name", "") for s in (patient.symptoms or []) if s.get("name")]) or "None documented"
    meds = ", ".join([f"{m.get('name','')} {m.get('dose','')}" for m in (patient.medications or []) if m.get("name")]) or "None documented"
    
    intake_data = [
        [Paragraph("<b>Conditions:</b>", body_style), Paragraph(conds, body_style)],
        [Paragraph("<b>Symptoms:</b>", body_style), Paragraph(syms, body_style)],
        [Paragraph("<b>Medications:</b>", body_style), Paragraph(meds, body_style)],
    ]
    t_intake = Table(intake_data, colWidths=[100, 440])
    t_intake.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#f8fafc")),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#e2e8f0")),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('PADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(t_intake)
    story.append(Spacer(1, 15))

    # 3. Lab Results Table
    story.append(Paragraph("Extracted Laboratory Results", h2_style))
    lab_headers = [
        Paragraph("<b>Test Name</b>", body_style),
        Paragraph("<b>Value</b>", body_style),
        Paragraph("<b>Unit</b>", body_style),
        Paragraph("<b>Ref Range</b>", body_style),
        Paragraph("<b>Status</b>", body_style),
        Paragraph("<b>Date</b>", body_style),
        Paragraph("<b>Source</b>", body_style)
    ]
    lab_table_data = [lab_headers]

    for lab in patient.lab_results:
        status_color = "#16a34a" if lab.status == "NORMAL" else ("#dc2626" if lab.status in ["LOW", "HIGH"] else "#64748b")
        status_p = Paragraph(f"<font color='{status_color}'><b>{lab.status}</b></font>", body_style)
        
        lab_table_data.append([
            Paragraph(lab.test_name, body_style),
            Paragraph(lab.value, body_style),
            Paragraph(lab.unit or "-", body_style),
            Paragraph(lab.reference_range or "Not provided", body_style),
            status_p,
            Paragraph(lab.test_date or "-", body_style),
            Paragraph(lab.source_document_name or "User Intake", body_style)
        ])

    t_labs = Table(lab_table_data, colWidths=[110, 50, 45, 95, 60, 65, 115])
    t_labs.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#f1f5f9")),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#cbd5e1")),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('PADDING', (0,0), (-1,-1), 5),
    ]))
    story.append(t_labs)
    story.append(Spacer(1, 15))

    # 4. Conflicts Radar Section
    if patient.conflicts:
        story.append(Paragraph("Potential Record Inconsistencies / Conflicts", h2_style))
        for c in patient.conflicts:
            c_text = f"<b>[{c.conflict_type}]</b> {c.description}<br/>• {c.source_a_name}: <i>{c.source_a_value}</i><br/>• {c.source_b_name}: <i>{c.source_b_value}</i>"
            story.append(Paragraph(c_text, alert_style))
            story.append(Spacer(1, 4))
        story.append(Spacer(1, 10))

    # 5. AI Summary & Disclaimer
    if patient.summaries:
        summary_obj = patient.summaries[-1]
        story.append(Paragraph("AI-Generated Clinical Summary", h2_style))
        story.append(Paragraph(summary_obj.text_summary.replace("\n", "<br/>"), body_style))
        story.append(Spacer(1, 10))
        story.append(Paragraph(summary_obj.disclaimer, disclaimer_style))

    doc.build(story)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes

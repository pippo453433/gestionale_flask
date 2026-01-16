from reportlab.pdfgen import canvas
from io import BytesIO

def genera_fattura_pdf(ordine):
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer)

    pdf.setFont("Helvetica", 12)
    pdf.drawString(50, 800, f"Fattura Ordine #{ordine.id}")
    pdf.drawString(50, 780, f"Cliente: {ordine.nome} {ordine.cognome}")
    pdf.drawString(50, 760, f"Email: {ordine.email}")
    pdf.drawString(50, 740, f"Totale: € {ordine.totale}")
    pdf.drawString(50, 720, f"Data: {ordine.data_ordine.strftime('%d/%m/%Y')}")

    y = 690
    pdf.drawString(50, y, "Dettagli ordine:")
    y -= 20

    for det in ordine.dettagli:
        pdf.drawString(50, y, f"- {det.prodotto.nome} x{det.quantita}  €{det.prezzo_unitario}")
        y -= 20

    pdf.save()
    buffer.seek(0)
    return buffer
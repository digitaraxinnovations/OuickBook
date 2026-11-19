from fastapi import Response

from app.services.customer_documents_service import PdfFile


def pdf_response(pdf: PdfFile) -> Response:
    """Send a PDF that the browser shows (inline) and can also save."""
    return Response(
        content=pdf.content,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{pdf.filename}"'},
    )

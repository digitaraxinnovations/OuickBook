from fastapi import APIRouter, Depends, Response, status

from app.api.deps import get_attachment_service, get_current_user
from app.models import User
from app.schemas.purchase import AttachmentLink, AttachmentRead, AttachmentUpload
from app.services.attachment_service import AttachmentService

router = APIRouter(prefix="/attachments", tags=["Attachments & receipts"])


@router.get("", response_model=list[AttachmentRead])
def list_attachments(
    entity_type: str,
    entity_id: int | None = None,
    user: User = Depends(get_current_user),
    service: AttachmentService = Depends(get_attachment_service),
):
    return service.list_for(user.company_id, entity_type.upper(), entity_id)


@router.get("/receipts", response_model=list[AttachmentRead])
def list_receipts_inbox(
    user: User = Depends(get_current_user),
    service: AttachmentService = Depends(get_attachment_service),
):
    """Receipts uploaded but not yet added to an expense or bill."""
    return service.list_inbox(user.company_id)


@router.post("", response_model=AttachmentRead, status_code=status.HTTP_201_CREATED)
def upload_attachment(
    data: AttachmentUpload,
    user: User = Depends(get_current_user),
    service: AttachmentService = Depends(get_attachment_service),
):
    return service.upload(user.company_id, data)


@router.get("/{attachment_id}/content")
def download_attachment(
    attachment_id: int,
    user: User = Depends(get_current_user),
    service: AttachmentService = Depends(get_attachment_service),
):
    attachment = service.get(user.company_id, attachment_id)
    return Response(
        content=attachment.content,
        media_type=attachment.mime_type,
        headers={"Content-Disposition": f'inline; filename="{attachment.filename}"'},
    )


@router.put("/{attachment_id}/link", response_model=AttachmentRead)
def link_attachment(
    attachment_id: int,
    data: AttachmentLink,
    user: User = Depends(get_current_user),
    service: AttachmentService = Depends(get_attachment_service),
):
    return service.link(user.company_id, attachment_id, data)


@router.delete("/{attachment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_attachment(
    attachment_id: int,
    user: User = Depends(get_current_user),
    service: AttachmentService = Depends(get_attachment_service),
):
    service.delete(user.company_id, attachment_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)

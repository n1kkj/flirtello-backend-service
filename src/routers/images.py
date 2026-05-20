import logging
from urllib.parse import urljoin
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select, text

from src.db.lib.billing.paid_actions import is_image_paid
from src.db.lib.content_models import DirectusFile, ImageInfo
from src.dependencies import get_current_user, get_session
from src.lib.config import config
from src.lib.verifier import TokenData

router = APIRouter()

logger = logging.getLogger(__name__)


class ImageDataResponse(BaseModel):
    image_type: str
    url: str
    is_blurred: bool


@router.get("/images/{image_id}")
async def get_image_data(
    image_id: str,
    current_user: TokenData = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> ImageDataResponse:
    image_id = UUID(image_id)
    img = session.get(ImageInfo, image_id)
    if img is None:
        raise HTTPException(status_code=404, detail="Image not found")

    user_id = UUID(current_user.user_id)
    if img.is_free:
        is_blurred = False
    else:
        is_blurred = not is_image_paid(session, user_id, image_id)

    file_id = img.image_blurred if is_blurred else img.image
    file = session.get(DirectusFile, file_id)
    if file is None:
        logger.error(f"File {file_id} not found")
        raise HTTPException(status_code=404, detail="Image not found")

    url = urljoin(config.storage_root, file.filename_disk)
    print(url)

    return ImageDataResponse(image_type=img.rating, url=url, is_blurred=is_blurred)


class ImagesDataResponse(BaseModel):
    image_id: str
    image_type: str
    url: str
    is_blurred: bool


@router.post("/images")
async def get_images_data(
    images_ids: list[UUID],
    current_user: TokenData = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> list[ImagesDataResponse]:
    res = []
    user_id = UUID(current_user.user_id)
    stmt = text(
        """
        WITH paid_images AS (
            SELECT additional_data->>'image_id' AS image_id
            FROM content.transactions
            WHERE user_id = :user_id
            )
        SELECT DISTINCT
            img.id AS image_id,
            img.rating,
            img.is_free,
            img.image,
            img.image_blurred,
            file.filename_disk,
            (pi.image_id IS NOT NULL) AS is_paid,
            CASE
                WHEN img.is_free OR (pi.image_id IS NOT NULL) THEN img.image
                ELSE img.image_blurred
            END AS selected_image
        FROM content.content_images img
        LEFT JOIN paid_images pi ON pi.image_id = CAST(img.id AS TEXT)
        LEFT JOIN content.directus_files file ON file.id = 
            CASE
                WHEN img.is_free OR (pi.image_id IS NOT NULL) THEN img.image
                ELSE img.image_blurred
            END
        WHERE CAST(img.id AS TEXT) = ANY(:images_ids);
        """
    ).params(user_id=user_id, images_ids=[str(image_id) for image_id in images_ids])

    results = session.exec(stmt).all()
    not_blurred = []
    blurred = []

    for image in results:
        if image.filename_disk is None:
            logger.error(f"File not found for image {image.image_id}")
            raise HTTPException(status_code=404, detail="Image not found")

        url = urljoin(config.storage_root, image.filename_disk)
        print(url)
        is_blurred = not image.is_paid and not image.is_free

        response = ImagesDataResponse(
            image_id=image.image_id.hex, image_type=image.rating, url=url, is_blurred=is_blurred
        )

        if is_blurred:
            blurred.append(response)
        else:
            not_blurred.append(response)

    return not_blurred + blurred

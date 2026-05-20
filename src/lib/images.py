import asyncio
from logging import getLogger
from urllib.parse import urljoin
from uuid import UUID

from sqlalchemy import text
from sqlmodel import Session

from src.db.lib.content_models import DirectusFile, ImageInfo, LLMStats
from src.db.lib.images import get_next_image, mark_image_as_seen
from src.db.lib.messages import send_message
from src.lib.config import config
from src.routers.images import ImagesDataResponse

logger = getLogger(__name__)


async def process_image_getting(
    session: Session,
    user_id: UUID,
    char_id: int,
    image_type: str,
) -> ImageInfo:
    i: ImageInfo = get_next_image(session, user_id, char_id, image_type)
    await asyncio.sleep(1)
    # записать сообщение в базу
    send_message(
        session,
        char_id,
        user_id,
        "character",
        "",
        LLMStats.dummy(),
        [{"type": "image", "id": i.id.hex}],
    )
    # пометить картинку как просмотренную
    mark_image_as_seen(session, user_id, i.id)

    return i


def get_directus_filename_disk(
    session: Session,
    file_id: UUID | None,
) -> str | None:
    if not file_id:
        return None
    file = session.get(DirectusFile, file_id)
    return file.filename_disk


def get_images_data(
    images_ids: list[UUID],
    user_id: UUID,
    session: Session,
) -> list[ImagesDataResponse]:
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

    # Create a mapping of image_id to database result
    results_map = {str(result.image_id): result for result in results}

    responses = []
    # Iterate through original images_ids to maintain order
    for image_id in images_ids:
        result = results_map.get(str(image_id))
        if result is None:
            continue

        if result.filename_disk is None:
            raise ValueError(f"File not found for image {result.image_id}")

        url = urljoin(config.storage_root, result.filename_disk)
        is_blurred = not result.is_paid and not result.is_free

        response = ImagesDataResponse(
            image_id=result.image_id.hex, image_type=result.rating, url=url, is_blurred=is_blurred
        )
        responses.append(response)

    return responses

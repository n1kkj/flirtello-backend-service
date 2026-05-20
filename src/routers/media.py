from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlmodel import Session, select

from src.db.lib.chat_models import Channel, Message
from src.dependencies import get_current_user, get_debug_user, get_session
from src.lib.images import get_images_data
from src.lib.verifier import TokenData
from src.schemas.media import MediaResponse

router = APIRouter(prefix="/media", tags=["Media"])


@router.get("/{char_id}")
async def get_media(
    char_id: int,
    in_ascending_order: bool = True,
    with_character_profile_images: bool = False,
    current_user: TokenData = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> MediaResponse:
    user_id = UUID(current_user.user_id)
    images_ids = []
    if with_character_profile_images:
        character_profile_images = session.exec(
            text(
                """ SELECT profile_images_ids
                    FROM public.characters
                    WHERE id = :char_id
                """
            ),
            params={"char_id": char_id},
        )
        character_profile_images: list[UUID] = character_profile_images.scalars().first()
        images_ids.extend(character_profile_images)
    channels = session.exec(
        select(Channel).where(Channel.char_id == char_id, Channel.user_id == user_id)
    ).all()
    for channel in channels:
        stmt = select(Message).where(Message.channel_id == channel.id)
        if in_ascending_order:
            messages_with_attachments = session.exec(stmt.order_by(Message.inserted_at.asc())).all()
        else:
            messages_with_attachments = session.exec(stmt.order_by(Message.inserted_at.desc())).all()
        for message in messages_with_attachments:
            if message.attachments:
                for attachment in message.attachments:
                    images_ids.append(UUID(attachment["id"]))

    images_data = get_images_data(images_ids, user_id, session)
    return MediaResponse(attachments=images_data)

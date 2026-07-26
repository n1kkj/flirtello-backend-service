from typing import List, Optional

from sqlalchemy import text
from sqlmodel import Session


def get_character(session: Session, character_id: int) -> Optional[dict]:
    """
    Get a character by ID from the public.characters view
    """
    query = text("SELECT * FROM content.characters WHERE id = :id")
    result = session.exec(query, params={"id": character_id})
    row = result.first()
    return dict(row._mapping) if row else None


def get_characters(session: Session, *, limit: int = 100, offset: int = 0) -> List[dict]:
    """
    Get characters from the public.characters view
    """
    query = text(
        """
        SELECT * FROM content.characters 
        ORDER BY sort ASC NULLS LAST
        LIMIT :limit OFFSET :offset
    """
    )

    result = session.exec(query, params={"limit": limit, "offset": offset})

    return [dict(row._mapping) for row in result]

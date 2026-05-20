import asyncio
import logging
import os
from decimal import Decimal
from typing import List, Optional, cast
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import APIKeyHeader
from pydantic import BaseModel, Field
from sqlalchemy.orm import selectinload
from sqlmodel import Session, insert, select, update

from src.db.lib.landing_models import Landing as DBLanding
from src.lib.config import config
from src.lib.images import get_directus_filename_disk, process_image_getting

from ..dependencies import get_current_user, get_session
from ..lib.verifier import TokenData
from ..schemas.landings import Landing as LandingResponse
from ..schemas.landings import *

router = APIRouter(tags=["Landings"])

api_key_header = APIKeyHeader(name="API-KEY", auto_error=False)


def validate_api_key(api_key: str):
    if api_key != config.api_key:
        raise HTTPException(status_code=403, detail="Invalid API Key")


@router.get("/landings")
async def get_all_landings(
    api_key: str = Depends(api_key_header),
    session: Session = Depends(get_session),
) -> list[Landing]:
    validate_api_key(api_key)
    stmt = select(DBLanding).where(DBLanding.status == "published")
    landings = session.exec(stmt).all()
    res = []
    for landing in landings:
        main_sections = [
            MainSection(
                **section.model_dump(),
                subsections=[
                    MainSubsection(
                        **subsections.model_dump(exclude={"image"}),
                        image=get_directus_filename_disk(session, subsections.image),
                    )
                    for subsections in section.subsections
                ],
            )
            for section in landing.main_sections
        ]
        benefits_sections = [
            BenefitsSection(
                **section.model_dump(),
                subsections=[
                    BenefitsSubsection(
                        **subsections.model_dump(exclude={"image"}),
                        image=get_directus_filename_disk(session, subsections.image),
                    )
                    for subsections in section.subsections
                ],
            )
            for section in landing.benefits_sections
        ]
        faq_sections = [
            FAQSection(
                **section.model_dump(),
                subsections=[
                    FAQSubsection(**subsections.model_dump()) for subsections in section.subsections
                ],
            )
            for section in landing.faq_sections
        ]
        more_ai_sections = [
            MoreAISection(
                **section.model_dump(),
                subsections=[
                    MoreAISubsection(**subsections.model_dump())
                    for subsections in section.subsections
                ],
            )
            for section in landing.more_ai_sections
        ]
        characters_sections = [
            CharactersSection(
                **section.model_dump(),
                content_characters=[
                    CharactersSectionContentCharacter(**subsections.model_dump())
                    for subsections in section.content_characters
                ],
            )
            for section in landing.characters_sections
        ]
        secondary_sections = [
            SecondarySection(
                **section.model_dump(),
            )
            for section in landing.secondary_sections
        ]
        conclusion_sections = [
            ConclusionSection(
                **section.model_dump(),
            )
            for section in landing.conclusion_sections
        ]
        landing = LandingResponse(
            **landing.model_dump(exclude={"main_image"}),
            main_image=get_directus_filename_disk(session, landing.main_image),
            main_sections=main_sections,
            benefits_sections=benefits_sections,
            faq_sections=faq_sections,
            more_ai_sections=more_ai_sections,
            characters_sections=characters_sections,
            secondary_sections=secondary_sections,
            conclusion_sections=conclusion_sections,
        )
        res.append(landing)

    return res


@router.get("/landings/{slug}")
async def get_landing_by_slug(
    slug: str,
    api_key: str = Depends(api_key_header),
    session: Session = Depends(get_session),
) -> Landing:
    validate_api_key(api_key)
    stmt = select(DBLanding).where(DBLanding.status == "published", DBLanding.slug == slug)
    landing = session.exec(stmt).first()
    if not landing:
        raise HTTPException(status_code=404, detail="No landing with entered slug")

    main_sections = [
        MainSection(
            **section.model_dump(),
            subsections=[
                MainSubsection(
                    **subsections.model_dump(exclude={"image"}),
                    image=get_directus_filename_disk(session, subsections.image),
                )
                for subsections in section.subsections
            ],
        )
        for section in landing.main_sections
    ]
    benefits_sections = [
        BenefitsSection(
            **section.model_dump(),
            subsections=[
                BenefitsSubsection(
                    **subsections.model_dump(exclude={"image"}),
                    image=get_directus_filename_disk(session, subsections.image),
                )
                for subsections in section.subsections
            ],
        )
        for section in landing.benefits_sections
    ]
    faq_sections = [
        FAQSection(
            **section.model_dump(),
            subsections=[
                FAQSubsection(**subsections.model_dump()) for subsections in section.subsections
            ],
        )
        for section in landing.faq_sections
    ]
    more_ai_sections = [
        MoreAISection(
            **section.model_dump(),
            subsections=[
                MoreAISubsection(**subsections.model_dump()) for subsections in section.subsections
            ],
        )
        for section in landing.more_ai_sections
    ]
    characters_sections = [
        CharactersSection(
            **section.model_dump(),
            content_characters=[
                CharactersSectionContentCharacter(**subsections.model_dump())
                for subsections in section.content_characters
            ],
        )
        for section in landing.characters_sections
    ]
    secondary_sections = [
        SecondarySection(
            **section.model_dump(),
        )
        for section in landing.secondary_sections
    ]
    conclusion_sections = [
        ConclusionSection(
            **section.model_dump(),
        )
        for section in landing.conclusion_sections
    ]
    landing_models = LandingResponse(
        **landing.model_dump(exclude={"main_image"}),
        main_image=get_directus_filename_disk(session, landing.main_image),
        main_sections=main_sections,
        benefits_sections=benefits_sections,
        faq_sections=faq_sections,
        more_ai_sections=more_ai_sections,
        characters_sections=characters_sections,
        secondary_sections=secondary_sections,
        conclusion_sections=conclusion_sections,
    )

    return landing_models

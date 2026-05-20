from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class LandingBase(BaseModel):
    status: str = Field(default="draft", max_length=255)

    date_created: Optional[datetime] = None
    main_title: Optional[str] = Field(default="NSWF AI Chat", max_length=255)
    main_subtitle: Optional[str] = Field(
        default="Explore the World of AI Sexting: Your Guide to Flirtello.com", max_length=255
    )
    slug: Optional[str] = None
    meta_title: Optional[str] = None
    meta_description: Optional[str] = None
    main_image: Optional[UUID | str] = None
    main_button_text: Optional[str] = None
    main_button_link: Optional[str] = None
    main_sections: List["MainSection"] = []
    benefits_sections: List["BenefitsSection"] = []
    characters_sections: List["CharactersSection"] = []
    conclusion_sections: List["ConclusionSection"] = []
    faq_sections: List["FAQSection"] = []
    secondary_sections: List["SecondarySection"] = []
    more_ai_sections: List["MoreAISection"] = []

    class Config:
        orm_mode = True
        arbitrary_types_allowed = True
        # Exclude fields from the serialized schema
        fields = {
            "date_updated": {"exclude": True},
            "landing_id": {"exclude": True},
            "user_updated": {"exclude": True},
        }


class Landing(LandingBase):
    id: int


class BenefitsSectionBase(BaseModel):
    sort: Optional[int] = None

    date_created: Optional[datetime] = None
    title: Optional[str] = Field(
        default="Benefits of Using the NSFW AI Chat Platform", max_length=255
    )
    subtitle: Optional[str] = Field(
        default="Embracing the world of AI sexting unlocks numerous benefits:", max_length=255
    )
    button_text: Optional[str] = Field(default="Try it for free!", max_length=255)
    button_link: Optional[str] = None
    subsections: List["BenefitsSubsection"] = []

    class Config:
        orm_mode = True
        arbitrary_types_allowed = True
        fields = {
            "date_updated": {"exclude": True},
            "landing_id": {"exclude": True},
            "user_updated": {"exclude": True},
        }


class BenefitsSection(BenefitsSectionBase):
    id: int


class BenefitsSubsectionBase(BaseModel):
    status: str = Field(default="draft", max_length=255)
    sort: Optional[int] = None

    date_created: Optional[datetime] = None
    title: Optional[str] = None
    text: Optional[str] = None
    image: Optional[UUID | str] = None

    class Config:
        orm_mode = True
        arbitrary_types_allowed = True
        fields = {
            "date_updated": {"exclude": True},
            "faq_section_id": {"exclude": True},
            "user_updated": {"exclude": True},
        }


class BenefitsSubsection(BenefitsSubsectionBase):
    id: int


class CharactersSectionBase(BaseModel):
    sort: Optional[int] = None

    date_created: Optional[datetime] = None
    title: Optional[str] = Field(default="Characters", max_length=255)
    content_characters: List["CharactersSectionContentCharacter"] = []

    class Config:
        orm_mode = True
        arbitrary_types_allowed = True
        fields = {
            "date_updated": {"exclude": True},
            "landing_id": {"exclude": True},
            "user_updated": {"exclude": True},
        }


class CharactersSection(CharactersSectionBase):
    id: int


class CharactersSectionContentCharacterBase(BaseModel):
    sort: Optional[int] = None
    content_characters_id: Optional[int] = None

    class Config:
        orm_mode = True
        arbitrary_types_allowed = True
        fields = {
            "landings_characters_section_id": {"exclude": True},
            "content_characters_id": {"exclude": True},
            "date_updated": {"exclude": True},
            "user_updated": {"exclude": True},
        }


class CharactersSectionContentCharacter(CharactersSectionContentCharacterBase):
    id: int


class ConclusionSectionBase(BaseModel):
    sort: Optional[int] = None

    date_created: Optional[datetime] = None
    title: Optional[str] = None
    text: Optional[str] = None
    button_text: Optional[str] = Field(default="Try it for free!", max_length=255)
    button_link: Optional[str] = None

    class Config:
        orm_mode = True
        arbitrary_types_allowed = True
        fields = {
            "date_updated": {"exclude": True},
            "landing_id": {"exclude": True},
            "user_updated": {"exclude": True},
        }


class ConclusionSection(ConclusionSectionBase):
    id: int


class FAQSectionBase(BaseModel):
    sort: Optional[int] = None

    date_created: Optional[datetime] = None
    title: Optional[str] = Field(default="Q&A Block", max_length=255)
    subtitle: Optional[str] = Field(
        default="Your NSFW Character AI Chat Questions Answered", max_length=255
    )
    subsections: List["FAQSubsection"] = []

    class Config:
        orm_mode = True
        arbitrary_types_allowed = True
        fields = {
            "date_updated": {"exclude": True},
            "landing_id": {"exclude": True},
            "user_updated": {"exclude": True},
        }


class FAQSection(FAQSectionBase):
    id: int


class FAQSubsectionBase(BaseModel):
    sort: Optional[int] = None

    date_created: Optional[datetime] = None
    question: Optional[str] = None
    answer: Optional[str] = None

    class Config:
        orm_mode = True
        arbitrary_types_allowed = True
        fields = {
            "faq_section_id": {"exclude": True},
            "date_updated": {"exclude": True},
            "user_updated": {"exclude": True},
        }


class FAQSubsection(FAQSubsectionBase):
    id: int


class MainSectionBase(BaseModel):
    sort: Optional[int] = None

    date_created: Optional[datetime] = None

    class Config:
        orm_mode = True
        arbitrary_types_allowed = True
        fields = {
            "date_updated": {"exclude": True},
            "landing_id": {"exclude": True},
            "user_updated": {"exclude": True},
        }


class MainSection(MainSectionBase):
    id: int

    subsections: List["MainSubsection"] = []


class MainSubsectionBase(BaseModel):
    sort: Optional[int] = None

    date_created: Optional[datetime] = None
    title: Optional[str] = None
    text: Optional[str] = None
    button_text: Optional[str] = Field(default="Try it for free!", max_length=255)
    button_link: Optional[str] = None
    image: Optional[UUID | str] = None

    class Config:
        orm_mode = True
        arbitrary_types_allowed = True
        fields = {
            "date_updated": {"exclude": True},
            "landings_main_section_id": {"exclude": True},
            "user_updated": {"exclude": True},
        }


class MainSubsection(MainSubsectionBase):
    id: int


class MoreAISectionBase(BaseModel):
    sort: Optional[int] = None

    date_created: Optional[datetime] = None
    title: Optional[str] = Field(default="More NSFW Al Chat with Flirtello.com")

    class Config:
        orm_mode = True
        arbitrary_types_allowed = True
        fields = {
            "date_updated": {"exclude": True},
            "landing_id": {"exclude": True},
            "user_updated": {"exclude": True},
        }


class MoreAISection(MoreAISectionBase):
    id: int
    subsections: List["MoreAISubsection"] = []


class MoreAISubsection(BaseModel):
    id: int = Field(default=None, primary_key=True)
    sort: Optional[int] = None
    button_text: Optional[str] = None
    button_link: Optional[str] = None

    class Config:
        orm_mode = True
        arbitrary_types_allowed = True


class SecondarySectionBase(BaseModel):
    title: Optional[str] = None
    text: Optional[str] = None
    button_text: Optional[str] = "Try it for free!"
    button_link: Optional[str] = None
    sort: Optional[int] = None

    class Config:
        orm_mode = True
        arbitrary_types_allowed = True
        fields = {
            "date_updated": {"exclude": True},
            "landing_id": {"exclude": True},
            "user_updated": {"exclude": True},
        }


class SecondarySection(SecondarySectionBase):
    id: int

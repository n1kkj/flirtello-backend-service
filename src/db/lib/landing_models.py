from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlmodel import Field, Relationship, SQLModel


class Landing(SQLModel, table=True):
    __tablename__ = "landings"
    __table_args__ = {"schema": "content"}

    id: int = Field(default=None, primary_key=True)
    status: str = Field(default="draft", max_length=255)
    user_created: Optional[UUID] = Field(default=None, foreign_key="directus_users.id")
    date_created: Optional[datetime] = None
    user_updated: Optional[UUID] = Field(default=None, foreign_key="directus_users.id")
    date_updated: Optional[datetime] = None
    slug: Optional[str] = Field(unique=True)
    meta_title: Optional[str] = Field(default=None)
    meta_description: Optional[str] = Field(default=None)

    main_title: Optional[str] = Field(default="NSWF AI Chat", max_length=255)
    main_subtitle: Optional[str] = Field(
        default="Explore the World of AI Sexting: Your Guide to Flirtello.com", max_length=255
    )
    main_image: Optional[UUID] = Field(default=None, foreign_key="directus_files.id")
    main_button_text: Optional[str] = Field(default=None, max_length=255)
    main_button_link: Optional[str] = Field(default=None, max_length=255)

    main_sections: list["MainSection"] = Relationship(back_populates="landing")
    benefits_sections: list["BenefitsSection"] = Relationship(back_populates="landing")
    characters_sections: list["CharactersSection"] = Relationship(back_populates="landing")
    conclusion_sections: list["ConclusionSection"] = Relationship(back_populates="landing")
    faq_sections: list["FAQSection"] = Relationship(back_populates="landing")
    secondary_sections: list["SecondarySection"] = Relationship(back_populates="landing")
    more_ai_sections: list["MoreAISection"] = Relationship(back_populates="landing")


class BenefitsSection(SQLModel, table=True):
    __tablename__ = "landings_benefits_section"
    __table_args__ = {"schema": "content"}

    id: int = Field(default=None, primary_key=True)
    sort: Optional[int] = None
    user_created: Optional[UUID] = Field(default=None, foreign_key="content.directus_users.id")
    date_created: Optional[datetime] = None
    user_updated: Optional[UUID] = Field(default=None, foreign_key="content.directus_users.id")
    date_updated: Optional[datetime] = None
    title: Optional[str] = Field(
        default="Benefits of Using the NSFW AI Chat Platform", max_length=255
    )
    subtitle: Optional[str] = Field(
        default="Embracing the world of AI sexting unlocks numerous benefits:", max_length=255
    )
    button_text: Optional[str] = Field(default="Try it for free!", max_length=255)
    button_link: Optional[str] = None
    landing_id: Optional[int] = Field(default=None, foreign_key="content.landings.id")

    landing: Landing = Relationship(back_populates="benefits_sections")
    subsections: list["BenefitsSubsection"] = Relationship(back_populates="benefits_section")


class BenefitsSubsection(SQLModel, table=True):
    __tablename__ = "landings_benefits_subsection"
    __table_args__ = {"schema": "content"}

    id: int = Field(default=None, primary_key=True)
    status: str = Field(default="draft", max_length=255)
    sort: Optional[int] = None
    user_created: Optional[UUID] = Field(default=None, foreign_key="content.directus_users.id")
    date_created: Optional[datetime] = None
    user_updated: Optional[UUID] = Field(default=None, foreign_key="content.directus_users.id")
    date_updated: Optional[datetime] = None
    title: Optional[str] = None
    text: Optional[str] = None
    image: Optional[UUID] = Field(default=None, foreign_key="content.directus_files.id")
    benefits_section_id: Optional[int] = Field(
        default=None, foreign_key="content.landings_benefits_section.id"
    )

    benefits_section: BenefitsSection = Relationship(back_populates="subsections")


class CharactersSection(SQLModel, table=True):
    __tablename__ = "landings_characters_section"
    __table_args__ = {"schema": "content"}

    id: int = Field(default=None, primary_key=True)
    sort: Optional[int] = None
    user_created: Optional[UUID] = Field(default=None, foreign_key="content.directus_users.id")
    date_created: Optional[datetime] = None
    user_updated: Optional[UUID] = Field(default=None, foreign_key="content.directus_users.id")
    date_updated: Optional[datetime] = None
    title: Optional[str] = Field(default="Characters", max_length=255)
    landing_id: Optional[int] = Field(default=None, foreign_key="content.landings.id")

    landing: Landing = Relationship(back_populates="characters_sections")
    content_characters: list["CharactersSectionContentCharacter"] = Relationship(
        back_populates="characters_section"
    )


class CharactersSectionContentCharacter(SQLModel, table=True):
    __tablename__ = "landings_characters_section_content_characters"
    __table_args__ = {"schema": "content"}

    id: int = Field(default=None, primary_key=True)
    landings_characters_section_id: Optional[int] = Field(
        default=None, foreign_key="content.landings_characters_section.id"
    )
    content_characters_id: Optional[int] = Field(
        default=None, foreign_key="content.content_characters.id"
    )
    sort: Optional[int] = None

    characters_section: CharactersSection = Relationship(back_populates="content_characters")


class ConclusionSection(SQLModel, table=True):
    __tablename__ = "landings_conclusion_section"
    __table_args__ = {"schema": "content"}

    id: int = Field(default=None, primary_key=True)
    sort: Optional[int] = None
    user_created: Optional[UUID] = Field(default=None, foreign_key="content.directus_users.id")
    date_created: Optional[datetime] = None
    user_updated: Optional[UUID] = Field(default=None, foreign_key="content.directus_users.id")
    date_updated: Optional[datetime] = None
    title: Optional[str] = None
    text: Optional[str] = None
    button_text: Optional[str] = Field(default="Try it for free!", max_length=255)
    button_link: Optional[str] = None
    landing_id: Optional[int] = Field(default=None, foreign_key="content.landings.id")

    landing: Landing = Relationship(back_populates="conclusion_sections")


class FAQSection(SQLModel, table=True):
    __tablename__ = "landings_faq_section"
    __table_args__ = {"schema": "content"}

    id: int = Field(default=None, primary_key=True)
    sort: Optional[int] = None
    user_created: Optional[UUID] = Field(default=None, foreign_key="content.directus_users.id")
    date_created: Optional[datetime] = None
    user_updated: Optional[UUID] = Field(default=None, foreign_key="content.directus_users.id")
    date_updated: Optional[datetime] = None
    title: Optional[str] = Field(default="Q&A Block", max_length=255)
    subtitle: Optional[str] = Field(
        default="Your NSFW Character AI Chat Questions Answered", max_length=255
    )
    landing_id: Optional[int] = Field(default=None, foreign_key="content.landings.id")

    landing: Landing = Relationship(back_populates="faq_sections")
    subsections: list["FAQSubsection"] = Relationship(back_populates="faq_section")


class FAQSubsection(SQLModel, table=True):
    __tablename__ = "landings_faq_subsection"
    __table_args__ = {"schema": "content"}

    id: int = Field(default=None, primary_key=True)
    sort: Optional[int] = None
    user_created: Optional[UUID] = Field(default=None, foreign_key="content.directus_users.id")
    date_created: Optional[datetime] = None
    user_updated: Optional[UUID] = Field(default=None, foreign_key="content.directus_users.id")
    date_updated: Optional[datetime] = None
    question: Optional[str] = None
    answer: Optional[str] = None
    faq_section_id: Optional[int] = Field(
        default=None, foreign_key="content.landings_faq_section.id"
    )

    faq_section: FAQSection = Relationship(back_populates="subsections")


class MainSection(SQLModel, table=True):
    __tablename__ = "landings_main_section"
    __table_args__ = {"schema": "content"}

    id: int = Field(default=None, primary_key=True)
    sort: Optional[int] = None
    user_created: Optional[UUID] = Field(default=None, foreign_key="content.directus_users.id")
    date_created: Optional[datetime] = None
    user_updated: Optional[UUID] = Field(default=None, foreign_key="content.directus_users.id")
    date_updated: Optional[datetime] = None
    landing_id: Optional[int] = Field(default=None, foreign_key="content.landings.id")

    landing: Landing = Relationship(back_populates="main_sections")
    subsections: list["MainSubsection"] = Relationship(back_populates="main_section")


class MainSubsection(SQLModel, table=True):
    __tablename__ = "landings_main_subsection"
    __table_args__ = {"schema": "content"}

    id: int = Field(default=None, primary_key=True)
    sort: Optional[int] = None
    user_created: Optional[UUID] = Field(default=None, foreign_key="content.directus_users.id")
    date_created: Optional[datetime] = None
    user_updated: Optional[UUID] = Field(default=None, foreign_key="content.directus_users.id")
    date_updated: Optional[datetime] = None
    title: Optional[str] = None
    text: Optional[str] = None
    button_text: Optional[str] = Field(default="Try it for free!", max_length=255)
    button_link: Optional[str] = None
    image: Optional[UUID] = Field(default=None, foreign_key="content.directus_files.id")
    landings_main_section_id: Optional[int] = Field(
        default=None, foreign_key="content.landings_main_section.id"
    )
    main_section: MainSection = Relationship(back_populates="subsections")


class MoreAISection(SQLModel, table=True):
    __tablename__ = "landings_more_ai_section"
    __table_args__ = {"schema": "content"}

    id: int = Field(default=None, primary_key=True)
    sort: Optional[int] = None
    user_created: Optional[UUID] = Field(default=None, foreign_key="content.directus_users.id")
    date_created: Optional[datetime] = None
    user_updated: Optional[UUID] = Field(default=None, foreign_key="content.directus_users.id")
    date_updated: Optional[datetime] = None
    title: Optional[str] = Field(default="More NSFW Al Chat with Flirtello.com")
    landing_id: Optional[int] = Field(default=None, foreign_key="content.landings.id")

    landing: Optional[Landing] = Relationship(back_populates="more_ai_sections")
    subsections: list["MoreAISubsection"] = Relationship(back_populates="more_ai_section")


class MoreAISubsection(SQLModel, table=True):
    __table_args__ = {"schema": "content"}
    __tablename__ = "landings_more_ai_subsection"

    id: int = Field(default=None, primary_key=True)
    sort: Optional[int] = None
    user_created: Optional[UUID] = Field(default=None, foreign_key="content.directus_users.id")
    date_created: Optional[datetime] = None
    user_updated: Optional[UUID] = Field(default=None, foreign_key="content.directus_users.id")
    date_updated: Optional[datetime] = None
    button_text: Optional[str] = None
    button_link: Optional[str] = None
    more_ai_section_id: Optional[int] = Field(
        default=None, foreign_key="content.landings_more_ai_section.id"
    )

    more_ai_section: Optional[MoreAISection] = Relationship(back_populates="subsections")


class SecondarySection(SQLModel, table=True):
    __tablename__ = "landings_secondary_section"
    __table_args__ = {"schema": "content"}

    id: int = Field(default=None, primary_key=True)
    sort: Optional[int] = None
    user_created: Optional[UUID] = Field(default=None, foreign_key="content.directus_users.id")
    date_created: Optional[datetime] = None  # Adjust type if necessary
    user_updated: Optional[UUID] = Field(default=None, foreign_key="content.directus_users.id")
    date_updated: Optional[datetime] = None  # Adjust type if necessary
    title: Optional[str] = None
    text: Optional[str] = None
    button_text: Optional[str] = Field(default="Try it for free!")
    button_link: Optional[str] = None
    landing_id: Optional[int] = Field(default=None, foreign_key="content.landings.id")

    landing: Optional[Landing] = Relationship(back_populates="secondary_sections")

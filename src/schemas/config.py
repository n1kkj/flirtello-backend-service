from typing import Optional
from uuid import UUID

from pydantic import BaseModel


class CommonConfigSchema(BaseModel):
    include_default_images: Optional[bool] = True

    class Config:
        extra = "ignore"


class CharConfigSchema(BaseModel):
    common: CommonConfigSchema

    class Config:
        extra = "ignore"

from typing import Optional

from pydantic import BaseModel


class BannerResponse(BaseModel):
    title: str
    description: Optional[str]
    desktop_background: Optional[str]
    mobile_background: Optional[str]
    button_url: Optional[str]

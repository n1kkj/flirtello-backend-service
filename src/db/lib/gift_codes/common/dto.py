from dataclasses import dataclass

from .models import GiftCode, GiftCodeUserLink


@dataclass
class GiftCodeActivationDTO:
    gift_code: GiftCode
    gift_code_activation: GiftCodeUserLink

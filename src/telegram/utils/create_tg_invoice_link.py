from typing import Dict, List, Union

import httpx


async def create_tg_invoice_link(
    bot_token: str,
    title: str,
    description: str,
    payload: dict[str, str],
    prices: List[Dict[str, Union[int, str]]],
) -> str:
    """
    Create a Telegram invoice link for Stars payment using raw HTTP request.

    Args:
        bot_token: Telegram Bot token
        title: Title of the invoice
        description: Description of what is being purchased
        payload: JSON-serialized data about the invoice
        prices: Array of objects with amount and label fields [{"label": "Product", "amount": 100}]

    Returns:
        str: Invoice link URL
    """
    url = f"https://api.telegram.org/bot{bot_token}/createInvoiceLink"

    data = {
        "title": title,
        "description": description,
        "payload": payload,
        "provider_token": "",  # Empty for Stars payment
        "currency": "XTR",  # XTR is used for Stars
        "prices": prices,
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(url, json=data)
        response_data = response.json()

        if not response.is_success or not response_data.get("ok"):
            raise Exception(
                f"Failed to create invoice link: {response_data.get('description', 'Unknown error')}"
            )

        return response_data["result"]

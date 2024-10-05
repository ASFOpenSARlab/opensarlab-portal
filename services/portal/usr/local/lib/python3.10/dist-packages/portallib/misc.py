from urllib.parse import quote
import logging

import httpx
from opensarlab.auth import encryptedjwt


async def is_deployment_healthy(lab_short_name: str) -> bool:
    try:
        url = f"http://127.0.0.1/lab/{quote(lab_short_name)}/hub/health"
        async with httpx.AsyncClient() as client:
            response = await client.get(url=url, timeout=15)

        if response.status_code == 200:
            logging.info(f"Lab {lab_short_name} return healthy")
            return True
        else:
            return False
    except Exception as e:
        logging.error(f"Error getting health of {lab_short_name}: {e}")
        return False


async def send_email(email: dict):
    """
    payload = {
        "to": {
            "username": list | str,
            "email": list | str
        },
        "from": {
            "username": str,
            "emails": str
        },
        "cc": {
            "username": list | str,
            "email": list | str
        },
        "subject": str,
        "html_body": str
    }
    """
    try:
        data = encryptedjwt.encrypt(email)
        url = "http://127.0.0.1/user/email/send"
        async with httpx.AsyncClient() as client:
            r = await client.post(url=url, data=data, timeout=15)
        r.raise_for_status

    except Exception as e:
        logging.error(f"{e}")
        raise


def send_email_sync(email: dict):
    """
    payload = {
        "to": {
            "username": list | str,
            "email": list | str
        },
        "from": {
            "username": str,
            "emails: str
        },
        "cc": {
            "username": list | str,
            "email": list | str
        },
        "subject": str,
        "html_body": str
    }
    """
    try:
        data = encryptedjwt.encrypt(email)
        url = "http://127.0.0.1/user/email/send"
        with httpx.Client() as client:
            r = client.post(url=url, data=data, timeout=15)
            r.raise_for_status

    except Exception as e:
        logging.error(f"Something went wrong with send_email_sync: {e}")
        raise

import requests

from opensarlab.auth import encryptedjwt


username = 'osl-admin'

payload = {
    "to": {
        "username": [username]
    },
    "from": {
        "username": "osl-admin"
    },
    "cc": {
        "username": ["osl-admin"]
    },
    "subject": "OpenScienceLab notification",
    "html_body": f"""
        Hello {username},

        This is a test email!!!
    """
}

url = "http://localhost/user/email/send"

data = encryptedjwt.encrypt(payload)
r = requests.post(url=url, data=data, timeout=15)
r.raise_for_status
print(r)

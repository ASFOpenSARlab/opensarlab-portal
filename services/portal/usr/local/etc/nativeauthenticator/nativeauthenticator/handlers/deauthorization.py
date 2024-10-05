from hashlib import blake2b
from base64 import b64decode
from hmac import compare_digest
import json

import escapism

from opensarlab.auth import encryptedjwt

from .extras.base import LocalBase
from .extras.orm import UserInfo


class SignatureNotValidException(Exception):
    pass


class ObjectNotStrOrBytesException(Exception):
    pass


def _get_token_key():

    secret_key = encryptedjwt.get_sso_token_from_file()

    if type(secret_key) is str:
        return secret_key.encode("utf-8")
    elif type(secret_key) is not bytes:
        raise ObjectNotStrOrBytesException("Secret Key needs to be str or bytes")

    return secret_key


def _get_data_from_encoded(payload: str) -> str:
    # Decode data
    data, signature = b64decode(payload).decode("utf-8").split(":::")

    # Make sure data is str, not bytes. This is to ensure consistency.
    if type(data) is bytes:
        data = bytes(data).decode("utf-8")
    elif type(data) is not str:
        raise ObjectNotStrOrBytesException(
            f"Object \"{data}\" is not of type 'str' or 'bytes'"
        )

    # Calculate signature based on local key.
    h = blake2b(digest_size=16, key=_get_token_key())
    h.update(data.encode("utf-8"))
    calculated_good_signature = h.hexdigest()

    # If the local key is the same as the remote key, then the signature will match and the payload is good.
    is_signature_verified = compare_digest(calculated_good_signature, signature)

    if not is_signature_verified:
        raise SignatureNotValidException(f"Signature not verified.")

    return data


class DeauthorizationHandler(LocalBase):
    """Responsible for deauthorize some username or claimname"""

    async def get(self):
        self.set_status(405)
        self.finish("Not Implemented")
        return

    async def post(self):
        """
        Request payload needs to be of the form:

            data = json.dumps({
              "username": unescaped_username,
              "claimname": "claim-escaped_username"
            })

            payload = b64encoded("{data}:::{signature}")

        where the signature is created using hashlib.blake2b with the key being the SSO token.
        """

        payload: str = self.request.body

        try:
            data: str = _get_data_from_encoded(payload)

        except ObjectNotStrOrBytesException as e:
            self.set_status(400)
            self.finish(f"{e}")
            return
        except SignatureNotValidException as e:
            self.set_status(400)
            self.finish(f"{e}")
            return

        try:
            data = json.loads(data)
        except Exception as e:
            self.set_status(400)
            self.finish(f"Payload is not json")
            return

        # If both username and claimname are provided, username is used
        # If neither are provided, throw error
        # If only claimname is provided, parse and unescape to find username
        username = data.get("username", None)
        claimname = data.get("claimname", None)

        if not username and not claimname:
            self.set_status(400)
            self.finish("Username or claimname not provided")
            return

        elif not username:
            username = escapism.unescape(
                claimname.replace("claim-", ""), escape_char="-"
            )

        user = UserInfo.deauthorization(self.db, username)
        if not user:
            self.set_status(400)
            self.finish("User does not exist")
            return

        self.set_status(200)
        self.finish(f"OK. User '{username}' deauthorized.")
        return

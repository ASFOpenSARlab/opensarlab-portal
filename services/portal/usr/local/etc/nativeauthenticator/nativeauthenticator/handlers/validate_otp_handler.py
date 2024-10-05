import tornado
from .extras.base import LocalBase
import pyotp


class ValidateOPTHandler(LocalBase):
    def post(self):
        data = tornado.escape.json_decode(self.request.body)
        input1 = data.get("input1", "")
        input2 = data.get("input2", "")
        secret = data.get("secret", "")

        if secret and input1 and input2:
            totp = pyotp.TOTP(secret)
            valid = totp.verify(input1, valid_window=2) and totp.verify(
                input2, valid_window=1
            )

            self.set_header("Content-Type", "application/json")
            self.write({"valid": valid})
        else:
            self.set_status(400)  # Bad Request
            self.write("Invalid or missing fields.")

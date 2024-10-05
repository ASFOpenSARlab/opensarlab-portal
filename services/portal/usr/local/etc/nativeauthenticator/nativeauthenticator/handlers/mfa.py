import base64
import io
import qrcode


def generate_mfa_uri(username, secret, issuer_name="OpenScienceLab"):
    if not secret:
        return None

    return f"otpauth://totp/{username}?secret={secret}&issuer={issuer_name}"


def generate_mfa_qrcode(username, secret, issuer_name):
    if not secret:
        return None

    qr_obj = qrcode.make(generate_mfa_uri(username, secret, issuer_name))

    with io.BytesIO() as buffer:
        qr_obj.save(buffer, "png")
        otp_qrcode = base64.b64encode(buffer.getvalue()).decode()

    return otp_qrcode

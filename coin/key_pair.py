from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.exceptions import InvalidSignature

from base64 import b64encode, b64decode


class KeyPair:
    """RSA key pair along with methods for signature
    creation and verification.

    Attributes:
        private_key: cryptography RSA key pair
        pub_der: der encoded RSA public key
    """

    def __init__(self):
        """Generates rsa key pair, then der encodes public key"""
        self.private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
            backend=default_backend()
        )

        self.pub_der = self.private_key.public_key().public_bytes(
            encoding=serialization.Encoding.DER,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )

    def sign(self, data):
        """sign post data

        Parameters:
            data (str): post body to be signed

        Returns:
            str: Base64 encoded signature
        """
        data = data.encode()
        signature = self.private_key.sign(
            data,
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA256()
        )

        return b64encode(signature).decode()

    @property
    def pub_key(self):
        return b64encode(self.pub_der).decode()

    @staticmethod
    def verify(signature, data, der_pub_key):
        """Verify request signature

        Parameters:
            signature (str): base64 encoded RSA signature
            data (str): post body to be verified
            der_pub_key (str): der encoded public key

        Returns:
            bool: Signature valid
        """
        data = data.encode()
        der_pub_key = b64decode(der_pub_key.encode())
        signature = b64decode(signature.encode())
        pub_key = serialization.load_der_public_key(der_pub_key, backend=default_backend())
        try:
            pub_key.verify(
                signature,
                data,
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH
                ),
                hashes.SHA256()
            )
        except InvalidSignature:
            return False

        return True

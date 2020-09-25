from __future__ import absolute_import, division, print_function, unicode_literals

from typing import TYPE_CHECKING

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.asymmetric.rsa import generate_private_key
from cryptography.hazmat.primitives.serialization import (
    Encoding,
    NoEncryption,
    PrivateFormat,
    PublicFormat,
    load_der_private_key,
    load_pem_private_key,
)
from OpenSSL import crypto  # pyOpenSSL

from .exceptions import assert_choice

if TYPE_CHECKING:
	from typing import Union

	from cryptography.hazmat.primitives.asymmetric.dh import DHPrivateKey
	from cryptography.hazmat.primitives.asymmetric.dsa import DSAPrivateKey
	from cryptography.hazmat.primitives.asymmetric.ec import EllipticCurvePrivateKey
	from cryptography.hazmat.primitives.asymmetric.rsa import RSAPrivateKey
	from OpenSSL.crypto import X509
	PrivateKey = Union[RSAPrivateKey, DSAPrivateKey, DHPrivateKey, EllipticCurvePrivateKey]

def load_certificate_file(filename):
	# type: (str, ) -> X509

	with open(filename, "rb") as fr:
		return crypto.load_certificate(crypto.FILETYPE_PEM, fr.read())

def get_pubkey_from_x509(x509):
	# type: (X509, ) -> bytes

	return crypto.dump_privatekey(crypto.FILETYPE_ASN1, x509.get_pubkey())

def load_keyfile(filename, encoding="PEM"):
	# type: (str, str) -> PrivateKey

	try:
		load_func = {
			"PEM": load_pem_private_key,
			"DER": load_der_private_key,
		}[encoding]
	except KeyError:
		raise ValueError("Invalid encoding")

	with open(filename, "rb") as fr:
		password = None
		backend = default_backend()
		return load_func(fr.read(), password, backend)

def generate_rsa_keyfile_pair(priv_key, pub_key, key_size=4096, encoding="PEM", format="modern"):
	# type: (str, str, int, str, str) -> RSAPrivateKey

	"""
		encoding: "PEM" -> ASN.1 encoding, "DER" -> base64 PEM
	"""

	if key_size < 2048:
		raise ValueError("key_size must be atleast 2048")

	encodings = {
		"PEM": Encoding.PEM,
		"DER": Encoding.DER,
	}

	private_formats = {
		"modern": PrivateFormat.PKCS8,
		"legacy": PrivateFormat.TraditionalOpenSSL,
	}

	public_formats = {
		"modern": PublicFormat.SubjectPublicKeyInfo,
		"legacy": PublicFormat.PKCS1,
	}

	assert_choice("encoding", encoding, encodings)
	assert_choice("format", format, private_formats)

	public_exponent = 65537
	backend = default_backend()

	key = generate_private_key(public_exponent, key_size, backend)

	with open(priv_key, "wb") as fw:
		fw.write(key.private_bytes(encodings[encoding], private_formats[format], NoEncryption()))

	with open(pub_key, "wb") as fw:
		fw.write(key.public_key().public_bytes(encodings[encoding], public_formats[format]))

	return key

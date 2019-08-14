from __future__ import absolute_import, division, print_function, unicode_literals

from typing import TYPE_CHECKING

from OpenSSL import crypto # pyOpenSSL
from Crypto.PublicKey import RSA # pycryptodome

if TYPE_CHECKING:
	from OpenSSL.crypto import X509
	from Crypto.PublicKey.RSA import RsaKey

def load_certificate_file(filename):
	# type: (str, ) -> X509

	with open(filename, "rb") as fr:
		return crypto.load_certificate(crypto.FILETYPE_PEM, fr.read())

def get_pubkey_from_x509(x509):
	# type: (X509, ) -> bytes

	return crypto.dump_privatekey(crypto.FILETYPE_ASN1, x509.get_pubkey())

def load_rsa_keyfile(filename):
	# type: (str, ) -> RsaKey

	with open(filename, "rb") as fr:
		return RSA.importKey(fr.read())

def generate_rsa_keyfile_pair(priv_key, pub_key, bits=1024*4):
	# type: (str, str, int) -> RsaKey

	key = RSA.generate(bits)

	with open(priv_key, "wb") as fw:
		fw.write(key.exportKey())

	with open(pub_key, "wb") as fw:
		fw.write(key.publickey().exportKey())

	return key

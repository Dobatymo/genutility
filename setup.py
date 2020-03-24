from __future__ import absolute_import, division, print_function, unicode_literals

#don't do `from builtins import str`
from setuptools import setup
from io import open

# nltk.download("punkt")

with open("README.md", "r", encoding="utf-8") as fr:
	long_description = fr.read()

setup(
	author="Dobatymo",
	name="genutility",
	version="0.0.22.post0",
	url="https://github.com/Dobatymo/genutility",
	description="A collection of various Python utilities",
	long_description=long_description,
	long_description_content_type="text/markdown",
	classifiers=[
		"Programming Language :: Python :: 2",
		"Programming Language :: Python :: 3",
		"License :: OSI Approved :: ISC License (ISCL)",
		"Operating System :: OS Independent",
		"Topic :: Utilities",
	],
	packages=["genutility", "genutility/compat", "genutility/fileformats", "genutility/hardware", "genutility/twothree"],
	package_data = {str("genutility"): ["data/*.tsv"]},
	python_requires=">=2.7",
	install_requires=[
		"future",
		"typing;python_version<'3.5'",
		"scandir;python_version<'3.5'",
		"pathlib2;python_version<'3.4'",
		"mock;python_version<'3.3'",
		"contextlib2;python_version<'3.3'",
	],
	extras_require={
		"gensim": ["gensim>=3.3.0", "numpy"],
		"pdf": ["PyPDF2"],
		"tls": ["cryptography", "pyOpenSSL"],
		"toml": ["toml"],
		"json": ["jsonschema"],
		"mediainfo": ["pymediainfo"],
		"ALL": ["av", "aiohttp", "bencode.py", "cryptography", "ctypes-windows-sdk>=0.0.4", "flask", "gensim",
			"msgpack", "netifaces", "nltk", "orderedset", "pyOpenSSL", "PyPDF2", "pypiwin32",
			"rhash", "toml", "unidecode", "werkzeug", "wmi", "wx"],
	},
	use_2to3=False
)

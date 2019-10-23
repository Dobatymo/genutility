from __future__ import absolute_import, division, print_function, unicode_literals

from setuptools import setup
from io import open

# nltk.download("punkt")

with open("README.md", "r", encoding="utf-8") as fr:
	long_description = fr.read()

setup(
	author="Dobatymo",
	name="genutility",
	version="0.0.8",
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
	python_requires=">=2.7",
	install_requires=[
		"future",
		"typing;python_version<'3.5'",
		"scandir;python_version<'3.5'",
		"pathlib;python_version<'3.4'",
		"mock;python_version<'3.3'",
		"contextlib2;python_version<'3.3'",
	],
	extras_require={
		"gensim": ["gensim>=3.3.0", "numpy"],
		"pdf": ["PyPDF2"],
		"tls": ["pycryptodome", "pyOpenSSL"],
		"toml": ["toml"],
		"ALL": ["aiohttp", "bencode.py", "ctypes-windows-sdk", "flask", "gensim", "msgpack",
			"netifaces", "nltk", "orderedset", "pycryptodome", "pyOpenSSL", "PyPDF2", "pypiwin32",
			"rhash", "toml", "unidecode", "werkzeug", "wmi", "wx"],
	},
	use_2to3=False
)

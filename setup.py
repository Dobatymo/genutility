import json
from itertools import chain

from setuptools import setup

# nltk.download("punkt")

with open("README.md", encoding="utf-8") as fr:
    long_description = fr.read()

with open("install_requires.json", encoding="utf-8") as fr:
    install_requires = json.load(fr)

with open("extras_require.json", encoding="utf-8") as fr:
    extras_require = json.load(fr)

extras_require["all"] = sorted(set(chain.from_iterable(extras_require.values())))

setup(
    author="Dobatymo",
    name="genutility",
    version="0.0.108",
    url="https://github.com/Dobatymo/genutility",
    description="A collection of various Python utilities",
    long_description=long_description,
    long_description_content_type="text/markdown",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: ISC License (ISCL)",
        "Operating System :: OS Independent",
        "Topic :: Utilities",
    ],
    packages=["genutility", "genutility.compat", "genutility.fileformats", "genutility.win"],
    package_data={"genutility": ["py.typed", "data/*.tsv"]},
    python_requires=">=3.7",
    install_requires=install_requires,
    extras_require=extras_require,
    license_files=["LICENSE"],
)

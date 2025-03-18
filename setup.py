import json
from itertools import chain

from setuptools import setup

# nltk.download("punkt")

with open("install_requires.json", encoding="utf-8") as fr:
    install_requires = json.load(fr)

with open("extras_require.json", encoding="utf-8") as fr:
    extras_require = json.load(fr)

extras_require["all"] = sorted(set(chain.from_iterable(extras_require.values())))

setup(
    packages=["genutility", "genutility.compat", "genutility.fileformats", "genutility.win"],
    package_data={"genutility": ["py.typed", "fileformats/data/*.tsv"]},
    install_requires=install_requires,
    extras_require=extras_require,
)

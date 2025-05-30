import json
import logging
from itertools import chain
from pathlib import Path
from typing import Dict, Set

global_modules = ["typing_extensions", "cwinsdk"]

modmap = {
    "OpenSSL": "pyOpenSSL>=17.5.0",
    "PIL": "Pillow>=9.2.0",
    "pypdf": "pypdf>=3.1.0,!=5.0.0",
    "aiohttp": "aiohttp>=3.7.4",
    "aioresponses": "aioresponses>=0.7.2",
    "av": "av>=8.0; python_version>='3.8'",
    "bencodepy": "bencode.py>=2.0.0",
    "bs4": "beautifulsoup4",
    "cryptography": "cryptography>=1.5.3",
    "cv2": "opencv-python",
    "cwinsdk": "ctypes-windows-sdk>=0.0.15; sys_platform=='win32'",
    "flask": "flask>=0.12.3",
    "gensim": "gensim>=4.0.0",
    "msgpack": "msgpack>=0.6.0",
    "nltk": "nltk>=3.6.1",
    "numba": "numba; python_version<'3.11'",
    "pkg_resources": "setuptools",
    "pptx": "python-pptx",
    "py7zr": "py7zr>=0.20.2",
    "pyspark": "pyspark>=3.0.0",
    "requests_mock": "requests-mock",
    "rhash": "rhash; sys_platform=='win32'",
    "scipy": "scipy<1.13",  # for gensim
    "simple_salesforce": "simple-salesforce>=1.1.0",
    "sklearn": "scikit-learn",
    "tls_property": "tls-property>=1.0.1",
    "typing_extensions": "typing-extensions>=4.0.0",
    "werkzeug": "werkzeug>=0.11.11",
    "win32com": "pywin32; sys_platform=='win32'",
    "win32evtlog": "pywin32; sys_platform=='win32'",
    "winerror": "pywin32; sys_platform=='win32'",
    "wmi": "wmi; sys_platform=='win32'",
    "wx": "wxPython>=4",
    "yaml": "ruamel.yaml",
    "ruamel": "ruamel.yaml",
    "mistune": "mistune<2",
    "polars": "polars>=1.18; python_version>='3.9'",
    "importlib_metadata": "importlib-metadata>=1.4",
}

BUILTINS = (
    "__main__",
    "_hashlib",
    "collections",
    "concurrent",
    "ctypes",
    "email",
    "http",
    "importlib",
    "multiprocessing",
    "os",
    "unittest",
    "urllib",
    "zlib",
)

MANUAL_FIXES_REPLACE = {
    "genutility.av": ["av", "numpy"],
}

MANUAL_FIXES_ADD = {
    "genutility.bs4": ["bs4"],
    "genutility.flask": ["flask"],
    "genutility.msgpack": ["msgpack"],
    "genutility.networkx": ["networkx"],
    "genutility.numba": ["numba"],
    "genutility.numpy": ["numpy"],
    "genutility.pandas": ["pandas"],
    "genutility.rich": ["rich"],
    "genutility.tensorflow": ["tensorflow"],
    "genutility.toml": ["toml"],
    "genutility.tqdm": ["tqdm"],
    "genutility.twisted": ["twisted"],
}


def lowercase(x):
    return x.lower()


def lowercasekey(x):
    return x[0].lower()


def main(path: Path) -> None:
    install = sorted((modmap.get(modname, modname) for modname in global_modules), key=lowercase)

    with open("install_requires.json", "w", encoding="utf-8") as fw:
        json.dump(install, fw, indent="    ")

    with path.open("rt", encoding="utf-8") as fr:
        extras: Dict[str, Set[str]] = {}
        module = None

        for line in fr:
            line = line.rstrip("\r\n")

            if line.startswith("  "):
                if not line.strip():
                    continue

                assert module is not None
                modname = line[2:].split(".")  # type: ignore[unreachable]

                if modname[0] == "genutility":
                    internal = ".".join(modname[:2])
                    if internal != module:
                        assert internal, modname
                        extras[module].add(internal)
                elif modname[0] not in BUILTINS:
                    if modname[0] not in global_modules:
                        requirement = modmap.get(modname[0], modname[0])
                        assert requirement, modname
                        extras[module].add(requirement)
            else:
                if not line:
                    continue

                modname = line[:-1].split(".")
                if not modname[0] == "genutility":
                    logging.warning("Invalid module: %s", modname)
                    continue

                module = ".".join(modname[:2])
                extras.setdefault(module, set())

        # add replace collisions not detected correctly by findimports
        for module, deps in MANUAL_FIXES_REPLACE.items():
            newdeps = set()
            for dep in deps:
                requirement = modmap.get(dep, dep)
                assert requirement
                newdeps.add(requirement)
            extras[module] = newdeps

        # when importing genutility modules which collide with other packages, also import them
        for module, deps in MANUAL_FIXES_ADD.items():
            for dep in deps:
                requirement = modmap.get(dep, dep)
                assert requirement
                extras[module].add(requirement)

        # add recursive dependencies
        changes = True
        while changes:
            changes = False
            for k in extras.keys():
                new_dep = set()
                for dep in extras[k]:
                    if dep.startswith("genutility."):
                        changes = True
                        new_dep.update(extras[dep])
                    else:
                        new_dep.add(dep)
                extras[k] = new_dep

        # sort dependencies
        sorted_extras = {k: sorted(v, key=lowercase) for k, v in sorted(extras.items(), key=lowercasekey)}

        for k, vals in sorted_extras.items():
            if not k.startswith("genutility."):
                raise ValueError(f"{k} is not part of genutility")

            if k.startswith("_"):
                if vals:
                    raise ValueError(f"{k} shouldn't have dependencies: {vals}")

            for v in vals:
                if v.startswith("genutility."):
                    raise ValueError(f"Recursive solver failed for {k}: {vals}")

        sorted_extras = {k[11:]: v for k, v in sorted_extras.items() if not k.startswith("genutility._")}

        with open("extras_require.json", "w", encoding="utf-8") as fw:
            json.dump(sorted_extras, fw, indent="    ")

        requirements_test = sorted(sorted_extras.pop("tests", []) + install, key=lowercase)

        requirements = sorted(set(chain.from_iterable(sorted_extras.values())) | set(install), key=lowercase)
        with open("requirements.txt", "w", encoding="utf-8") as fw:
            for package in requirements:
                fw.write(package + "\n")

        with open("requirements-test.txt", "w", encoding="utf-8") as fw:
            for package in requirements_test:
                fw.write(package + "\n")

        requirements_dev = sorted(["black", "isort", "flake8", "bandit[toml]>=1.7.5"], key=lowercase)
        with open("requirements-ci.txt", "w", encoding="utf-8") as fw:
            for package in requirements_dev:
                fw.write(package + "\n")


if __name__ == "__main__":
    from argparse import ArgumentParser

    from genutility.args import is_file

    parser = ArgumentParser()
    parser.add_argument("path", type=is_file)
    args = parser.parse_args()

    main(args.path)

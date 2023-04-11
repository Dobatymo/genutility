py -m pip install findimports
py -m findimports --ignore-stdlib "genutility" > all-deps.txt
py findimports-to-extras.py all-deps.txt

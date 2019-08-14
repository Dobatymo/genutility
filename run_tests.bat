rem py -2.7 -m unittest discover "genutility/tests/" "*.py"
rem py -3.5 -m unittest discover "genutility/tests/" "*.py"
rem py -3.6 -m unittest discover "genutility/tests/" "*.py"

py -m genutility.tests.algorithms
py -m genutility.tests.concurrency
py -m genutility.tests.file
py -m genutility.tests.func
py -m genutility.tests.hash
py -m genutility.tests.iter
py -m genutility.tests.math
py -m genutility.tests.ops
py -m genutility.tests.pdf
py -m genutility.tests.sequence
py -m genutility.tests.sort
py -m genutility.tests.string

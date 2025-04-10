rem without the verbose flag the tests sometimes fail with a KeyboardInterrupt !?
py -3.7 -m unittest discover -v genutility.tests "*.py"
py -3.8 -m unittest discover -v genutility.tests "*.py"
py -3.9 -m unittest discover -v genutility.tests "*.py"
py -3.10 -m unittest discover -v genutility.tests "*.py"
py -3.11 -m unittest discover -v genutility.tests "*.py"
pause

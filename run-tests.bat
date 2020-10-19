rem without the verbose flag the tests sometimes fail with a KeyboardInterrupt !?
py -2.7 -m unittest discover -v genutility.tests "*.py"
py -3.6 -m unittest discover -v genutility.tests "*.py"
py -3.7 -m unittest discover -v genutility.tests "*.py"
py -3.8 -m unittest discover -v genutility.tests "*.py"
py -3.9 -m unittest discover -v genutility.tests "*.py"
pause

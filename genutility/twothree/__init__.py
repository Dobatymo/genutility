
try:
	from builtins import FileNotFoundError
except ImportError:
	FileNotFoundError = IOError

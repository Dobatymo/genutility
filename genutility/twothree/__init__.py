
try:
	from builtins import FileNotFoundError
except ImportError:
	FileNotFoundError = IOError

try:
	from builtins import FileExistsError
except ImportError:
	FileExistsError = IOError

from __future__ import absolute_import, division, print_function, unicode_literals

from builtins import filter, range

import sys, os, os.path, subprocess, logging

from ..twothree.filesystem import tofs, fromfs
from ..string import surrounding_join

logger = logging.getLogger(__name__)

class RarError(Exception):
	def __init__(self, msg, returncode=None, cmd=None, output=""):
		Exception.__init__(self, msg)
		self.returncode = returncode
		self.cmd = cmd
		self.output = output

"""WinRAR Exit Codes
255 	USER BREAK	User stopped the process
9	CREATE ERROR	Create file error
8	MEMORY ERROR	Not enough memory for operation
7	USER ERROR	Command line option error
6	OPEN ERROR	Open file error
5	WRITE ERROR	Write to disk error
4	LOCKED ARCHIVE	Attempt to modify an archive previously locked by the 'k' command
3	CRC ERROR	A CRC error occurred when unpacking
2	FATAL ERROR	A fatal error occurred
1	WARNING	Non fatal error(s) occurred
0	SUCCESS	Successful operation (User exit)"""

class Rar(object):

	windows_executable = "C:/Program Files/WinRAR/Rar.exe"

	def __init__(self, archive, executable=None):
		"""archive: archive to work with, everything which is supported by winrar
		executable: path/to/Rar.exe"""

		self.exe = executable or self.windows_executable

		if not os.path.isfile(self.exe):
			raise ValueError("Invalid executable")

		self.archive = archive
		self.filelist = []
		self.cmd = ""
		self.flags = {}
		self.flags["lock"] = [False, "k"]
		self.flags["delete"] = [False, "df"]
		self.flags["test"] = [False, "t"]
		self.flags["filetime"] = [False, "tl"]
		self.flags["append_archive_name"] = [False, "ad"]
		self.options = {}
		self.options["split"] = [False, "v%s"]
		self.options["compression"] = [False, "m%u"]
		self.options["password"] = [False, "p%s"]
		self.options["password_header"] = [False, "hp%s"]
		self.options["recovery"] = [False, "rr%up"]
		self.options["recovery_volumes"] = [False, "rr%u%%"]

	def add_file(self, pathname):
		self.filelist.append(pathname)

	def add_files(self, filelist):
		self.filelist.extend(filelist)

	def set_compression(self, level):
		"""level: 0 store, 1 fastest, 2 fast, 3 normal, 4 good, 5 best (default: 3)"""

		if level not in range(0, 6) and level is not False:
			raise RarError("Invalid parameter: Set compression level (0-store...3-default...5-best)")
		self.options["compression"][0] = level

	def set_password(self, password, encrypt_filenames=False):
		if encrypt_filenames:
			self.options["password_header"][0] = password
			self.options["password"][0] = False
		else:
			self.options["password"][0] = password
			self.options["password_header"][0] = False

	def add_recovery_info(self, rr):
		"""rr: recovery record in percent, only 1-10 is valid"""

		if rr < 1 or rr > 10:
			raise RarError("Only 1%-10% valid")
		self.options["recovery"][0] = rr

	def add_recovery_volumes(self, rv):
		"""rv: number of recovery volumes"""

		self.options["recovery_volumes"][0] = rv

	def split(self, split):
		self.options["split"][0] = split

	def lock(self, flag = True):
		self.flags["lock"][0] = flag

	def delete_after_archiving(self, flag = True):
		"""flag (bool): delete files after archiving"""

		self.flags["delete"][0] = flag

	def test_after_archiving(self, flag = True):
		"""flag (bool): test archive after archiving"""

		self.flags["test"][0] = flag

	def set_archive_to_filetime(self, flag = True):
		self.flags["filetime"][0] = flag

	def commandline(self, cmd):
		self.cmd = cmd.strip()

	def execute(self, args):
		cmd = "{} {}".format(self.exe, args)
		logger.debug("CMD: " + cmd)
		try:
			ret = subprocess.check_output(tofs(cmd), stderr=subprocess.STDOUT, cwd=os.getcwd())
		except UnicodeEncodeError as e:
			raise RarError("UnicodeError, Win32Console fault")
		except subprocess.CalledProcessError as e:
			raise RarError("Error", e.returncode, fromfs(e.cmd), e.output.decode(sys.stdout.encoding)) #should use only stderr

	def test(self, password="-"):
		self.execute('t -p{} "{}"'.format(password, self.archive))

	def get_files_str(self):
		return surrounding_join(" ", self.filelist, "\"", "\"")

	def get_flag_str(self):
		return surrounding_join(" ", [value[1] for value in self.flags.itervalues() if value[0] is True], "-", "")

	def get_options_str(self):
		return surrounding_join(" ", [value[1] % value[0] for value in self.options.itervalues() if value[0] is not False], "-", "")

	def get_args(self, command):
		return "%s %s %s %s \"%s\" %s" % (command, self.get_flag_str(), self.get_options_str(), self.cmd, self.archive, self.get_files_str())

	def create(self):
		self.execute(self.get_args("a"))

	def extract(self, dir, mode = 0):
		self.filelist = [dir]
		if mode == 1:
			self.flags["append_archive_name"][0] = True
		self.execute(self.get_args("x"))

	def close(self):
		pass

def create_rar_from_folder(path, dest_path=".", profile_setter_func=None, filter_func=lambda x:True, name_transform=lambda x:x):
	if not os.path.isdir(path):
		return False

	root, dirname = os.path.split(path)

	if dest_path == ".":
		dest_path = root

	cwd = os.getcwd()
	os.chdir(path)

	try:
		r = Rar(os.path.join(dest_path, "{}.rar".format(name_transform(dirname))))
		if profile_setter_func:
			profile_setter_func(r)
		for c in filter(filter_func, os.listdir(".")): #was: listdir_rec
			r.add_file(c)
		r.create()
	except RarError as e:
		logger.error("%s\n%s" % (str(e), e.output))
		return False

	os.chdir(cwd)
	return True

def create_rar_from_file(path, dest_path=".", profile_setter_func=None, name_transform = lambda x:x):
	root, dirname = os.path.split(path)

	if dest_path == ".":
		dest_path = root

	cwd = os.getcwd()
	os.chdir(root)

	try:
		r = Rar(os.path.join(dest_path, "{}.rar".format(name_transform(dirname))))
		if profile_setter_func:
			profile_setter_func(r)
		r.add_file(dirname)
		r.create()
	except RarError as e:
		logger.error("%s\n%s" % (str(e), e.output))
		return False

	os.chdir(cwd)
	return True

from __future__ import absolute_import, division, print_function, unicode_literals

import logging
import signal
import threading
from multiprocessing import Pool
from queue import Empty, Full, Queue
from typing import TYPE_CHECKING

from .exceptions import NoResult, assert_choice

if TYPE_CHECKING:
	from typing import Any, Callable, Iterable, Iterator, Optional, Tuple, TypeVar, Union
	T = TypeVar("T")
	U = TypeVar("U")

logger = logging.getLogger(__name__)

class Worker(threading.Thread):

	TASK_IDLE = 0
	TASK_COMPLETE = 1
	TASK_EXCEPTION = 2

	def __init__(self, tasks, returns):
		# type: (Queue[Optional[Tuple[int, int, Callable, tuple, dict]]], Queue[Tuple[int, int, Tuple[int, Union[Any, Exception]]]]) -> None

		threading.Thread.__init__(self)
		self.tasks = tasks
		self.returns = returns

		self.daemon = True
		self.running = True
		self.start()

	def run(self):
		# type: () -> None

		while self.running:
			# self.returns.put((self.TASK_IDLE, self))
			task = self.tasks.get(True)
			if task:
				state, id, func, args, kargs = task
			else:
				self.tasks.task_done()
				self.running = False
				break

			try:
				ret = func(*args, **kargs)
			except Exception as e:  # pylint: disable=broad-except
				logger.exception("threaded task failed")
				self.returns.put((state, self.TASK_EXCEPTION, (id, e)))
			else:
				self.returns.put((state, self.TASK_COMPLETE, (id, ret)))

			try:
				self.tasks.task_done()
			except ValueError:  # if the task was canceled inbetween
				pass

		logger.debug("thread ended")

	def cancel(self):
		# type: () -> None

		self.running = False

class ThreadPool(object):

	def __init__(self, num_threads):
		# type: (int, ) -> None

		self.num_threads = num_threads
		self.tasks = Queue()  # type: Queue[Optional[Tuple[int, int, Callable, tuple, dict]]]
		self.returns = Queue()  # type: Queue[Tuple[int, int, Tuple[int, Union[Any, Exception]]]]
		self.my_worker = [Worker(self.tasks, self.returns) for _ in range(num_threads)]
		self.state = 0  # this is used to be able to cancel (or ignore the results of ongoing) tasks

	def add_task(self, id, func, *args, **kargs):
		# type: (int, Callable[..., Any], *Any, **Any) -> None

		self.tasks.put((self.state, id, func, args, kargs))

	def get(self):
		# type: () -> Tuple[int, Optional[Any]]

		while True:  # so invalid states can be ignored
			state, type, result = self.returns.get(True)  # type: Tuple[int, int, Tuple[int, Union[Any, Exception]]]
			if state == self.state:
				if type == Worker.TASK_COMPLETE:
					return result # (id, ret)
				else:
					id, e = result
					return id, None  # maybe raise here?
			#  else: old result, ignore

	@staticmethod
	def clear(queue):
		# type: (Queue[Any], ) -> None

		""" Only undocumented methods. """

		with queue.mutex:
			queue.queue.clear()
			queue.all_tasks_done.notify_all()
			queue.unfinished_tasks = 0

	@staticmethod
	def _clear(queue):
		# type: (Queue[Any], ) -> None

		""" Only uses documented methods, but is slower. """

		while not queue.empty():
			queue.get()
			queue.task_done()

	def close(self, finishall=False):
		# type: (bool, ) -> None

		""" if `finishall` is True, it will finish all tasks currently in the queue,
			if `finishall` is False, only currently active tasks will be finished
		"""

		if finishall:
			for i in range(self.num_threads):
				self.tasks.put(None)
		else:
			for w in self.my_worker:
				w.cancel()

	def cancel(self):
		# type: () -> None

		""" Does not cancel already running tasks. Just clears queue and ignores
			results of currently running tasks.
		"""

		self.clear(self.tasks)
		self.clear(self.returns)
		self.state += 1

	def wait(self):
		# type: () -> None

		self.tasks.join()

def gather_all_unsorted(threadpool, func, params, *args, **kwargs):
	# type: (ThreadPool, Callable, Iterable, tuple, dict) -> Iterator[Tuple[Any, Any]]

	""" Runs multiple tasks concurrently and returns all results in the order
		of execution finish as soon as possible.
	"""

	for i, param in enumerate(params):
		threadpool.add_task(i, func, param, *args, **kwargs)

	for i in range(len(params)):
		yield threadpool.get()

def gather_any(threadpool, func, params, *args, **kwargs):
	# type: (ThreadPool, Callable, Iterable, tuple, dict) -> Tuple[Any, Any]

	""" Runs multiple tasks concurrently and just returns the result of the first
		task which finishes.
	"""

	for id, result in gather_all_unsorted(threadpool, func, params, *args, **kwargs):
		threadpool.cancel()
		return id, result # result will be None, if tasked threw exception
	raise NoResult("No task returned a valid result")

def NotThreadSafe(verify=False):
	# type: (bool, ) -> Callable[type]

	""" Class decorator. Only works on new style classes (object)
		`verify=True` prohibits write access to attributes.
	"""

	def OnClass(TheClass):
		# type: (type, ) -> type

		if verify:
			orig_init = TheClass.__init__
			orig_setattr = TheClass.__setattr__

			def __setattr__(self, name, value):
				if self.thread_ident == threading.current_thread().ident:
					orig_setattr(self, name, value)
				else:
					raise RuntimeError("{}.{} = {} called from different thread".format(TheClass.__name__, name, value))

			def __init__(self, *args, **kws):
				orig_setattr(self, "thread_ident", threading.current_thread().ident)
				orig_init(self, *args, **kws)

			TheClass.__init__ = __init__
			TheClass.__setattr__ = __setattr__
		return TheClass
	return OnClass

class AbortIteration(Exception):
	pass

class IterWorker(threading.Thread):

	STATE_WAITING = 0
	STATE_RUNNING = 1
	STATE_PAUSING = 2
	STATE_PAUSED = 3
	STATE_STOPPED = 4

	CMD_RESUME = 0
	CMD_ABORT = 1

	def __init__(self, taskqueue, onstatechange=None):
		# type: (Queue, Optional[Callable]) -> None

		threading.Thread.__init__(self)
		self.queue = taskqueue
		self.onstatechange = onstatechange
		self.control = Queue()
		self.state = self.STATE_WAITING

	@property
	def state(self):
		# type: () -> int

		return self._state

	@state.setter
	def state(self, value):
		# type: (int, ) -> None

		assert_choice("value", value, (0, 1, 2, 3, 4))

		self._state = value
		if self.onstatechange:
			self.onstatechange(value)

	def run(self):
		# type: () -> None

		while True:
			iter = self.queue.get()
			if not iter:
				self.state = self.STATE_STOPPED
				return
			self.state = self.STATE_RUNNING
			try:
				for __ in iter:
					if self.state == self.STATE_PAUSING:
						self.state = self.STATE_PAUSED
						cmd = self.control.get()
						if cmd == self.CMD_RESUME:
							self.state = self.STATE_RUNNING
							continue
						elif cmd == self.CMD_ABORT:
							break
			except AbortIteration:
				logger.warning("Task aborted")
			except Exception:
				logger.exception("Task threw exception")
			self.queue.task_done() #untested
			self.state = self.STATE_WAITING

	def pause(self):
		# type: () -> None

		if self.state == self.STATE_RUNNING:
			self.state = self.STATE_PAUSING

	def resume(self):
		# type: () -> None

		if self.state == self.STATE_PAUSED:
			self.control.put(self.CMD_RESUME)

	def stop(self):
		# type: () -> None

		if self.state < self.STATE_STOPPED:
			self.queue.put(None)

	def clear(self):
		# type: () -> None

		try:
			while True:
				self.queue.get_nowait()
				self.queue.task_done()
		except Empty:
			pass

	def abort(self):
		# type: () -> None

		self.pause()
		self.control.put(self.CMD_ABORT)

# was: DownloadWorker
class ProgressWorker(threading.Thread):
	def __init__(self, manager, tasks):
		threading.Thread.__init__(self)
		self.manager = manager
		self.tasks = tasks

		self.running = True
		self.task, self.done, self.total = None, None, None

	def run(self):
		while self.running:
			self.task = self.tasks.get()
			if self.task:
				func, args, kwargs = self.task
			else:
				break

			try:
				result = func(self.report, *args, **kwargs)
			except Exception:
				logger.exception("Task failed")
				result = None
			self.task, self.done, self.total = None, None, None
			self.manager.finalize(result)

	def quit(self):
		self.running = False

	def report(self, done, total):
		self.done = done
		self.total = total

	def get(self):  # not using locks atm, can return inconsistent data
		if self.task and self.done and self.total:
			return (self.task, self.done, self.total)
		else:
			return None

# was: ThreadedDownloader
class ProgressThreadPool(object):

	def __init__(self, concurrent=1):
		# from config
		self.concurrent = concurrent

		self.waiting_queue = Queue()
		self.completed = []
		self.failed = []
		self.lock = threading.Lock()

		self.workers = list(ProgressWorker(self, self.waiting_queue) for i in range(self.concurrent))
		for w in self.workers:
			w.daemon = True  # program will end even if threads are still running
			w.start()

	def start(self, callable, *args, **kwargs):
		self.waiting_queue.put((callable, args, kwargs))

	def finalize(self, result):
		if result:
			setter, status, localname, length = result
			with self.lock:
				if status:
					self.failed.append((status, localname, length))
				else:
					self.completed.append((localname, length))
					setter(localname)
		else:  # task failed
			pass

	def clear_completed(self):
		self.completed = []  # assignment is atomic right?

	def cancel_pending(self):
		# copied from https://stackoverflow.com/a/18873213
		with self.waiting_queue.mutex:
			self.waiting_queue.queue.clear()
			self.waiting_queue.all_tasks_done.notify_all()
			self.waiting_queue.unfinished_tasks = 0

	def get_waiting(self):
		return list(task for task in self.waiting_queue.queue if task)

	def get_completed(self):
		return self.completed

	def get_failed(self):
		return self.failed

	def get_running(self):  # no locks, inconsistent data
		return list(task for task in (w.get() for w in self.workers) if task)

class BoundedQueue(object):

	# similar: pip install bounded-iterator

	""" Semaphor bounded queue. Can be used with `multiprocessing.Pool` for example.
		`imap()` calls iterable from same process but different thread.

		Other semaphore classes like `multiprocessing.BoundedSemaphore` can be used as well.
	"""

	def __init__(self, size, it, timeout=None, semaphore=threading.BoundedSemaphore):
		# type: (int, Iterable[T], Optional[float], Callable[[int], Any]) -> None

		self.semaphore = semaphore(size)
		self.iterable = it
		self.timeout = timeout
		self.iterator = None # type: Optional[Iterator[T]]

	def __iter__(self):
		# type: () -> Iterator[T]

		self.iterator = iter(self.iterable)
		return self

	def __next__(self):
		# type: () -> T

		if self.iterator is None:
			raise TypeError

		if not self.semaphore.acquire(timeout=self.timeout):
			raise Full("BoundedQueue semaphore acquisition timed out")

		return next(self.iterator)

	def done(self):
		# type: () -> None

		self.semaphore.release()

def _ignore_sigint():
	# type: () -> None

	""" This need to be pickle'able to work with `multiprocessing.Pool`.
	"""

	signal.signal(signal.SIGINT, signal.SIG_IGN)

def parallel_map(func, it, ordered=True, parallel=True, processes=None, bufsize=1, chunksize=1):
	# type: (Callable[[T], U], Iterable[T], bool, bool, Optional[int], int, int) -> Iterator[U]

	""" Parallel map which uses multiprocessing to distribute tasks.
		`bufsize` should be used to limit memory usage when the iterable `it`
		can be processed faster than the output iterator is consumed.

		Keyboard interrupts are ignored in child processes. They should however be terminated
		correctly by the main thread.
	"""

	if parallel:

		q = BoundedQueue(bufsize, it)

		with Pool(processes, _ignore_sigint) as p:

			if ordered:
				process = p.imap
			else:
				process = p.imap_unordered

			try:
				for item in process(func, q, chunksize):
					yield item
					q.done()
			except GeneratorExit:
				logging.warning("interrupted")
				q.done()  # the semaphore in the bounded queue might block otherwise
				raise
	else:
		for item in it:
			yield func(item)

class ThreadsafeList(list):  # untested!!!

	""" This is a list object with context manager to handle locking to perform multiple operations
		on a list in a threadsafe way.
		Example.
		l = ThreadsafeList([1, 2, 3])
		l.append(4) # atomic, no locking needed
		with l:
			l[0] += 4 # not atomic, thus executed with context manager
	"""

	def __init__(self, it):
		list.__init__(self, it)
		self.lock = threading.Lock()

	def __enter__(self):
		self.lock.acquire()
		return self

	def __exit__(self, exc_type, exc_value, traceback):
		self.lock.release()

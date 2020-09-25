from __future__ import absolute_import, division, print_function, unicode_literals


class SplitRecursive(object):

	"""Fast non-prime-based factorial algorithm.
		Python port of: http://www.luschny.de/math/factorial/java/FactorialSplit.java.html
	"""

	def factorial(self, n):
		# type: (int, ) -> int

		if n < 0:
			raise ArithmeticError("Factorial: n has to be >= 0, but was " + n)

		if n < 2:
			return 1

		p = 1
		r = 1
		self.N = 1

		log2n = n.bit_length() - 1 # should be the same as: int(floor(log(n, 2)))
		h = 0
		shift = 0
		high = 1

		while h != n:
			shift += h
			h = n >> log2n
			log2n -= 1
			length = high
			if (h & 1) == 1:
				high = h
			else:
				high = h - 1
			length = (high - length) >> 1

			if length > 0:
				p *= self.product(length)
				r *= p
		return r << shift

	def product(self, n):
		m = n >> 1
		if m == 0:
			self.N += 2
			return self.N
		if n == 2:
			self.N += 2
			ret = self.N * (self.N + 2)
			self.N += 2
			return ret
		return self.product(n - m) * self.product(m)

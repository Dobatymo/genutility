from twisted.internet import protocol


class GenericFactory(protocol.Factory):
	def __init__(self, protocol, *args, **kwargs):
		self.protocol = protocol
		self.args = args
		self.kwargs = kwargs

	def buildProtocol(self, addr):
		return self.protocol(self, *self.args, **self.kwargs)  # deleted "self, " here...

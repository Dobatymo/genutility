import requests

class RasaRestWebhook(object):

	def __init__(self, sender, scheme="http", netloc="localhost:5005", timeout=60):
		# type: (str, str, str, int) -> None

		self.sender = sender
		self.scheme = scheme
		self.netloc = netloc
		self.timeout = timeout

	def get_endpoint(self, path):
		return self.scheme + "://" + self.netloc + path

	def health(self):
		# type: () -> dict

		url = self.get_endpoint("/webhooks/rest/")

		r = requests.get(url, timeout=self.timeout)
		r.raise_for_status()
		return r.json()

	def send_message(self, message):
		# type: (str, ) -> dict

		url = self.get_endpoint("/webhooks/rest/webhook")

		r = requests.post(url, json={
			"sender": self.sender,
			"message": message,
		}, timeout=self.timeout)
		r.raise_for_status()
		return r.json()

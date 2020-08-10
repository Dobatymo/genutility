import requests

class RasaRestWebhook(object):

	scheme = "http"

	def __init__(self, sender, netloc="localhost:5005", timeout=60):
		# type: (str, str, int) -> None

		self.sender = sender
		self.netloc = netloc
		self.timeout = timeout

	def health(self):
		# type: () -> dict

		url = self.scheme + "://" + self.netloc + "/webhooks/rest/"

		r = requests.get(url, timeout=self.timeout)
		r.raise_for_status()
		return r.json()

	def send_message(self, message):
		# type: (str, ) -> dict

		url = self.scheme + "://" + self.netloc + "/webhooks/rest/webhook"

		r = requests.post(url, json={
			"sender": self.sender,
			"message": message,
		}, timeout=self.timeout)
		r.raise_for_status()
		return r.json()

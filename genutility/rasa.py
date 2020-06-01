import requests

class RasaRestWebhook(object):

	scheme = "http"
	path = "/webhooks/rest/webhook"

	def __init__(self, sender, netloc="localhost:5005", timeout=60):
		# type: (str, str, int) -> None

		self.sender = sender
		self.netloc = netloc
		self.timeout = timeout

	def send_message(self, message):
		# type: (str, ) -> dict

		url = self.scheme + "://" + self.netloc + self.path
		r = requests.post(url, json={
			"sender": self.sender,
			"message": message,
		}, timeout=self.timeout)
		r.raise_for_status()
		return r.json()


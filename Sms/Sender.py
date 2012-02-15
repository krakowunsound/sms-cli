from logging import debug, error
from Config import Config
from Exceptions import *

class SmsSender(object):
	def __init__(self, recipients = [], engine_options = {}, **kwargs):
		debug("Importing engine: %s" % Config().engine)
		driver_module = __import__("Sms." + Config().engine, fromlist = ["Sms"])
		self._driver = driver_module.SmsDriver(options = Config().engine_options(), **kwargs)
		self._recipients = recipients
		self._message = ""

	def addRecipient(self, recipient):
		self._recipients.append(recipient)

	def clearRecipients(self):
		self._recipients = recipients

	def addMessage(self, message):
		if self._message:
			self._message += "\n"
		self._message += message

	def clearMessage(self):
		self._message = ""

	def send(self, message = None, recipients = []):
		if not message:
			message = self._message
			self.clearMessage()
		if not recipients:
			recipients = self._recipients

		assert(message and recipients)

		try:
			try:
				self._driver.sendMulti(message, recipients)
			except AttributeError:
				for recipient in recipients:
					self._driver.send(message, recipient)
		except SmsError, e:
			error(str(e))
			return False

		return True


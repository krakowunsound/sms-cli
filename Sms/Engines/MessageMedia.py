## Michal Ludvig <mludvig@logix.net.nz>
## http://www.logix.cz/michal/devel/sms-cli
## License: GPL Version 2

from Sms.Logger import *
from Sms.Exceptions import SmsError
from Sms.SimpleObjects import *
import GenericSoap

import random
from suds.client import Client

class SmsDriver(GenericSoap.SmsDriver):
    url = 'http://soap.m4u.com.au/?wsdl'

    def __init__(self, options = {}):
        GenericSoap.SmsDriver.__init__(self, options)

        # Soap Client
        self.client = Client(self.url, cache = self.cache)

        # Authentication
        self.auth = self.client.factory.create('AuthenticationType')
        self.auth.userId = self.options['username']
        self.auth.password = self.options['password']

    def send(self, message):
        debug("MessageMedia.send([%s])" % ", ".join(message.recipients))

        # Message Type
        message_t = self.client.factory.create("MessageType")
        message_t.content = message.message
        message_t.deliveryReport = True
        for recipient in message.recipients:
            message_t.recipients.recipient.append(self.client.factory.create("RecipientType"))
            message_t.recipients.recipient[-1].value = recipient
            message_t.recipients.recipient[-1]._uid = random.randint(100000000, 999999999)

        # Container for multiple messages
        send_messages_t = self.client.factory.create("SendMessagesBodyType")
        send_messages_t.messages.message.append(message_t)

        # Send it out
        ret = self.client.service.sendMessages(self.auth, send_messages_t)

        error_recipients = []

        mids = []
        if 'errors' in dir(ret):
                for error in ret.errors.error:
                    for recipient in error.recipients.recipient:
                        debug("SMS(MessageMedia) failed to %s: %s" % (recipient.value, error._code))
                        error_recipients.append(recipient.value)
                        mids.append(SmsSendStatus(message.message, recipient = recipient.value, despatched = False, comment = error._code))

        for recipient in message_t.recipients.recipient:
            if recipient.value not in error_recipients:
                debug("SMS(MessageMedia) sent to %s with ID: %s" % (recipient.value, recipient._uid))
                mids.append(SmsSendStatus(message.message, recipient = recipient.value, despatched = True, mid = recipient._uid))
        return mids

    def receive(self, senders = [], in_reply_to = [], keep = False):
        replies_raw = []

        check_replies_t = self.client.service.checkReplies(self.auth)
        if not check_replies_t.replies:
            return []

        # Fetch new messages
        if senders == [] and in_reply_to == []:
            replies_raw = check_replies_t.replies.reply
        else:
            for reply_t in check_replies_t.replies.reply:
                debug("SMS(MessageMedia) received sender=%s, uid=%s: %s" % (reply_t.origin, reply_t._uid, reply_t.content))
                if str(reply_t._uid) in in_reply_to or reply_t.origin in senders:
                    replies_raw.append(reply_t)

        # Delete messages from the gateway
        if replies_raw and not keep:
            confirm_replies_t = self.client.factory.create("ConfirmRepliesBodyType")
            for reply_t in replies_raw:
                confirm_replies_t.replies.reply.append(self.client.factory.create("ConfirmItemType"))
                confirm_replies_t.replies.reply[-1]._receiptId = str(reply_t._receiptId)
                debug("SMS(MessageMedia) deleting sender=%s, uid=%s: %s" % (reply_t.origin, reply_t._uid, reply_t.content))
            ret = self.client.service.confirmReplies(self.auth, confirm_replies_t)
            debug("SMS(MessageMedia) deleted %d messages" % ret._confirmed)

        replies = []
        for reply_t in replies_raw:
            replies.append(SmsMessage(message = reply_t.content, sender = reply_t.origin, mid = reply_t._uid, timestamp = reply_t.received))
        return replies

# vim:et:sw=4:sts=4:ai:sta

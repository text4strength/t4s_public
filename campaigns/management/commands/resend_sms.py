from django.core.management.base import BaseCommand
from django.conf import settings
from django.utils import timezone

from accounts.utils import is_good_time_to_send_messages, get_twilio_info
from smsmessages.models import MessageRecord
from smsmessages.constants import RETRY, GIVEUP, SUCCESS

from twilio import TwilioRestException

class Command(BaseCommand):

    def handle(self, *args, **options):
        if is_good_time_to_send_messages():
            records = MessageRecord.objects.filter(status=RETRY)
        else:
            records = []

        for record in records:
            try:
                twilio = record.task_queue.twilio
                client, from_num = get_twilio_info(twilio)

                #TODO (Future): Should we check if individual account holder is under conversation_limit_per_day?
                twilio_reply = client.messages.create(body=record.content, to=record.receiver_num, from_=from_num)
                record.twilio_msg_sid= twilio_reply.sid
                record.status = SUCCESS
                record.sent_at = timezone.localtime(timezone.now())
            except TwilioRestException, e:
                # log in MessageRecord here
                record.failed_times =  record.failed_times + 1
                
                if record.failed_times > settings.RETRY_LIMIT:
                    record.status = GIVEUP
                    #TODO: send notification to researcher here?

            record.save()


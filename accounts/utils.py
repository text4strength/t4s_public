import random
import re

from twilio.rest import TwilioRestClient
from twilio import TwilioRestException

from django.core.cache import cache
from django.conf import settings
from django.utils import timezone

# NOTE: The problem with having a universal (i.e. not tied to the individual TaskQ objects)
# time limit is that researcher can change his/her mind later and some of the old messages
# that are pedning will be sent according to the new time limit once user profile settings are
# updated. For now, we'll just use universal time limit because there are only a couple of
# researchers who are using this system, so we don't have to introduce unnecessary complicated
# logic in the code to store time limit in individual TaskQ objects


def is_good_time_to_send_messages():
    # to prevent circular import, we load it here
    from accounts.models import TimeLimit

    now = timezone.localtime(timezone.now())
    time_limit_obj = TimeLimit.objects.latest('id')
    after = time_limit_obj.after
    before = time_limit_obj.before

    return after <= now.time() <= before

def get_twilio_info(twilio_obj=None):
    try:
        client = TwilioRestClient(twilio_obj.sid, twilio_obj.token)
        from_num = twilio_obj.number
    except Exception, e: # expected error is AttributeError if twilio_obj is None
        client = TwilioRestClient(settings.T4S_TWILIO_SID, settings.T4S_TWILIO_TOKEN)
        from_num = settings.T4S_TWILIO_NUMBER

    return (client, from_num)

def send_verification_code(to_num):
    client = TwilioRestClient(settings.T4S_TWILIO_SID, settings.T4S_TWILIO_TOKEN)
    rand_num = random.randrange(10000, 99999)
    msg_content = "This is your verfication code for Text4Strength: " + str(rand_num)
    msg_content += ". It will expire in five minutes, so please go ahead and complete the registration." 

    cache.set(to_num, rand_num, 300)

    try:
        client.sms.messages.create(body=msg_content, to=to_num, from_=settings.T4S_TWILIO_NUMBER)
    except TwilioRestException:
        return False
    return True

def get_user_role(user):
    person = None
    for role in ['student', 'advisor', 'researcher']:
        try:
            person = getattr(user, role)
            break
        except:
            pass
    return person

def format_to_phone_num(num_str):
    # Insert commas in thousandth places for every digit EXCEPT the last one, then
    # replace commas with dashes and then finally, add the last digit that was
    # excluded back
    phone_num_len = len(num_str)
    if (phone_num_len == 10):
        pattern=re.compile(r'^\D*(\d{3})\D*(\d{3})\D*(\d{4})\D*$')        
        formatted_num = '-'.join(pattern.search(num_str).groups())
    elif ((phone_num_len > 10) and (phone_num_len <= 13)):
        pattern=re.compile(r'^\D*(\d{1,3})\D*(\d{3})\D*(\d{3})\D*(\d{4})\D*$')
        formatted_num = '-'.join(pattern.search(num_str).groups())
    elif ((phone_num_len > 13) and (phone_num_len <= 15)):
        pattern=re.compile(r'^\D*(\d{1,2})\D*(\d{3})\D*(\d{3})\D*(\d{3})\D*(\d{4})\D*$')
        formatted_num = '-'.join(pattern.search(num_str).groups())
    else:   # Probably raise error; Not sure
        formatted_num = num_str

    return formatted_num
    
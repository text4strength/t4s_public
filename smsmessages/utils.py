'''
Created on Feb 14, 2014

@author: lacheephyo
'''
# Solution: we have to exclude all parents ids from the search
from accounts.models import Advisor, Student
from smsmessages.models import MessageRecord
from twilio import TwilioRestException
from smsmessages.constants import RETRY

# Function below is used in messages/views.py
# to prevent us from creating circular message sequence
def get_parent_ids(msg):
    ids = [msg.id]
    options = msg.child_msg_options.all()
    if options:
        for option in options:
            ids.extend(get_parent_ids(option.parent_msg))
    return ids

def send_sms(client, msg_content, to_num, from_num, campaign=None, task_queue=None, root_msg=None, record_msg=True):
    # TODO: we need to add 'sender' and 'receiver' in the future after we create Twilio user with fixtures
    # Note: we left out 'prompting_msg' because this is the sender portion; So it can be NULL as default
    record = MessageRecord(content=msg_content, message=root_msg, sender_num=from_num,
                           receiver_num=to_num, campaign=campaign, task_queue=task_queue)
    
    # TODO: This needs to be removed eventually because I'm only preliminarily testing whether
    # we can send SMS to both US and China from our system. 
    if ((len(to_num) > 10) and (to_num[:1] != "+")):
        to_num = "+" + to_num

    try:
        twilio_reply = client.messages.create(body=msg_content, to=to_num, from_=from_num)
        if record_msg: # for notification messages, we don't want to record them because they're just noise
            record.twilio_msg_sid= twilio_reply.sid
            record.save()
    except Exception, e:
        if record_msg:
            # log in MessageRecord here
            record.status = RETRY
            record.failed_times = 1
            record.save()

        raise e # pass it up the chain so that we can do things like notifying the researcher

# NOTE: We do NOT record notification messages in DB message log
def send_sms_notification(client, notify_msg, to_groups, our_twilio_num, campaign=None, task_queue=None, root_msg=None):
    for gp in to_groups:
        advisors = list(Advisor.objects.filter(groups=gp))
        students = list(Student.objects.filter(groups=gp))

        for person in students+advisors:
            to_num = person.user.username
            send_sms(client, notify_msg, to_num, our_twilio_num, campaign=campaign,
                     task_queue=task_queue, root_msg=root_msg, record_msg=False)

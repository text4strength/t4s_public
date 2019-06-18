import traceback

from django.core.management.base import BaseCommand
from django.utils import timezone

from accounts.models import Student, Advisor, TimeLimit
from accounts.utils import is_good_time_to_send_messages, get_twilio_info
from campaigns.models import TaskQueue
from campaigns.constants import PENDING, SENT, SENDING, FAILED
from campaigns.utils import send_email_notification
from smsmessages.utils import send_sms

class Command(BaseCommand):

    def told_us_to_stop_sending_messages(self, person):
        return person.halt

    def conversation_limit_ok(self, person):
        return (person.conversation_limit_per_day > person.conversation_count_of_today)

    def handle(self, *args, **options):
        # Let's check this here so that we can a hit to DB
        if is_good_time_to_send_messages():
            # using now = datetime.now() will not include timezone info, so Django will warn us
            # https://docs.djangoproject.com/en/1.8/topics/i18n/timezones/#interpretation-of-naive-datetime-objects
            # Therefore, we're using the following timezone.localtime(....) instead from
            # Ref: https://docs.djangoproject.com/en/1.8/topics/i18n/timezones/#usage
            now = timezone.localtime(timezone.now())
            pending_tasks = TaskQueue.objects.filter(status=PENDING, launch_time__lt=now)
        else:
            pending_tasks = []

        for task in pending_tasks:
            try:
                root_msg = task.campaign.root_message
                msg_content =  root_msg.get_full_content()
                client, from_num = get_twilio_info(task.twilio)

                for group in task.groups.all():
                    advisors = list(Advisor.objects.filter(groups=group))
                    students = list(Student.objects.filter(groups=group))

                    for person in students+advisors:

                        if self.told_us_to_stop_sending_messages(person): # HALT
                            task.status = SENT
                            task.save()
                            continue

                        # check the sms limitation
                        if self.conversation_limit_ok(person):
                            to_num = person.user.username
                            send_sms(client, msg_content, to_num, from_num, campaign=task.campaign, task_queue=task, root_msg=root_msg)
                            person.conversation_count_of_today += 1
                            person.save()

                            # update task status
                            task.status = SENT
                            task.save()

            except Exception, e:
                task.status = FAILED
                task.save()
                launch_time = str(task.launch_time)
                groups = ', '.join("%s" % g for g in task.groups.all())
                campaign_title = task.campaign.title

                subject = "Failed to finish Task ID: " + str(task.id) + ", " + \
                            "Campaign Title:" + campaign_title
                msg_body = "Failed to finish Task ID: " + str(task.id) + "\n" + \
                            "Campaign Title:" + campaign_title + "\n" + \
                            "Groups Sent TO: " + groups  + "\n" + \
                            "Time Sent: " + launch_time  + "\n" + \
                            "To Number: " + to_num  + "\n" + \
                            "Twilio Error status: " + str(e.status) + "\n" + \
                            "Twilio Error Detail as below: "  + "\n" + \
                            str(e.msg) + "\n\n\n"

                msg_body += traceback.format_exc()
                send_email_notification(subject, msg_body)

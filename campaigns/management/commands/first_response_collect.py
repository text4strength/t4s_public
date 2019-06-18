from django.core.management.base import BaseCommand, CommandError

from django.contrib.auth.models import User
from accounts.models import Student, Advisor, Researcher, TwilioAccount, TimeLimit
from campaigns.models import Campaign, TaskQueue
from organizations.models import School, Group
from smsmessages.models import Message, MessageOption, MessageRecord
from wizard.models import Wizard

from campaigns.constants import PENDING, SENT, SENDING, FAILED
from accounts import utils

import csv

class Command(BaseCommand):

    # Usage: python manage.py collect "S. Cayuga Girls FT"
    # python manage.py first_response_collect "S. Cayuga Boys FT"
    # python manage.py first_response_collect "Dansville Field Test Girls"
    # python manage.py first_response_collect "Danville Field Test Boys"

    def handle(self, *args, **options):
        std_out = False
        result = ["School", "Group", "Phone"]
        for group_name in args:

            with open(group_name+'.csv', 'w') as csvfile:
                csvwiter = csv.writer(csvfile, delimiter=',', lineterminator='\n')

                if std_out: print(group_name + "\n====================")
                group_obj = Group.objects.filter(name=group_name).first()
                students = Student.objects.filter(groups=group_obj)
                tasks = TaskQueue.objects.filter(groups=group_obj.id, status='sent').order_by('launch_time')

                for t in tasks:
                    campaign_title = t.campaign.title
                    result.append(campaign_title)   # first row for headings

                csvwiter.writerow([unicode(s).encode("utf-8") for s in result]) # some lines are non-ASCII
                if std_out: print(result)
                if std_out: print("====================================================================================================")
                ## write to csv here

                for student in students:
                    school = student.school.name
                    group = group_name
                    phone_num = student.user.username
                    phone_num_str = utils.format_to_phone_num(phone_num)

                    result = [school, group, phone_num_str]
                    for t in tasks:
                        records = MessageRecord.objects.filter(task_queue=t, message__isnull=True, sender_num=phone_num)
                        if not records: # empty list
                            result.append('')
                        else:
                            for record in records: # scan through the conversations received
                                student_response = record.content
                                prompt_msg_str = record.prompting_msg.content
                                root_msg_str = record.campaign.root_message.content
                                campaign_title = record.campaign.title
                                user_obj = User.objects.filter(username=record.sender_num).first()

                                if root_msg_str[0:150] == prompt_msg_str[0:150]:
                                    result.append(student_response)
                                    break # we found it, move on to other tasks

                    csvwiter.writerow(result)
                    if std_out: print(result)

        if std_out: print("*****")

# Student.objects.filter(groups=Group.objects.filter(name="Phyo").first()).first().user.id
# TaskQueue.objects.filter(groups=11).first().campaign
# MessageRecord.objects.filter(task_queue=tq1, message__isnull=True)
# tq1=TaskQueue.objects.filter(id=124).first()


# find groups
# groups = Group.objects.filter(name__startswith="Phyo") # or (name="Phyo")
# group_ids = [g.id for g in groups]

# for g in group_ids:
# # collect the conversations that were ALREADY sent to this group
# tasks = TaskQueue.objects.filter(groups=g, status='sent').order_by('launch_time')

# for t in tasks:
# records = MessageRecord.objects.filter(task_queue=t, message__isnull=True)
#   for r in records:
#       student_response = r.content
#       prompting_msg_str = r.prompting_msg.content
#       root_msg_str = r.campaign.root_message.content
#       campaign_title = r.campaign.title
#       user_obj = User.objects.filter(username=r.sender_num).first()
#       if user_obj:
#           student_obj = Student.objects.filter(user=user_obj).first()
#           if student_obj:
#               school = student_obj.school.name
#               student_groups = Student.objects.filter(user=student_obj).first().groups.all()

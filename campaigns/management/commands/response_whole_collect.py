from django.core.management.base import BaseCommand

from django.contrib.auth.models import User
from django.db.models import Q
from accounts.models import Student
from organizations.models import School, Group
from smsmessages.models import Message, MessageOption, MessageRecord

from accounts import utils

import csv

class Command(BaseCommand):

    # Usage: python manage.py collect "S. Cayuga Girls FT"
    # python manage.py response_whole_collect "S. Cayuga Boys FT"
    # python manage.py response_whole_collect "Dansville Field Test Girls"
    # python manage.py response_whole_collect "Danville Field Test Boys"

    """
        def get_context_data(self, **kwargs):
        data = super(UserConversationView, self).get_context_data(**kwargs)
        phone_num = self.request.GET['username']
        if 'taskq_id' in self.request.GET:
            taskq_id = self.request.GET['taskq_id']
            # data['taskq_id'] = taskq_id # let's pass this on for use in "Chat with Participant directly" feature
            taskq_obj = TaskQueue.objects.get(id=taskq_id)
            # messages replied/sent by student tied to a particular taskQ
            records = MessageRecord.objects.filter(task_queue=taskq_obj).filter(Q(receiver_num=phone_num)|Q(sender_num=phone_num))
        else:
            records = MessageRecord.objects.filter(Q(receiver_num=phone_num)|Q(sender_num=phone_num))  # all messages sent/received by student

        data['records'] = records
        data['phone_number'] = phone_num
        return data
    """
    def handle(self, *args, **options):
        std_out = True#False
        result = ["Group Name", "From", "To", "Time Sent or Received", "Message Content", "Conversation Title"]
        for group_name in args:

            with open(group_name+'.csv', 'w') as csvfile:
                csvwiter = csv.writer(csvfile, delimiter=',', lineterminator='\n')

                if std_out: print(group_name + "\n====================")
                group_obj = Group.objects.filter(name=group_name).first()
                students = Student.objects.filter(groups=group_obj)

                csvwiter.writerow([unicode(s).encode("utf-8") for s in result]) # some lines are non-ASCII
                if std_out: print(result)
                if std_out: print("====================================================================================================")

                for student in students:
                    #school = student.school.name
                    group = group_name
                    phone_num = student.user.username
                    records = MessageRecord.objects.filter(Q(receiver_num=phone_num)|Q(sender_num=phone_num))  # all messages sent/received by student

                    if not records: # empty list
                        result.append('')
                    else:
                        for record in records:
                            result = [group]
                            sender = utils.format_to_phone_num(record.sender_num)
                            receiver = utils.format_to_phone_num(record.receiver_num)
                            msg_content = "Message Failed To Be Sent" if record.status == "give up" else unicode(record.content).encode("utf-8")

                            try:
                                campaign_title = unicode(record.campaign.title).encode("utf-8")
                            except:
                                campaign_title = "N/A"

                            result.extend([sender, receiver, record.created_at, msg_content, campaign_title])

                            csvwiter.writerow(result)
                            if std_out: print(result)

                    csvwiter.writerow([]) # write an empty row between each student
                    if std_out: print("*****\n\n")

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

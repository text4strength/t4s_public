from django.db import models
from django.contrib.auth.models import User

from accounts.constants import PEERLEADER, STUDENTMEMBER
from accounts.utils import format_to_phone_num
from organizations.models import School

from datetime import time

# goal: classify User as "students", "researcher", "teacher/advisor" or "leader"
# student, researcher, advisors, leaders
class Student(models.Model):
    ROLE_CHOICES = (
        (PEERLEADER, 'Group/Peer Leader'),
        (STUDENTMEMBER, 'Group Member'),
    )
    
    user = models.OneToOneField(User)
    halt = models.BooleanField(default=False) # if we should text him/her
    groups = models.ManyToManyField('organizations.Group')
    school = models.ForeignKey(School)
    role = models.CharField(max_length=30, choices=ROLE_CHOICES, default=STUDENTMEMBER)
    conversation_limit_per_day = models.IntegerField(default=100)
    conversation_count_of_today = models.IntegerField(default=0)

    def get_formatted_phone_number(self):
        return format_to_phone_num(self.user.username)


class Advisor(models.Model):
    user = models.OneToOneField(User)
    halt = models.BooleanField(default=False) # if we should text him/her
    groups = models.ManyToManyField('organizations.Group')
    school = models.ForeignKey(School)
    conversation_limit_per_day = models.IntegerField(default=100)
    conversation_count_of_today = models.IntegerField(default=0)

    def get_formatted_phone_number(self):
        return format_to_phone_num(self.user.username)

class Researcher(models.Model):
    user = models.OneToOneField(User)
    halt = models.BooleanField(default=False) # if we should text him/her
    phone = models.CharField(max_length=16, blank=True)
    conversation_limit_per_day = models.IntegerField(default=100000)
    conversation_count_of_today = models.IntegerField(default=0)

    def get_formatted_phone_number(self):
        return format_to_phone_num(self.user.username)

class TwilioAccount(models.Model):
    name = models.CharField(max_length=50, blank=True)
    number = models.CharField(max_length=16, blank=True)
    sid = models.CharField(max_length=100, blank=True)
    token = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def get_formatted_phone_number(self):
        return format_to_phone_num(self.number)

class TimeLimit(models.Model):
    after = models.TimeField(blank=True, default=time(16, 0)) # 4PM
    before = models.TimeField(blank=True, default=time(23, 0)) # 11PM

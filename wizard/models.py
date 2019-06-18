from django.db import models
from django.contrib.auth.models import User

from campaigns.models import Campaign
from smsmessages.models import Message


class Wizard(models.Model):
    """
    Save direct chat conversations with the students
    """
    campaign = models.ForeignKey(Campaign)
    message = models.ForeignKey(Message)
    recipient = models.ForeignKey(User) # student who is queued in wizard chat
    status = models.BooleanField(default=False) # 'false' is case open; 'true' is closed
    notify = models.BooleanField(default=True) # notify research EVERYTIME the student sends us a chat
    deleted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)


from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

from smsmessages.constants import SUCCESS, GIVEUP, RETRY
from accounts.utils import format_to_phone_num


class Message(models.Model):
    # Note: when we save MessageRecord, we have both content and message. Their length SHOULD be synced.
    # Read more about them there.
    # create new field called campaign here? Is that manytomany or onetomany (foreignkey very likely)
    campaign = models.ForeignKey('campaigns.Campaign', null=True, blank=True) # 'campaigns.Campaign' is used to avoid circular reference with Campaign
    content = models.TextField(db_index=True, max_length=500)
    composer = models.ForeignKey(User, related_name='composed_message')
    created_at = models.DateTimeField(auto_now_add=True)
    groups = models.ManyToManyField('organizations.Group') # groups to send notification message to
    #is_connected = models.BooleanField(default=False)

    def __unicode__(self):
        return self.content

    def get_full_content(self):
        options = self.options.all()
        full_content = self.content

        for option in options:
            # Sometimes, sender choose not include option-related texts in the main message that is sent
            # e.g., How are you feeling from a scale of 1-10?
            if not option.exclude_in_msg:
                if option.trigger_keyword == '*':
                    # CAUTION: Do NOT remove the space BEFORE trigger keyword below
                    full_content += ' %s%s'%(option.separator, option.option_content)
                else:
                    # CAUTION: Do NOT remove the space BEFORE trigger keyword below
                    full_content += ' %s%s%s'%(option.trigger_keyword, option.separator, option.option_content)
                
        return full_content

    def get_all_group_names(self):
        groups = self.groups.all()

        group_name = ''
        for group in groups:
            group_name += group.name + ', '

        return group_name

class MessageOption(models.Model):
    """
    """
    '''
    Note: kapor explained the diff between two calls below (why we named 'options' and 'child_msg_options'
    >>> msg.options.all() # equals: MesssageOption.objects.filter(parent_msg=msg)
    >>> msg.child_message.all() # equals: MesssageOption.objects.filter(child_msg=msg)
    '''
    parent_msg = models.ForeignKey(Message, related_name='options')
    child_msg = models.ForeignKey(Message, related_name='child_msg_options')
    #"Hi, here are the options 1) assdsa 2) asds" # 1 and 2 are trigger, 'assdsa' and 'asds' are option
    #"Thank you" # this is child_msg
    trigger_keyword = models.CharField(max_length=160)
    separator = models.CharField(max_length=10, default='')
    option_content = models.CharField(max_length=160)
    exclude_in_msg = models.BooleanField(default=False)
    notify = models.BooleanField(default=False)
    wizard = models.BooleanField(default=False)
    #def __unicode__(self):
    #    return self.content

class MessageRecord(models.Model):
    STATUS_CHOICES = (
        (SUCCESS, 'success'),
        (RETRY, 'retry'),
        (GIVEUP, 'give up'),
    )
    
    # 'content' and 'message' are separated because sometimes students may responds to things that we don't have Message object for;
    # Also, 'message' is used for finding the last sent message when we receive something from student; 'content' is pure text from them or us
    # 'prompting_msge' will only exists for entries where we record student's reponses
    content = models.TextField(max_length=500)
    message = models.ForeignKey(Message, null=True, blank=True) # This is the mesasge we send to students; for response records from students, this will be NULL
    sender_num = models.CharField(max_length=16)
    receiver_num = models.CharField(max_length=16)
    sent_at = models.DateTimeField(default=timezone.localtime(timezone.now()))#datetime.now) #TODO: I don't think we need sent_at anymore. Remove it later
    prompting_msg = models.ForeignKey(Message, related_name='prompting_msg', null=True, blank=True) # This is the prompting message that the student is replying to; Can be NULL

    campaign = models.ForeignKey('campaigns.Campaign', null=True, blank=True) # 'campaigns.Campaign' is because if we use just "Campaign", in campaigns/models.py we import Message and here, we import Campaign, so it's circular  
    task_queue = models.ForeignKey('campaigns.TaskQueue', null=True, blank=True)
    sender = models.ForeignKey(User, related_name='sender', null=True, blank=True)
    receiver = models.ForeignKey(User, related_name='receiver', null=True, blank=True) 
    is_wizard = models.BooleanField(default=False)

    # following vars are the ones developer cares about
    created_at = models.DateTimeField(auto_now_add=True)
    twilio_msg_sid = models.CharField(max_length=100, blank=True, null=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='success')
    failed_times = models.IntegerField(default=0)

    def get_formatted_sender_number(self):
        return format_to_phone_num(self.sender_num)

    def get_formatted_receiver_number(self):
        return format_to_phone_num(self.receiver_num)

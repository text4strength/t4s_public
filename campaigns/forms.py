'''
Created on Feb 12, 2014

@author: lacheephyo
'''
import json
from datetime import datetime

from django import forms
from accounts.models import TimeLimit
from campaigns.models import Campaign

class SingleMessageConveresationCreateForm(forms.ModelForm):
    err_msgs = {'required': "You must type in the content of the message.", 
               'max_length': "The message length should be no longer than the limit below."}
    parent_msg = forms.CharField(max_length=160, error_messages=err_msgs)
    reply_msg = forms.CharField(max_length=160, error_messages=err_msgs)

    class Meta:
        model = Campaign
        fields = ('title',)
        error_messages = {
            'title': {
                'required': "The title of the conversation is required.",
            }
        }


class MultipleMessageConversationCreateForm(forms.ModelForm):
    cur_msg = forms.CharField(max_length=160)
    options = forms.CharField() # these two vars should be the same name as AJAX dict keys
    selected_group_names = forms.CharField()
    selected_group_ids = forms.CharField()

    class Meta:
        model = Campaign
        fields = ('title',)

    def clean_options(self):
        data = self.data
        options = json.loads(data['options'])
        return options  # this will go to form_valid of CampaignCreateConversationView


class ConversationTitleEditForm(forms.ModelForm):
    class Meta:
        model = Campaign
        fields = ('title',)
        widgets = {
                'title': forms.TextInput(attrs={'size':'156'}),
        }


class ConversationSendForm(forms.Form):
    datetime_err_msgs = {'required': "You must select a time to send this conversation."}
    group_err_msgs = {'required': "You must select at least one group to send this conversation."}
    twilio_err_msgs = {'required': "You must select a phone number to send this message."}
    
    launch_datetime = forms.CharField(required=True, error_messages=datetime_err_msgs)
    selected_group_ids = forms.CharField(required=True, error_messages=group_err_msgs, widget=forms.HiddenInput)
    twilio_id = forms.CharField(required=True, error_messages=twilio_err_msgs)

    def clean_launch_datetime(self):
        data = self.data
        launch_datetime = data.get('launch_datetime') # this is a string
        launch_time_obj = datetime.strptime(launch_datetime, '%Y-%m-%d %H:%M:%S')
        launch_time = launch_time_obj.time().replace(second=0) # only strip out H:M part for comparison

        time_limit = TimeLimit.objects.latest('id') # just use the latest entry in the DB to be safe
        before = time_limit.before
        after = time_limit.after

        before_str = before.strftime('%H:%M')
        after_str = after.strftime('%H:%M')

        if (not (after <= launch_time <= before )):
            raise forms.ValidationError("Sorry. We can only send messages between " + after_str + " and " + before_str + " hours." +
                   "Please update the Time Limit Settings under User Profile Settings if you'd like it to be different.")

        return launch_datetime

class CampaignConversationForm(forms.Form):
    options = forms.CharField() # these two vars should be the same name as AJAX dict keys
    parent_msg_content = forms.CharField(required=False)    # Once we've created it, we don't require it to exist

    def clean_options(self):
        data = self.data
        options = json.loads(data['options'])
        return options  # this will go to form_valid of CampaignCreateConversationView


class ConversationDuplicateForm(forms.ModelForm):
    class Meta:
        model = Campaign
        fields = ('title',)
        widgets = {
                'title': forms.TextInput(attrs={'size':'156'}),
        }

    def __init__(self, campaign, *args, **kwargs):      # this is to get 'campaign' object from CampaignDuplicateView via get_form() 
        super(ConversationDuplicateForm, self).__init__(*args, **kwargs)
        self.fields['title'].initial = 'Copy of ' + campaign.title # to set default for title 


class LinkMessagesForm(forms.Form):
    data_str =  forms.CharField()   #whatever the key name passed from ajax call

    def clean_data_str(self):
        data = self.data
        options = json.loads(data['data_str'])
        return options  # this will go to form_valid of WizardChatView



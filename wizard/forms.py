import json

from django import forms

class WizardMessageSendForm(forms.Form):
    data_str =  forms.CharField()   #whatever the key name passed from ajax call

    def clean_data_str(self):
        data = self.data
        options = json.loads(data['data_str'])
        return options  # this will go to form_valid of WizardChatView



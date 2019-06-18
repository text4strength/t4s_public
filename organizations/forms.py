from django import forms

from accounts.models import Student
from organizations.models import Group, School
from organizations.mixins import PhoneNumberFormMixin

import re

class SchoolCreateForm(forms.ModelForm):
    class Meta:
        model = School
        fields = ('name',)
        widgets = {
                'name': forms.TextInput(attrs={'size':'156'}),
        }

class StudentCreateForm(forms.ModelForm):
    phone_numbers = forms.CharField(widget=forms.Textarea)
    class Meta:
        model = Student
        exclude = ('user',)

        # if we want Django to check the phone number to make sure whether they contain alphabets
        #def clean_phone_numbers(self):

class GroupCreateForm(forms.ModelForm):
    name = forms.CharField(required=True, label='Group Name', widget=forms.TextInput(attrs={'size':'58'}))
    phone_numbers = forms.CharField(required=False, widget=forms.HiddenInput)
    class Meta:
        model = Group
        fields = ('name',)

class GroupNameEditForm(forms.ModelForm):
    class Meta:
        model = Group
        fields = ('name',)
        widgets = {
                'name': forms.TextInput(attrs={'size':'156'}),
        }

class GroupMembershipEditForm(forms.Form):
    phone_numbers = forms.CharField(required=False, widget=forms.HiddenInput)
    #school = forms.CharField(widget=forms.Select)

    """
    def __init__(self, *args, **kwargs):
        super(GroupMembershipEditForm, self).__init__(*args, **kwargs)
        schools = School.objects.all()
        choices = [(s.id, s.name) for s in schools]
        self.fields['school'].widget.choices = [['', '------'],] + choices
    """

class ContactEditForm(forms.ModelForm):
    class Meta:
        model = School
        fields = ('contacts', 'help_reply',)
        placeholder_txt = "Type your customized reply for HELPINFO here."
        widgets = {
                'contacts': forms.Textarea(attrs={'cols': 160, 'rows': 3}),
                'help_reply': forms.Textarea(attrs={'cols': 160, 'rows': 3, 'placeholder': placeholder_txt}),
        }
        labels = {
            'contacts': 'Emergency contact number(s) at this organization:',
            'help_reply': 'Text we reply when student text HELPINFO:'
        }        
        error_messages = {
            'help_reply': {
                'max_length': "SMS messages are limited to 160 characters.",
            },
        }

    def clean_contacts(self):
        data = self.data
        numbers = []
        for num in data['contacts'].split(','):
            # TODO: refactor this into PhoneNumberFormMixin
            phone_re = re.compile(r'^\d{10,15}$')
            if not phone_re.match(num.strip()):
                raise forms.ValidationError("Phone number(s): " + num + " must be numeric and between 10-15 digits long.")
            numbers.append(num.strip())

        return ','.join(numbers)

class SchoolAddStudentForm(PhoneNumberFormMixin, forms.Form):
    form_attrs = {'cols': 160, 'rows': 3}
    phone_numbers = forms.CharField(widget=forms.Textarea(attrs=form_attrs))
    first_names = forms.CharField(required=False, widget=forms.Textarea(attrs=form_attrs))
    last_names = forms.CharField(required=False, widget=forms.Textarea(attrs=form_attrs))
    role = forms.CharField(widget=forms.Select)

    def __init__(self, *args, **kwargs):
        super(SchoolAddStudentForm, self).__init__(*args, **kwargs)
        self.fields['phone_numbers'].label = 'Step 1 (required): Add comma-separated list of phone numbers [E.g., 5856261234, 8613910912345]:'
        self.fields['first_names'].label = 'Step 2 (optional): Add comma-separated list of first names [E.g., Sophie, Sean, Maria]:'
        self.fields['last_names'].label = 'Step 3 (optional): Add comma-separated list of last names [E.g., Gunn, Smith, Moore]:'

        self.fields['role'].widget.choices = (('', '------'),) + Student.ROLE_CHOICES
        self.fields['role'].label = 'Step 4 (required): Select roles of these phone numbers (if irrelevant, choose "Group Leader"):'

    # # Note: If we have 'clean_phone_numbers' here and in PhoneNumberFormMixin, only the method below is entered
    # # As a result, I merge the checking of duplicates and phone number format into PhoneNumberMixin

class SchoolAddAdvisorForm(PhoneNumberFormMixin, forms.Form):
    form_attrs = {'cols': 160, 'rows': 3}
    phone_numbers = forms.CharField(widget=forms.Textarea(attrs=form_attrs))
    first_names = forms.CharField(required=False, widget=forms.Textarea(attrs=form_attrs))
    last_names = forms.CharField(required=False, widget=forms.Textarea(attrs=form_attrs))

    def __init__(self, *args, **kwargs):
        super(SchoolAddAdvisorForm, self).__init__(*args, **kwargs)
        self.fields['phone_numbers'].label = 'Step 1 (required): Add comma-separated list of phone numbers [E.g., 5856261234, 8613910912345]:'
        self.fields['first_names'].label = 'Step 2 (optional): Add comma-separated list of first names [E.g., Sophie, Sean, Maria]:'
        self.fields['last_names'].label = 'Step 3 (optional): Add comma-separated list of last names [E.g., Gunn, Smith, Moore]:'

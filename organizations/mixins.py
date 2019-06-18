'''
Created on Mar 14, 2014

@author: lacheephyo
'''
import re

from django.forms import forms


class PhoneNumberFormMixin(object):
    """
    Form mixin for checking phone nunbers.
    E.164 [Ref: http://en.wikipedia.org/wiki/E.164] limits telephone nums to
    15 digits including intl. prefix which can be up to 3 digits. 
    Assume intl. prefix is just 1 digit, then we have up to 14 digit to  
    support, but we'll let it be as much as 15 for the sake of it.
    """
    def clean_phone_numbers(self):
        data = self.data

        numbers = []

        # check if the phone number format is proper (10-15 digits and not empty)
        for num in data['phone_numbers'].split(','):
            phone_re = re.compile(r'^\d{10,15}$')
            if not phone_re.match(num.strip()):
                error_msg = "Phone number import error: " + num + " must be numeric and between 10-15 digits long " + \
                            "or must NOT be empty. Please make sure that there's NO TRAILING COMMA at the end of " + \
                            "your list [e.g., '1234567890,' will fool the system to think that you have an empty " + \
                            "phone number at the end of the list.]"
                raise forms.ValidationError(error_msg)

            numbers.append(num.strip())

        return ','.join(numbers)

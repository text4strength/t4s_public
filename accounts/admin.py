from django.contrib import admin
from accounts.models import Student, Advisor, Researcher, TwilioAccount, TimeLimit

admin.site.register(Student)
admin.site.register(Advisor)
admin.site.register(Researcher)
admin.site.register(TwilioAccount)
admin.site.register(TimeLimit)

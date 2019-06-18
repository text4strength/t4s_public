from django.conf.urls import patterns, url
from wizard.views import WizardListView, DeleteWizardView, SwitchWizardStatusView, WizardChatView, WizardChatRecordView, \
    SwitchWizardNotificationStatusView, RegularChatView


urlpatterns = patterns('',
    url(r'^list/$', WizardListView.as_view(), name='list_wizard'),
    url(r'^delete_wizard/$', DeleteWizardView.as_view(), name='delete_wizard'),
    url(r'^switch_status/$', SwitchWizardStatusView.as_view(), name='switch_status'),
    url(r'^switch_notify_status/$', SwitchWizardNotificationStatusView.as_view(), name='switch_notify_status'),
    url(r'^wizard_chat/$', WizardChatView.as_view(), name='wizard_chat'),
    url(r'^regular_chat/$', RegularChatView.as_view(), name='regular_chat'),
    url(r'^wizard_chat_records/$', WizardChatRecordView.as_view(), name='wizard_chat_records'),
)

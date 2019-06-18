from django.conf.urls import patterns, url

from accounts.views import LoginView, LogoutView, RegisterView,\
    VerficationCodeView, ChangePasswordView, UserProfileView,\
    UpdateConversationLimitView, UpdateTimeLimitView,\
    TwilioAccountListView, TwilioAccountCreateView, TwilioAccountDeleteView, TwilioAccountEditView

from django.views.generic.base import TemplateView

urlpatterns = patterns('',
    url(r'^login/$', LoginView.as_view(), name='login'),
    url(r'^logout/$', LogoutView.as_view(), name='logout'),

    url(r'^register/$', RegisterView.as_view(), name='register'),
    url(r'^send_verification_code/$', VerficationCodeView.as_view(), name='verify'),
    url(r'^confirm/$', TemplateView.as_view(template_name='accounts/confirm.html'), name='confirm'),

    url(r'^user_profile/$', UserProfileView.as_view(), name='user_profile'),
    url(r'^change_password/$', ChangePasswordView.as_view(), name='change_password'),
    url(r'^update_conversation_limit/$', UpdateConversationLimitView.as_view(), name='update_conversation_limit'),
    url(r'^update_time_limit/$', UpdateTimeLimitView.as_view(), name='update_time_limit'),

    url(r'^list_twilio_account/$', TwilioAccountListView.as_view(), name='list_twilio_account'),
    url(r'^create_twilio_account/$', TwilioAccountCreateView.as_view(), name='create_twilio_account'),
    url(r'^edit_twilio_account/(?P<pk>\d+)/$', TwilioAccountEditView.as_view(), name='edit_twilio_account'),
    url(r'^delete_twilio_account/(?P<pk>\d+)/$', TwilioAccountDeleteView.as_view(), name='delete_twilio_account'),
)

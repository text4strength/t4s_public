import json
from braces.views import LoginRequiredMixin, CsrfExemptMixin, JsonRequestResponseMixin, AjaxResponseMixin

from django.core.urlresolvers import reverse_lazy
from django.core import serializers
from django.contrib import messages
from django.db.models import Q
from django.http.response import HttpResponse
from django.views.generic.list import ListView
from django.views.generic.base import View, TemplateView, RedirectView
from django.views.generic.edit import CreateView, FormView, UpdateView
from django.contrib.auth.models import User

from accounts.utils import format_to_phone_num, get_twilio_info
from smsmessages.utils import send_sms
from campaigns.models import TaskQueue, Campaign
from smsmessages.models import MessageRecord
from wizard.models import Wizard
from wizard.forms import WizardMessageSendForm

from smsmessages.constants import SUCCESS

class WizardListView(LoginRequiredMixin, ListView):
    model = Wizard
    template_name = 'wizard/list.html'

    def get_context_data(self, **kwargs):
        data = super(WizardListView, self).get_context_data(**kwargs)
        data.update(self.request.GET.items())
        data['order_field'] = data.get('order_field', 'created_at')
        data['order_by'] = data.get('order_by', '-')
        return data

    def get_queryset(self):
        qs = super(WizardListView, self).get_queryset().exclude(deleted=True)

        order_field = self.request.GET.get('order_field')
        order_by = self.request.GET.get('order_by')

        if (order_field is None) or (order_by == '-'): # /wizard/list/ or list/?order_by=-
            qs = qs.order_by('-created_at') # show from most recent by default

        return qs # else, we return default, which is oldest first

class DeleteWizardView(LoginRequiredMixin, RedirectView):
    permanent = False

    def get_redirect_url(self, *args, **kwargs):
        wizard_obj = Wizard.objects.get(id=self.request.GET['wizard_id'])
        wizard_obj.deleted = True
        wizard_obj.status = True # close the case to be safe
        wizard_obj.save()
        return reverse_lazy('wizard:list_wizard') #+ '?page=' + self.request.GET.get('page', '1')

class SwitchWizardStatusView(LoginRequiredMixin, RedirectView):
    permanent = False

    def get_redirect_url(self, *args, **kwargs):
        wizard_obj = Wizard.objects.get(id=self.request.GET['wizard_id'])
        old_status = wizard_obj.status
        wizard_obj.status = (not old_status)
        wizard_obj.save()
        return reverse_lazy('wizard:list_wizard') #+ '?page=' + self.request.GET.get('page', '1')

class SwitchWizardNotificationStatusView(LoginRequiredMixin, RedirectView):
    permanent = False

    def get_redirect_url(self, *args, **kwargs):
        wizard_obj = Wizard.objects.get(id=self.request.GET['wizard_id'])
        old_notify = wizard_obj.notify
        wizard_obj.notify = (not old_notify)
        wizard_obj.save()
        return reverse_lazy('wizard:list_wizard')

class WizardChatRecordView(LoginRequiredMixin, JsonRequestResponseMixin, AjaxResponseMixin, View):

    def get_ajax(self, request, *args, **kwargs):
        wizard_obj = Wizard.objects.get(id=self.request.GET['wizard_id'])
        campaign_obj = wizard_obj.campaign
        raw_phone_num = wizard_obj.recipient.username
        records = MessageRecord.objects.filter(campaign=campaign_obj).filter(Q(receiver_num=raw_phone_num)|Q(sender_num=raw_phone_num))
        records = serializers.serialize('json', records)
        return self.render_json_response({'result': 'success', 'records': records})

class WizardChatView(CsrfExemptMixin, LoginRequiredMixin, FormView):
    template_name = 'wizard/wizard_chat.html'
    form_class = WizardMessageSendForm

    def get_success_url(self):
        return reverse_lazy('wizard:wizard_chat') + '?wizard_id=' + self.request.GET.get('wizard_id')

    def get_context_data(self, **kwargs):
        data = super(WizardChatView, self).get_context_data(**kwargs)
        wizard_obj = Wizard.objects.get(id=self.request.GET['wizard_id'])
        campaign_obj = wizard_obj.campaign
        raw_phone_num = wizard_obj.recipient.username
        phone_num = format_to_phone_num(raw_phone_num)

        if 'show_all_history' in self.request.GET:
            records = MessageRecord.objects.filter(Q(receiver_num=raw_phone_num)|Q(sender_num=raw_phone_num))
            data['show_all_history'] = 1
        else:
            records = MessageRecord.objects.filter(campaign=campaign_obj).filter(Q(receiver_num=raw_phone_num)|Q(sender_num=raw_phone_num))

        data['records'] = records
        data['phone_number'] = phone_num
        data['campaign_title'] = campaign_obj.title
        data['campaign_id'] = campaign_obj.id
        data['wizard_obj'] = wizard_obj
        return data

    def form_valid(self, form):
        data = form.cleaned_data

        if data['data_str'].get('msg'):
            msg_content = data['data_str']['msg']
        else: # if empty string
            messages.error(self.request, 'message content in data received is empty.')
            return HttpResponse(json.dumps({'result': 'failure in retrieving msg'}))

        if data['data_str'].get('campaign_id'):
            cam_id = data['data_str']['campaign_id']
            cam_obj = Campaign.objects.get(id=cam_id)
        else:
            messages.error(self.request, 'campaign id in data received is empty.')
            return HttpResponse(json.dumps({'result': 'failure in retrieving campaign id'}))

        if data['data_str'].get('to_num'):
            to_num = str(data['data_str']['to_num'])
        else:
            messages.error(self.request, 'to_num in data received is empty.')
            return HttpResponse(json.dumps({'result': 'failure in retrieving to_num'}))

        if data['data_str'].get('taskq_id'):
            taskq_id = data['data_str']['taskq_id']
            taskq_obj = TaskQueue.objects.get(id=taskq_id)
            root_msg = taskq_obj.campaign.root_message
            client, from_num = get_twilio_info(taskq_obj.twilio)

            send_sms(client, msg_content, to_num, from_num, campaign=cam_obj, task_queue=taskq_obj, root_msg=root_msg, record_msg=True)
            messages.success(self.request, 'Message (update or creation) was successful')
            return HttpResponse(json.dumps({'result': 'success'}))
        else:
            messages.error(self.request, 'taskq id in data received is empty.')
            return HttpResponse(json.dumps({'result': 'failure in retrieving taskq id'}))

class RegularChatView(LoginRequiredMixin, RedirectView):
    """
    For direct chat with the participant, retrieve an existing wizard case,
    if any, that is open for the most recent campaign OR create a new one
    and redirect to wizard chat for that most recent campaign.
    """
    permanent = False

    def get_redirect_url(self, *args, **kwargs):
        if 'username' in self.request.GET:
            phone_number = self.request.GET['username']
            # Step1: get last campaign we sent to her
            last_msg_record = MessageRecord.objects.filter(message__isnull=False,
                                                           campaign__isnull=False,
                                                           receiver_num=phone_number,
                                                           status=SUCCESS).order_by('created_at').last()

            last_campaign = last_msg_record.campaign
            last_msg = last_msg_record.message
            recipient_user = User.objects.get(username=phone_number)

            # Step2: see if that campaign and phone_number is registered in wizard AND is open
            wizard_list = Wizard.objects.filter(campaign=last_campaign, recipient=recipient_user)

            # Step3: if wizard case exists,
            if wizard_list:
                wizard = wizard_list.last()

                # Step3 a: and is closed, reopen
                if wizard.status:
                    wizard.status = False
                    wizard.deleted = False
                    wizard.save()

            # Step4: if wizard does not exist, create one and return the wizard_id and redirect
            # Of course, we don't need 'else', but having it makes intention of the code explicit
            else:
                wizard = Wizard(campaign=last_campaign, recipient=recipient_user, message=last_msg)
                wizard.save()

        # Step3 b: then redirect with the existing wizard_id
        return reverse_lazy('wizard:wizard_chat') + '?wizard_id=' + str(wizard.id) + '&show_all_history=1'

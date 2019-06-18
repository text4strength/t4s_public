import re

from django.core.urlresolvers import reverse_lazy
from django.contrib.auth.models import User
from django.db.models import Q
from django.http.response import HttpResponse
from django.views.generic.base import View, TemplateView
from django.views.generic.edit import CreateView, UpdateView, DeleteView
from django.views.generic.list import ListView

from campaigns.models import TaskQueue, Campaign
from campaigns.utils import send_email_notification
from smsmessages.models import Message, MessageOption, MessageRecord
from t4s.settings import T4S_TWILIO_SID, T4S_TWILIO_TOKEN
from wizard.models import Wizard
from smsmessages.forms import AddOptionForm, MessageUpdateForm
from smsmessages.constants import DONT_UNDERSTAND, THANKYOU, FREERESPONSE, RESUME_REPLY, HALT_REPLY, FIRST_TIMER_WELCOME
from accounts.utils import format_to_phone_num, get_user_role
from smsmessages.utils import get_parent_ids, send_sms, send_sms_notification

from twilio.rest import TwilioRestClient
from organizations.constants import CONTACT_TEXT
from braces.views import LoginRequiredMixin, AjaxResponseMixin,\
    JsonRequestResponseMixin

class MessageListView(LoginRequiredMixin, ListView):
    model = Message
    template_name = 'messages/list.html'
    
    # queryset is needed below because we only want to list the ones composed by the user
    def get_queryset(self):
        qs = super(MessageListView, self).get_queryset()
        return qs.filter(composer=self.request.user)

class MessageUpdateView(LoginRequiredMixin, UpdateView):
    model = Message
    form_class = MessageUpdateForm # check "forms.py" wher e we restrict what info we show
    template_name = 'messages/update.html'
    success_url = reverse_lazy('smsmessages:list')

class MessageDeleteView(LoginRequiredMixin, DeleteView):
    model = Message
    success_url = reverse_lazy('smsmessages:list')

    def get(self, request, *args, **kwargs):
        return self.delete(request, *args, **kwargs)

class AddOptionView(LoginRequiredMixin, CreateView):
    model = MessageOption
    template_name = 'messages/options/create.html'
    form_class = AddOptionForm

    def get_success_url(self):
        if 'cam_id' in self.request.GET:
            cam_id = self.request.GET['cam_id']
            return '%s?cam_id=%s'%(reverse_lazy('campaigns:message_list'), cam_id)
            #return '{}?cam_id={}'.format(reverse_lazy('campaigns:message_list'), cam_id)
        return reverse_lazy('smsmessages:list')
        

    # the method below is to pass down parent_msg to template
    def get_context_data(self, **kwargs):
        data = super(AddOptionView, self).get_context_data(**kwargs)
        msg = Message.objects.get(id=self.request.GET['msg_id'])
        data['parent_msg'] = msg
        return data


    def get_form(self, form_class):
        msg = Message.objects.get(id=self.request.GET['msg_id'])
        return form_class(msg, **self.get_form_kwargs())
        

    # we need below because we excluded parent_message in the form
    def form_valid(self, form):
        option = form.save(commit=False)
        msg = Message.objects.get(id=self.request.GET['msg_id'])
        option.parent_msg = msg
        option.save()
        return super(AddOptionView, self).form_valid(form)

class MessageSearchView(LoginRequiredMixin, JsonRequestResponseMixin, AjaxResponseMixin, View):
    def get_ajax(self, request, *args, **kwargs):
        keyword = request.GET.get('keyword')
        parent_msg_id = request.GET['msg_id']
        parent_msg = Message.objects.get(id=parent_msg_id)
        parent_ids = get_parent_ids(parent_msg)
        # https://docs.djangoproject.com/en/dev/ref/models/querysets/#values-list
        # can be short for:
        # child_ids = [option.child_msg.id for option in parent_msg.options.all()]
        child_ids = []
        for option in parent_msg.options.all():
            child_ids.append(option.child_msg.id)
        
        excluded_ids_list = parent_ids + child_ids 
        msgs = Message.objects.exclude(id__in=excluded_ids_list).filter(content__icontains=keyword)[:10]
        msgs_json = [{'id': m.id, 'content': m.content} for m in msgs]
        return self.render_json_response(msgs_json)

class MessageReceiveView(View):
    def get(self, request, *args, **kwargs):

        # Twilio's GET request for incoming SMS looks like this:
        # "GET /smsmessages/receive?AccountSid=AC14415ab0be51ba4da097dd51da5a7d8f
        # &MessageSid=SMacc66709b7ba53144cd632b6ee17c0f0&Body=Ahhhhh&ToZip=14603
        # &ToCity=ROCHESTER&FromState=NY&ToState=NY&SmsSid=SMacc66709b7ba53144cd632b6ee17c0f0
        # &To=%2B15853600116&ToCountry=US&FromCountry=US&SmsMessageSid=SMacc66709b7ba53144cd632b6ee17c0f0
        # &ApiVersion=2010-04-01&FromCity=&SmsStatus=received&NumMedia=0&From=%2B15856268095&FromZip= HTTP/1.1" 404 2862

        # TODO ***: Refactor this and figure out a neater way to separate between country code and core phone num 
        # IMPORTANT: must get rid of the '+1' too
        
        # TODO: This is a temporary solution; We need to decide on how to handle different country codes more elegantly
        if ((request.GET['From'][:2] == "+1") and (len(request.GET['From'][2:]) == 10)): # means US number
            caller_num = request.GET['From'][2:]        # "5856261222" from "+15856261222"
        else:
            caller_num = request.GET['From'][1:]        #  "8613910988979" from "+8613910988979" 

        our_twilio_num = request.GET['To'][2:]      # our_twilio number WITH country code and '+'

        msg_content = request.GET['Body']
        sms_sid = request.GET['SmsSid']

        last_msg_record = MessageRecord.objects.filter(message__isnull=False, receiver_num=caller_num).last()

        if last_msg_record is None: # we never sent/received message from this number, so welcome them and alert our team via email
            client = TwilioRestClient(T4S_TWILIO_SID, T4S_TWILIO_TOKEN)
            send_sms(client, FIRST_TIMER_WELCOME, caller_num, our_twilio_num, campaign=None, task_queue=None, root_msg=None)
            subject = "Unknown user (" + caller_num + ") sent text to the system"
            msg_body = "Someone with phone number: " + caller_num + " texted our system.\n" + \
                        "The text message content was as follow:\n" + msg_content + "\n" + \
                        "Please follow up with him as necessary."
            send_email_notification(subject, msg_body)
            return HttpResponse('OK')
        else:
            last_msg_sent = last_msg_record.message

        task_queue = last_msg_record.task_queue
        campaign = last_msg_record.campaign     # For trigger keyword if user type 'A' vs. 'a', we need to cover this

        # Note: we cannot search twilio num by TwilioAccount.objects.get(number=our_twilio_num)
        # because our_twilio_num has country code and '+' in it
        if task_queue: # if this reply is in response to an earlier message from us, it has task_queue
            twilio = task_queue.twilio
            client = TwilioRestClient(twilio.sid, twilio.token)#(settings.T4S_TWILIO_SID, settings.T4S_TWILIO_TOKEN)

        #our_twilio_num = twilio.number # because URL's "To=" number has "+1"/country code, we'll use it for now to prepare for i18n
        recipient = User.objects.get(username=caller_num)

        # Step 1: Save incoming msg first
        record = MessageRecord(content=msg_content, sender_num=caller_num, receiver_num=our_twilio_num, twilio_msg_sid=sms_sid,
                           campaign=campaign, task_queue=task_queue, prompting_msg=last_msg_sent, is_wizard=False)
        record.save()

        # Step 2: Check if student replied HALT
        matched_obj = re.match('halt.*', msg_content, re.I|re.S)
        user = get_user_role(recipient)
        if matched_obj:
            user.halt = True
            user.save()

            send_sms(client, HALT_REPLY, caller_num, our_twilio_num, campaign=campaign, task_queue=task_queue, root_msg=last_msg_sent)
            return HttpResponse('OK')

        # Step 3: Check if student replied RESUME
        matched_obj = re.match('resume.*', msg_content, re.I|re.S)
        if matched_obj:
            user.halt = False
            user.save()

            send_sms(client, RESUME_REPLY, caller_num, our_twilio_num, campaign=campaign, task_queue=task_queue, root_msg=last_msg_sent)
            return HttpResponse('OK')

        # Step 4: Check if student replied TUTORIAL
        matched_obj = re.match('tutorial.*', msg_content, re.I|re.S)
        if matched_obj:
            tutorial_campaign = Campaign.objects.filter(tutorial=True)
            response = tutorial_campaign.last().root_message.get_full_content()

            send_sms(client, response, caller_num, our_twilio_num, campaign=tutorial_campaign.last(),
                     task_queue=task_queue, root_msg=tutorial_campaign.last().root_message)
            return HttpResponse('OK')

        # Step 5: Check if student replied AID
        matched_obj = re.match('aid.*', msg_content, re.I|re.S)
        if matched_obj:
            try:
                school = User.objects.get(username=caller_num).student.school
            except:
                school = User.objects.get(username=caller_num).advisor.school

            response_msg = school.help_reply

            # IMPORTANT: we must set root_msg so that if they type HELPINFO in the middle of a conversation, we still don't lose track of where they are
            send_sms(client, response_msg, caller_num, our_twilio_num, campaign=campaign, task_queue=task_queue, root_msg=last_msg_sent)
            return HttpResponse('OK')

        # Step 6: Check if student reply CONTACT
        matched_obj = re.match('contact(.*)', msg_content, re.I|re.S)
        if matched_obj:
            try:
                school = User.objects.get(username=caller_num).student.school
            except:
                school = User.objects.get(username=caller_num).advisor.school
                
            for contact in school.contacts.split(','):
                response_msg = CONTACT_TEXT + caller_num
                send_sms(client, response_msg, contact, our_twilio_num, root_msg=last_msg_sent)  # IMPORTANT: we must set root_msg so that if they type HELPINFO in the middle of a conversation, we still don't lose track of where they are
            return HttpResponse('OK')

        # Step 7: Check if student replied BACK
        matched_obj = re.match('back(.*)', msg_content, re.I|re.S)
        is_back_step = False
        if matched_obj and matched_obj.groups():
            is_back_step = True
            try:
                steps = int(matched_obj.group(1).strip())
            except: # 'back', 'back random 4', etc.
                steps = 1
            
            for step in range(steps):   # rewind
                option = MessageOption.objects.filter(child_msg=last_msg_sent).first()
                if option:
                    last_msg_sent = option.parent_msg
                else:
                    break

            sent_msgs = MessageRecord.objects.filter(message__isnull=False, task_queue=last_msg_record.task_queue, receiver_num=caller_num).order_by('-id')
            if sent_msgs.count() > steps:
                last_msg_record = sent_msgs[steps]
            else:
                last_msg_record = sent_msgs.last()

        # This used to be here; but I moved it to Step#1 above. See what the side effects are after 8/20/2015
        # record = MessageRecord(content=msg_content, sender_num=caller_num, receiver_num=our_twilio_num, twilio_msg_sid=sms_sid,
        #                    campaign=campaign, task_queue=task_queue, prompting_msg=last_msg_sent, is_wizard=False)
        # record.save()

        # If student replied BACK, handle it
        if is_back_step:
            # send the msg, donot try to match the options
            response = last_msg_sent.get_full_content()
            send_sms(client, response, caller_num, our_twilio_num, campaign=campaign, task_queue=task_queue, root_msg=last_msg_sent)
        else:
            # helpinfo, HELPINFO, Helpinfo (we respond to them say "Here's the number for suicide prevention center: "; QUIT, quit, Quit (then we unsubscribe them from our message stream)
            # BACK, Back, back (will rewind the message to an earlier one)

            # Handle the end of the conversation
            if not last_msg_sent.options.exists():
                send_sms(client, THANKYOU, caller_num, our_twilio_num, campaign=campaign, task_queue=task_queue, root_msg=last_msg_sent)
                
            else:
                # Check if this user and this campaign has been queued in wizard (i.e. if not wizard.status:); if YES, return OK
                wizard_table_entry = Wizard.objects.filter(campaign=campaign, recipient=recipient)
                if wizard_table_entry:
                    wizard = wizard_table_entry.last()
                    if not wizard.status: # if case is NOT closed
                        # We'll notify researcher (this is such a wasteful use of Twilio texting
                        # and could potentially overwhelm/annoy whoever guards the system; but Tony wants it)
                        notify_msg = "New text in Wizard: participant (" + format_to_phone_num(caller_num) + \
                                     ") in wizard queue replied '" + msg_content + "' for " + \
                                "conversation titled: " + campaign.title
                        to_groups = last_msg_sent.groups.all()
                        send_sms_notification(client, notify_msg, to_groups, our_twilio_num,
                                              campaign=campaign, task_queue=task_queue, root_msg=last_msg_sent)

                        return HttpResponse('OK')

                # checking if trigger keyword is nonexistent
                matched_msg_option = [] #None
                user_response = msg_content.strip()

                for option in last_msg_sent.options.all():
                    trigger_keyword = option.trigger_keyword
                    # We will match "YEs" as well as "Yes!!" when researcher only defined "Yes" as keyword
                    # CAUTION: The first clause of checking if trigger != FREERESPONSE is important and must come first as a short-circuit
                    if (trigger_keyword != FREERESPONSE) and (re.match('^\s*%s.*$'%trigger_keyword, user_response, re.I)):
                        # matched_msg_option = option
                        # we cannot break here because if we have "1" and "10" as keyword,
                        # the latter option will never be detected
                        matched_msg_option.append(option)

                # can't find in regular list of expected options, so trying to match and see if '*' is there
                if not matched_msg_option:
                    for option in last_msg_sent.options.all():
                        if option.trigger_keyword == FREERESPONSE:
                            matched_msg_option.append(option)

                # this means we have more than one match in the regex above; choose the one with longer option
                if len(matched_msg_option) > 1:
                    max_len = max(len(x.trigger_keyword) for x in matched_msg_option)
                    for o in matched_msg_option:
                        if len(o.trigger_keyword) == max_len:
                            matched_msg_option = [o]
                            break

                # If we found a match in keyword, we respond
                if matched_msg_option:
                    matched_msg_option = matched_msg_option[0]
                    # send planned response to user here
                    response = matched_msg_option.child_msg.get_full_content()
                    # TODO: decide if root_msg=matched_msg_option.parent_msg is correct because we are going to be using root_msg as pretty much prompting_msg
                    # TODO: also decide if renaming 'root_msg' to 'prompting_msg' might make sense in smsmessages/utils.py's send_sms method
                    send_sms(client, response, caller_num, our_twilio_num, campaign=campaign, task_queue=task_queue, root_msg=matched_msg_option.child_msg)

                    # Send notifications to advisors/researchers/anyone if it is set up
                    # TODO: refactor
                    notify_msg = "T4S Notification: a participant (" + format_to_phone_num(caller_num) + \
                                 ") replied '" + user_response + "' CORRECTLY to a prompt which expects this keyword: '" + \
                                 trigger_keyword +"' in conversation titled '" + campaign.title + "'. "
                    wizard_msg = "Queued in wizard per your request anyway."
                    if matched_msg_option.wizard: # this is when researcher wants to queue participant in wizard regardless if his/her response is correct
                        notify_msg += " " + wizard_msg      # step 1. extend the notification message
                        wizard_table_entry = Wizard.objects.filter(campaign=campaign, recipient=recipient)

                        # Since the user explicitly said queue in wizard regardless of response correctness, we do it
                        if not wizard_table_entry:          # step 2. register in the wizard table
                            wizard = Wizard(campaign=campaign, recipient=recipient, message=last_msg_sent)
                            wizard.save()
                        else: # there's an entry in the table for this campaign for this recipient, so make sure we set its case status to "open"
                            wizard = wizard_table_entry.last()
                            wizard.status = False
                            wizard.deleted = False      # if deleted, show it in the table again
                            wizard.save()

                        # step 3. update the 'is_wizard' flag to 'True' in message log
                        record.is_wizard = True
                        record.save()

                    # after taking care of wizard business, send notification to respective folks
                    if matched_msg_option.notify:
                        # I considered using TaskQueue to send messages; But it requires us to
                        # associate a campaign_obj, plus it doesn't allow us to avoid recording
                        # these sent notification in log. Archiving these notification messages will
                        # just add noise in our DB when time comes for data analysis.
                        # So I'm avoiding that and choosing a simpler--albeit a little bit
                        # time consuming--approach that gives us a bit more freedom
                        to_groups = last_msg_sent.groups.all()
                        root_msg = matched_msg_option.parent_msg
                        send_sms_notification(client, notify_msg, to_groups, our_twilio_num,
                                              campaign=campaign, task_queue=task_queue, root_msg=None)

                else: # No match in option/trigger keyword, we tell them we don't understand
                    dont_understand = DONT_UNDERSTAND + "Please reply with "
                    for option in last_msg_sent.options.all():
                        trigger_keyword = option.trigger_keyword
                        if (trigger_keyword != FREERESPONSE): # not asterik
                            dont_understand += trigger_keyword + " or "

                    dont_understand += "type AID if you need more help." #dont_understand[:-3] # remove trailing "or "

                    # Step 1: Reply to participant first
                    send_sms(client, dont_understand, caller_num, our_twilio_num, campaign=campaign, task_queue=task_queue, root_msg=last_msg_sent)


                    # Step 2: Make sure to register this conversation instance in messagerecord regardless
                    # (set is_wizard=True for now; not very sure if we need to set it differently in the future)
                    record.is_wizard = True
                    record.save()

                    # Potential TODO based on Tony's new new request
                    # remove Step 3 and (possibly) step 4 below if he agrees; if he still wants notification,
                    # we can change "NOT queued in wizard"

                    # # Step 3: Mandatory queuing of this instance in wizard table because Tony requested it.
                    # # First search participant with specific campaign in the wizard table
                    # wizard_table_entry = Wizard.objects.filter(campaign=campaign, recipient=recipient)
                    #
                    # if wizard_table_entry:          # s/he is already registered in the table for this campaign
                    #     wizard = wizard_table_entry.last()
                    #
                    #     # reopen the case
                    #     if wizard.status:    # if status is True, case closed
                    #         wizard.status = False
                    #         wizard_table_entry.deleted = False      # if deleted, show it in the table again
                    #         wizard.save()
                    #
                    # else: # don't have old wizard table entry; create a new one
                    #     wizard = Wizard(campaign=campaign, recipient=recipient, message=last_msg_sent)
                    #     wizard.save()
                    #
                    # # Step 4: We'll notify researcher (this is such a wasteful use of Twilio texting
                    # # and could potentially annoy whoever guards the system; but Tony wants it)
                    # notify_msg = "T4S Notification: participant (" + format_to_phone_num(caller_num) + \
                    #              ") replied '" + user_response + "', which seems like an unexpected option for " + \
                    #         "conversation titled '" + campaign.title + "'. Queued in wizard."
                    #
                    # to_groups = last_msg_sent.groups.all()
                    # send_sms_notification(client, notify_msg, to_groups, our_twilio_num,
                    #                       campaign=campaign, task_queue=task_queue, root_msg=last_msg_sent)

        # need to know the last message they received
        return HttpResponse('OK')

class UserConversationView(LoginRequiredMixin, TemplateView):
    template_name = 'messages/view_conversation.html'
    
    def get_context_data(self, **kwargs):
        data = super(UserConversationView, self).get_context_data(**kwargs)
        phone_num = self.request.GET['username']
        if 'taskq_id' in self.request.GET:
            taskq_id = self.request.GET['taskq_id']
            # data['taskq_id'] = taskq_id # let's pass this on for use in "Chat with Participant directly" feature
            taskq_obj = TaskQueue.objects.get(id=taskq_id)
            # messages replied/sent by student tied to a particular taskQ
            records = MessageRecord.objects.filter(task_queue=taskq_obj).filter(Q(receiver_num=phone_num)|Q(sender_num=phone_num))
        else: 
            records = MessageRecord.objects.filter(Q(receiver_num=phone_num)|Q(sender_num=phone_num))  # all messages sent/received by student

        data['records'] = records
        data['phone_number'] = phone_num
        return data

class TaskQueueConversationView(LoginRequiredMixin, TemplateView):
    template_name = 'messages/taskq_conversation.html'
    
    def get_context_data(self, **kwargs):
        data = super(TaskQueueConversationView, self).get_context_data(**kwargs)
        taskq_id = self.request.GET['taskq_id']
        taskq_obj = TaskQueue.objects.get(id=taskq_id)

        records = MessageRecord.objects.filter(task_queue=taskq_obj, message__isnull=True) # if 'message__isnull=True' then this is the message we received from students
        data['records'] = records
        return data

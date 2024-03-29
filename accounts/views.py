from django.views.generic.edit import FormView

from accounts.forms import LoginForm, RegisterForm, ChangePasswordForm,\
    UpdateStudentProfileForm, UpdateConversationLimitForm, UpdateTimeLimitForm,\
    TwilioAccountCreateForm, TwilioAccountEditForm
from django.contrib import auth, messages
from django.views.generic.base import RedirectView, View, TemplateView
from django.views.generic.list import ListView
from django.views.generic.edit import CreateView, UpdateView, DeleteView,\
    FormView

from django.core.urlresolvers import reverse_lazy
from django.contrib.auth.models import User
from accounts.constants import STUDENT, RESEARCHER, PEERLEADER
from accounts.models import Researcher, Student, Advisor, TwilioAccount, TimeLimit
from braces.views import JsonRequestResponseMixin, AjaxResponseMixin,\
    LoginRequiredMixin
from accounts.utils import send_verification_code, get_user_role
from organizations.models import School
from t4s import settings


class LoginView(FormView):
    template_name = 'accounts/login.html'
    form_class = LoginForm
    success_url = reverse_lazy('campaigns:list')

    def form_valid(self, form):
        data = form.cleaned_data
        auth.login(self.request, data['user'])
        return super(LoginView, self).form_valid(form)


class LogoutView(RedirectView):
    permanent = False
    url = reverse_lazy('portals:home')

    def get_redirect_url(self, *args, **kwargs):
        auth.logout(self.request)
        return super(LogoutView, self).get_redirect_url(*args, **kwargs)


class RegisterView(FormView):
    template_name = 'accounts/register.html'
    form_class = RegisterForm
    success_url = reverse_lazy('accounts:confirm')

    def get_context_data(self, **kwargs):
        data = super(RegisterView, self).get_context_data(**kwargs)
        data['schools'] = School.objects.all()
        return data

    def form_valid(self, form):
        data = form.cleaned_data

        user = User(username=data.get('username'))
        user.first_name = data.get('firstname')
        user.last_name = data.get('lastname')
        user.email = data.get('email')
        user.set_password(data.get('password'))
        user.is_active = False
        user.save()

        if data.get('role') == RESEARCHER:
            researcher = Researcher()
            researcher.user = user
            researcher.phone = data.get('phone')
            researcher.save()
        elif data.get('role') == STUDENT:
            student = Student()
            student.user = user
            student.school = School.objects.get(id=data.get('school')) # <select name=xxxx> defines this
            student.role = PEERLEADER
            student.save()
        else:
            advisor = Advisor()
            advisor.user = user
            advisor.school = School.objects.get(id=data.get('school'))
            advisor.save()
            
        return super(RegisterView, self).form_valid(form)


class VerficationCodeView(JsonRequestResponseMixin, AjaxResponseMixin, View):
    def get_ajax(self, request, *args, **kwargs):
        to_num = request.GET.get('phonenum')
        return self.render_json_response({'sent': send_verification_code(to_num)})


class ChangePasswordView(LoginRequiredMixin, FormView):
    template_name = 'accounts/change_password.html'
    form_class = ChangePasswordForm
    success_url = reverse_lazy('accounts:change_password')

    def get_form(self, form_class): # to pass down to Form Class so that user obj can be seen there
        return form_class(self.request.user, **self.get_form_kwargs())

    def form_valid(self, form):
        data = form.cleaned_data
        new_password = data['new_password']
        self.request.user.set_password(new_password)
        self.request.user.save()

        messages.success(self.request, 'Update success')

        return super(ChangePasswordView, self).form_valid(form)


class UserProfileView(LoginRequiredMixin, TemplateView):
    template_name = 'accounts/user_profile.html'

    def get_context_data(self, **kwargs):
        data = super(UserProfileView, self).get_context_data(**kwargs)
        usr_name = self.request.GET['username']
        usr_obj = User.objects.get(username=usr_name)
        data['person'] = get_user_role(usr_obj)
        data['twilio_num'] = settings.T4S_TWILIO_NUMBER
        data['twilio_sid'] = settings.T4S_TWILIO_SID
        data['twilio_token'] = settings.T4S_TWILIO_TOKEN
        return data


class UpdateConversationLimitView(LoginRequiredMixin, FormView):
    template_name = 'accounts/update_conversation_limit.html'
    form_class = UpdateConversationLimitForm

    def get_success_url(self):
        return reverse_lazy('accounts:user_profile') + '?username=' + self.request.GET['username']

    def get_person(self):
        usr_name = self.request.GET['username']
        usr_obj = User.objects.get(username=usr_name)
        return get_user_role(usr_obj)

    def get_form_class(self):
        person = self.get_person()
        if isinstance(person, Student):
            return UpdateConversationLimitForm
        return super(UpdateConversationLimitView, self).get_form_class()

    def get_form(self, form_class): # create a new instance of form_class; required because of __init__ in UpdateProfileForm
        person = self.get_person()
        return form_class(person, **self.get_form_kwargs())

    def get_context_data(self, **kwargs):
        data = super(UpdateConversationLimitView, self).get_context_data(**kwargs)
        data['username'] = self.request.GET['username']
        return data

    def form_valid(self, form):
        data = form.cleaned_data
        person = self.get_person()
        person.conversation_limit_per_day = data['conversation_limit_per_day']
        person.save()

        return super(UpdateConversationLimitView, self).form_valid(form)

class TwilioAccountListView(LoginRequiredMixin, ListView):
    model = TwilioAccount
    template_name = 'accounts/list_twilio_accounts.html'
    paginate_by = 20

    #this is just so that we can click on 'User Profile Settings' breadcrumb
    def get_context_data(self, **kwargs):
        data = super(TwilioAccountListView, self).get_context_data(**kwargs)
        data['username'] = self.request.user.get_username()
        return data

class TwilioAccountCreateView(LoginRequiredMixin, CreateView):
    model = TwilioAccount
    form_class = TwilioAccountCreateForm
    template_name = 'accounts/create_twilio_accounts.html'
    success_url = reverse_lazy('accounts:list_twilio_account')

class TwilioAccountEditView(LoginRequiredMixin, UpdateView):
    model = TwilioAccount
    form_class = TwilioAccountEditForm
    template_name = 'accounts/edit_twilio_accounts.html'
    success_url = reverse_lazy('accounts:list_twilio_account')

class TwilioAccountDeleteView(LoginRequiredMixin, DeleteView):
    model = TwilioAccount
    success_url = reverse_lazy('accounts:list_twilio_account')

    def get(self, request, *args, **kwargs):
        return self.delete(request, *args, **kwargs)

class UpdateTimeLimitView(LoginRequiredMixin, FormView):
    model = TimeLimit
    template_name = 'accounts/update_time_limit.html'
    form_class = UpdateTimeLimitForm

    def get_success_url(self):
        return reverse_lazy('accounts:user_profile') + '?username=' + self.request.GET['username']

    # so that we can go back to 'User Profile Settings' page after update
    def get_context_data(self, **kwargs):
        data = super(UpdateTimeLimitView, self).get_context_data(**kwargs)
        data['username'] = self.request.GET['username']
        return data

    def get_form(self, form_class): # create a new instance of form_class; required because of __init__ in UpdateProfileForm
        time_limit = TimeLimit.objects.first()
        return form_class(time_limit, **self.get_form_kwargs())

    def form_valid(self, form):
        data = form.cleaned_data
        new_before = data['before']
        new_after = data['after']
        time_limit = TimeLimit.objects.first() #  we'll always use just the first entry
        time_limit.before = new_before
        time_limit.after = new_after
        time_limit.save()
        messages.success(self.request, 'Update success')

        return super(UpdateTimeLimitView, self).form_valid(form)

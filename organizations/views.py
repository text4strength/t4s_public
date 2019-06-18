from braces.views import LoginRequiredMixin, JsonRequestResponseMixin,\
    AjaxResponseMixin, SetHeadlineMixin


from django.contrib.auth.models import User
from django.core.urlresolvers import reverse_lazy
from django.forms.util import ErrorList
from django.http.response import HttpResponseRedirect
from django.views.generic.edit import CreateView, UpdateView, DeleteView,\
    FormView
from django.views.generic.list import ListView
from django.views.generic.base import View, TemplateView, RedirectView
from django import forms

from accounts.models import Student, Advisor, Researcher
from accounts.utils import get_user_role
from organizations.forms import StudentCreateForm, GroupCreateForm,\
    ContactEditForm, SchoolAddStudentForm,\
    SchoolAddAdvisorForm, GroupNameEditForm, GroupMembershipEditForm,\
    SchoolCreateForm
from organizations.models import School, Group


class GroupCreateView(LoginRequiredMixin, CreateView):
    model = Group
    form_class = GroupCreateForm
    template_name = 'organizations/create_group.html'
    success_url = reverse_lazy('organizations:list_group') # ('app_name:urls name')

    def get_context_data(self, **kwargs):
        data = super(GroupCreateView, self).get_context_data(**kwargs)
        data['schools'] = School.objects.all()
        return data
    
    def form_valid(self, form):
        group = form.save(commit=False)
        group.created_by = self.request.user
        group.save()

        # set this new group to all the selected members
        data = form.cleaned_data
        for phone in data['phone_numbers'].split(','):
            if phone:
                user = User.objects.get(username=phone)
                person = get_user_role(user)
                person.groups.add(group)    # don't need to save this because it's many-to-many field
        
        return super(GroupCreateView, self).form_valid(form)


class GroupMembershipEditView(LoginRequiredMixin, SetHeadlineMixin, FormView):
    form_class = GroupMembershipEditForm
    template_name = 'organizations/edit_group_member.html'

    def get_headline(self):
        group = Group.objects.get(id=self.request.GET['group_id'])
        return 'Manage Memebership of %s'%group.name

    def get_success_url(self):
        return reverse_lazy('organizations:edit_group_member') + '?group_id=' + self.request.GET['group_id'] 
    
    def get_context_data(self, **kwargs):
        data = super(GroupMembershipEditView, self).get_context_data(**kwargs)
        data.update(self.request.GET.items()) # new

        group = Group.objects.get(id=self.request.GET['group_id'])
        data['group'] = group

        data['students'] = list(Student.objects.filter(groups=group))
        data['advisors'] = list(Advisor.objects.filter(groups=group))
        data['all_users'] = data['students'] + data['advisors']

        # If we want table to be sortable, uncomment below and commented template part in edit_group_member.html
        # if (data.get('order_by') == "-"):
        #     data['all_users'].sort(key=lambda x: x.user.username, reverse=True)
        # elif (data.get('order_by') == ""):
        #     data['all_users'].sort(key=lambda x: x.user.username)

        data['schools'] = list(School.objects.all())
        return data

    def form_valid(self, form):
        data = form.cleaned_data
        group = Group.objects.get(id=self.request.GET['group_id'])

        for phone in data['phone_numbers'].split(','):
            phone = phone.strip()
            user = User.objects.get(username=phone)
            person = get_user_role(user)
            # if the group is not in the student groups, we add it
            if group not in person.groups.all():
                person.groups.add(group)       # Note: don't need to save bcoz ManyToMany
                
        return HttpResponseRedirect(self.get_success_url())


class GroupListView(LoginRequiredMixin, ListView):
    model = Group
    template_name = 'organizations/list_group.html'
    #paginate_by = 15 # we don't need this thanks to dataTables' pagination

    def get_context_data(self, **kwargs):
        data = super(GroupListView, self).get_context_data(**kwargs)
        data.update(self.request.GET.items())
        data['order_field'] = data.get('order_field', 'created_at')
        data['order_by'] = data.get('order_by', '-')
        return data

    def get_queryset(self):
        qs = super(GroupListView, self).get_queryset()
        qs = qs.order_by('-created_at')  # by default, show most recent
        order_field = self.request.GET.get('order_field')
        order_by = self.request.GET.get('order_by')
        if order_field:
            qs = qs.order_by('%s%s'%(order_by, order_field))
        return qs


class GroupNameEditView(LoginRequiredMixin, UpdateView):
    model = Group
    form_class = GroupNameEditForm
    template_name = 'organizations/edit_group_name.html'
    success_url = reverse_lazy('organizations:list_group')


class GroupDeleteView(LoginRequiredMixin, DeleteView):
    model = Group
    success_url = reverse_lazy('organizations:list_group')

    def get(self, request, *args, **kwargs):
        return self.delete(request, *args, **kwargs)


class SchoolCreateView(LoginRequiredMixin, CreateView):
    model = School
    form_class = SchoolCreateForm
    template_name = 'organizations/create_school.html'
    success_url = reverse_lazy('organizations:list_school')


class SchoolListView(LoginRequiredMixin, ListView):
    model = School
    template_name = 'organizations/list_school.html'
    # paginate_by = 15 # now handled by dataTable's pagination

    def get_context_data(self, **kwargs):
        data = super(SchoolListView, self).get_context_data(**kwargs)
        data.update(self.request.GET.items())
        data['order_field'] = data.get('order_field', 'created_at')
        data['order_by'] = data.get('order_by', '-')
        return data

    def get_queryset(self):
        qs = super(SchoolListView, self).get_queryset()
        qs = qs.order_by('-created_at')  # by default, show most recent
        order_field = self.request.GET.get('order_field')
        order_by = self.request.GET.get('order_by')
        if order_field:
            qs = qs.order_by('%s%s'%(order_by, order_field))
        return qs

class SchoolEditView(LoginRequiredMixin, UpdateView):
    model = School
    form_class = SchoolCreateForm
    template_name = 'organizations/edit_school.html'
    success_url = reverse_lazy('organizations:list_school')


class SchoolDeleteMemberView(LoginRequiredMixin, DeleteView):
    model = User
    
    def get_success_url(self):
        return reverse_lazy('organizations:list_student') + '?school_id=' + self.request.GET['school_id'] 
    
    # This is to prevent us to taking ot another page and be asked to confirm if we want to delete
    def get(self, request, *args, **kwargs):
        return self.delete(request, *args, **kwargs)


class ContactEditView(LoginRequiredMixin, UpdateView):  # UpdateView will pass down object of the model, which is "School" in this case
    model = School
    form_class = ContactEditForm
    template_name = 'organizations/edit_contact.html'
    success_url = reverse_lazy('organizations:list_school')


class PersonRemoveView(LoginRequiredMixin, RedirectView):
    permanent = False   # if permanent is True and if we refresh page, they will not actually request, but instead use the browser cache, so we want it to be false

    def get_redirect_url(self, *args, **kwargs):
        # delete stu here and redirect to the same page
        user = User.objects.get(id=self.request.GET['user_id'])
        person = get_user_role(user)
        group = Group.objects.get(id=self.request.GET['group_id'])
        person.groups.remove(group)                    # DONT need to save because ManyToMany field auto saves (because student is not changed in changing ManyToMany)
        return reverse_lazy('organizations:edit_group_member') + '?group_id=' + self.request.GET['group_id']


# TODO: change this name to StudentAddView or something
class StudentListView(LoginRequiredMixin, FormView):
    form_class = SchoolAddStudentForm
    template_name = 'organizations/list_student.html'

    def get_success_url(self):
        return reverse_lazy('organizations:list_student') + '?school_id=' + self.request.GET['school_id'] 
    
    def get_context_data(self, **kwargs):
        data = super(StudentListView, self).get_context_data(**kwargs)
        school = School.objects.get(id=self.request.GET['school_id'])
        data['school'] = school
        data['students'] = list(Student.objects.filter(school=school))
        return data

    def form_valid(self, form):
        data = form.cleaned_data
        phones = []
        first_names = []
        last_names = []
        default_name = 'N/A'

        for phone in data['phone_numbers'].split(','):
            phones.append(phone.strip())

        for fn in data['first_names'].split(','):
            if not (fn.strip()): # if empty string, then default to 'N/A'
                first_names.append(default_name)
            else:
                first_names.append(fn.strip())

        for ln in data['last_names'].split(','):
            if not (ln.strip()): # if empty string, then default to 'N/A'
                last_names.append(default_name)
            else:
                last_names.append(ln.strip())

        #qs = User.objects.filter(username__in=phones) # this is not specific to school, so commented out
        qs = Student.objects.filter(user__username__in=phones, school__id=self.request.GET['school_id'])

        if qs: # TODO: refactor
            duplicate_nums = set(student.user.username for student in qs)
            duplicate_nums_str = ", ".join(duplicate_nums)
            error_msg = "Phone number(s): " + duplicate_nums_str + " already belong(s) to this organization. " + \
                        "If you'd like to update the info--such as first/last names--of these " + \
                        "number(s), please delete/remove first from the table above, and add them as a new entry. " + \
                        "Otherwise, remove the phone number(s) from the list below, and try again."
            form._errors[forms.forms.NON_FIELD_ERRORS] = ErrorList([error_msg])

            return self.form_invalid(form)

        # We'll base block data entry on phone numbers because
        # they are the life-blood of our program
        len_first_names = len(first_names)
        len_last_names = len(last_names)

        for idx, phone in enumerate(phones):
            if not User.objects.filter(username=phone).exists():
                user = User(username=phone)
                user.first_name = first_names[idx] if len_first_names > idx else default_name
                user.last_name = last_names[idx] if len_last_names > idx else default_name
                user.save()

                person = Student(user=user)
                person.school = School.objects.get(id=self.request.GET['school_id'])
                person.role = data['role']
                person.save()

            else: # TODO: refactor this
                error_msg = "PHONE NUMBER ALREADY EXISTS: (" + phone + ") already exist in the database."

                # means user exists in the DB, but is NOT advisor (probably student or something else)
                if Advisor.objects.filter(user__username=phone).exists():
                    school_name = Advisor.objects.filter(user__username=phone).last().school.name
                    error_msg += " We located it in organization named: " + school_name + "."
                elif Student.objects.filter(user__username=phone).exists():
                    school_name = Student.objects.filter(user__username=phone).last().school.name
                    error_msg += " We located it in organization named: " + school_name + "."

                error_msg += " We do not allow duplicate phone numbers in the user database." + \
                            " If you'd like to add the user to this organization, please remove " + \
                            "him/her from the other organization and try again."
                form._errors[forms.forms.NON_FIELD_ERRORS] = ErrorList([error_msg])
                return self.form_invalid(form)

        return HttpResponseRedirect(self.get_success_url())

class GroupManagementView(LoginRequiredMixin, TemplateView):
    template_name = 'organizations/manage_groups.html'

    def get_context_data(self, **kwargs):
        data = super(GroupManagementView, self).get_context_data(**kwargs)
        data['groups'] = Group.objects.all()
        return data


class ListStudentByGroupView(LoginRequiredMixin, JsonRequestResponseMixin, AjaxResponseMixin, View):
    def get_ajax(self, request, *args, **kwargs):
        group_id = request.GET.get('group_id')
        group = Group.objects.get(id=group_id)
        students = Student.objects.filter(groups=group)
        groups_json = [{'username': stu.username} for stu in students]
        return self.render_json_response(groups_json)


class ListMembersBySchoolView(LoginRequiredMixin, JsonRequestResponseMixin, AjaxResponseMixin, View):
    def get_ajax(self, request, *args, **kwargs):
        school_id = request.GET.get('school_id')
        school = School.objects.get(id=school_id)
        advisors = list(Advisor.objects.filter(school=school))
        students = list(Student.objects.filter(school=school))
        members_json = [{'phone_num': stu.user.username, 'role': stu.get_role_display(), 'school': school.name} for stu in students]
        members_json += [{'phone_num': adv.user.username, 'role': 'Advisor', 'school': school.name} for adv in advisors]

        return self.render_json_response(members_json)


class AdvisorListView(LoginRequiredMixin, FormView):
    form_class = SchoolAddAdvisorForm
    template_name = 'organizations/list_advisor.html'
    
    def get_success_url(self):
        return reverse_lazy('organizations:list_advisor') + '?school_id=' + self.request.GET['school_id'] 

    def get_context_data(self, **kwargs):
        data = super(AdvisorListView, self).get_context_data(**kwargs)
        school = School.objects.get(id=self.request.GET['school_id'])
        data['school'] = school
        data['advisors'] = list(Advisor.objects.filter(school=school))
        return data

    def form_valid(self, form):
        data = form.cleaned_data
        phones = []
        first_names = []
        last_names = []
        default_name = 'N/A'

        for phone in data['phone_numbers'].split(','):
            phones.append(phone.strip())

        for fn in data['first_names'].split(','):
            if not (fn.strip()): # if empty string, then default to 'N/A'
                first_names.append(default_name)
            else:
                first_names.append(fn.strip())

        for ln in data['last_names'].split(','):
            if not (ln.strip()): # if empty string, then default to 'N/A'
                last_names.append(default_name)
            else:
                last_names.append(ln.strip())

        qs = Advisor.objects.filter(user__username__in=phones, school__id=self.request.GET['school_id'])

        if qs: # TODO: refactor
            duplicate_nums = set(advisor.user.username for advisor in qs)
            duplicate_nums_str = ", ".join(duplicate_nums)
            error_msg = "Phone number(s): " + duplicate_nums_str + " already belongs to this organization. " + \
                        "If you'd like to update the info--such as first/last names--of these " + \
                        "number(s), please delete/remove first from the table above, and add them as a new entry. " + \
                        "Otherwise, remove the phone number(s) from the list below, and try again."
            form._errors[forms.forms.NON_FIELD_ERRORS] = ErrorList([error_msg])
            return self.form_invalid(form)

        # We'll base block data entry on phone numbers because
        # they are the life-blood of our program
        len_first_names = len(first_names)
        len_last_names = len(last_names)

        for idx, phone in enumerate(phones):
            if not User.objects.filter(username=phone).exists():
                user = User(username=phone)
                user.first_name = first_names[idx] if len_first_names > idx else default_name
                user.last_name = last_names[idx] if len_last_names > idx else default_name
                user.save()

                person = Advisor(user=user)
                person.school = School.objects.get(id=self.request.GET['school_id'])
                person.save()
            else: # TODO: refactor this
                error_msg = "PHONE NUMBER ALREADY EXISTS: (" + phone + ") already exist in the database."

                # means user exists in the DB, but is NOT advisor (probably student or something else)
                if Student.objects.filter(user__username=phone).exists():
                    school_name = Student.objects.filter(user__username=phone).last().school.name
                    error_msg += " We located it in organization named: " + school_name + "."
                elif Advisor.objects.filter(user__username=phone).exists():
                    school_name = Advisor.objects.filter(user__username=phone).last().school.name
                    error_msg += " We located it in organization named: " + school_name + "."

                error_msg += " We do not allow duplicate phone numbers in the user database." + \
                            " If you'd like to add the user to this organization, please remove " + \
                            "him/her from the other organization and try again."
                form._errors[forms.forms.NON_FIELD_ERRORS] = ErrorList([error_msg])
                return self.form_invalid(form)

        return HttpResponseRedirect(self.get_success_url())


class SchoolDeleteAdvisorView(LoginRequiredMixin, DeleteView):
    model = User
    
    def get_success_url(self):
        return reverse_lazy('organizations:list_advisor') + '?school_id=' + self.request.GET['school_id'] 
    
    # This is to prevent us to taking ot another page and be asked to confirm if we want to delete
    def get(self, request, *args, **kwargs):
        return self.delete(request, *args, **kwargs)

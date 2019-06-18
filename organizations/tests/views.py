from datetime import datetime
from django.test import TestCase

from django.contrib.auth.models import User
from accounts.models import Student
from organizations.models import School, Group


class OrganizationsViewTestCase(TestCase):
    def test_index(self):
        school_name = "xxx"
        school_1 = School.objects.create(
            name = school_name,
            created_at = datetime.datetime(2014, 04, 10, 0, 37),
            contacts = "555123456"
        )
        group_1 = Group.objects.create(
            name = "FemalesWithScoreLessThan_5"
        )
        user_1 = User.objects.create(
            first_name = "Test",
            last_name = "Name",
            email = "test@test.com",
        )
        student_1 = Student.objects.create(
            user = user_1,
            school = school_1,
            groups = group_1,
            role = "Peer Leader",
            created_at = datetime.datetime(2014, 04, 10, 0, 37),
        )

        resp = self.client.get('/organizations/')
        self.assertEqual(resp.status_code, 200)

        self.assertTrue('organizations_list' in resp.context)

        # There's only one school in the organization list
        self.assertEqual([organization.pk for organization in resp.context['organizations_list']], [1])

        organization = resp.context['organizations_list'].first()
        self.assertEqual(organization.name, school_name)
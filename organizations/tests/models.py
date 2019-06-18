from django.db import models
from django.test import TestCase
from django.contrib.auth.models import User
from organizations.models import Group, School

class OrganizationsModelTestCase(TestCase):

    def setUp(self):
        super(OrganizationsModelTestCase, self).setUp()

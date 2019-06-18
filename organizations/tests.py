from django.test import TestCase

# Create your tests here.
class OrganizationsViewTestCase(TestCase):
    def test_index(self):
        resp = self.client.get('/create_group/')
        self.assertEqual(resp.status_code, 200)


from __future__ import absolute_import

import pytest

from django import test
from django.contrib.auth.models import User
from django.test.utils import override_settings

from heythere.models import Notification, get_notification_types

TEST_NOTIFICATIONS = {
    'CUSTOM_USER': {
        'persistant': True,
        'send_onsite': True,
        'send_email': False,
        'headline_template': 'My headline: {{headline}}',
        'body_template': 'My body: {{body}}',
        'email_field': 'contact'
    },
    'TEMPORARY': {
        'persistant': False,
        'send_onsite': True,
        'send_email': True,
        'headline_template': 'My headline: {{headline}}',
        'body_template': 'My body: {{body}}',
    },
    'SEND_EMAIL': {
        'persistant': True,
        'send_onsite': False,
        'send_email': True,
        'headline_template': 'My headline: {{headline}}',
        'body_template': 'My body: {{body}}',
    }
}


class TestNotificationModel(test.TestCase):
    def setUp(self):
        self.user = User.objects.create_user('testuser')

    def _create_notification(self, notification_type=None):
        notification_type = notification_type or (
            get_notification_types()[0][0])
        notification = Notification.objects.create_notification(
            user=self.user,
            notification_type=notification_type,
            headline={'headline': 'This is a notification'},
            body={'body': 'This is the body'}
        )
        return notification

    def test_basic_notification(self):
        notification = self._create_notification()

        self.assertTrue(notification.active)
        self.assertEqual(notification.user, self.user)
        self.assertEqual(notification.headline, 'This is a notification')
        self.assertIn(notification.user.__unicode__(),
                      notification.__unicode__())

    def test_all_of_a_users_notifications(self):
        self._create_notification()
        self._create_notification()
        self._create_notification()

        self.assertEqual(Notification.objects.for_user(self.user).count(), 3)

    def test_reading_notification(self):
        notification = self._create_notification()
        self.assertTrue(notification.active)
        notification.read()
        self.assertFalse(notification.active)

    def test_mark_all_as_read(self):
        self._create_notification()
        self._create_notification()
        self._create_notification()
        self._create_notification()
        self._create_notification()

        self.assertEqual(self.user.notifications.unread(self.user).count(), 5)

        Notification.objects.clear_all(self.user)
        self.assertEqual(self.user.notifications.unread(self.user).count(), 0)

        self.assertEqual(self.user.notifications.read(self.user).count(), 5)

    def test_unsent(self):
        self._create_notification()
        self.assertEqual(self.user.notifications.unsent(self.user).count(), 1)

    @override_settings(NOTIFICATIONS=TEST_NOTIFICATIONS)
    def test_sending(self):
        self._create_notification('SEND_EMAIL')
        self.user.notifications.unsent(self.user).first().send()
        self.assertEqual(self.user.notifications.unsent(self.user).count(), 0)
        self.assertEqual(self.user.notifications.sent(self.user).count(), 1)

    def test_something(self):
        notification = Notification()
        notification.notification_type = 'BAD_TYPE'
        with pytest.raises(KeyError):
            notification.notification

    @override_settings(NOTIFICATIONS=TEST_NOTIFICATIONS)
    def test_sending_unmarks_active(self):
        self._create_notification('TEMPORARY')
        self.user.notifications.unsent(self.user).first().send()
        self.assertEqual(Notification.objects.unread(self.user).count(), 0)

    @override_settings(NOTIFICATIONS=TEST_NOTIFICATIONS)
    @override_settings(AUTH_USER_MODEL='tests.CustomUser')
    def test_change_email_field(self):
        self.assertIn(
            ('CUSTOM_USER', 'Custom_user'),
            Notification()._meta.get_field_by_name(
                'notification_type')[0].get_choices())
        notification = self._create_notification('CUSTOM_USER')
        self.assertIn('My body:', notification.body)

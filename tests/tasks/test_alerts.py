from tests import BaseTestCase
from unittest.mock import MagicMock, ANY, patch

from dingolytics.tasks.check_alerts_for_query import check_alerts_for_query_task
from dingolytics.tasks.check_alerts_for_query import notify_subscriptions
from redash.models import Alert


class TestCheckAlertsForQuery(BaseTestCase):
    def setUp(self):
        super().setUp()
        patch_1 = patch("dingolytics.tasks.check_alerts_for_query.notify_subscriptions")
        self.notify_subscriptions_mock = patch_1.start()
        self.addCleanup(patch_1.stop)

    def test_notifies_subscribers_when_should(self):
        Alert.evaluate = MagicMock(return_value=Alert.TRIGGERED_STATE)
        alert = self.factory.create_alert()
        check_alerts_for_query_task(alert.query_id)()
        self.assertTrue(self.notify_subscriptions_mock.called)

    def test_doesnt_notify_when_nothing_changed(self):
        Alert.evaluate = MagicMock(return_value=Alert.OK_STATE)
        alert = self.factory.create_alert()
        check_alerts_for_query_task(alert.query_id)()
        self.assertFalse(self.notify_subscriptions_mock.called)

    def test_doesnt_notify_when_muted(self):
        Alert.evaluate = MagicMock(return_value=Alert.TRIGGERED_STATE)
        alert = self.factory.create_alert(options={"muted": True})
        check_alerts_for_query_task(alert.query_id)()
        self.assertFalse(self.notify_subscriptions_mock.called)


class TestNotifySubscriptions(BaseTestCase):
    def test_calls_notify_for_subscribers(self):
        subscription = self.factory.create_alert_subscription()
        subscription.notify = MagicMock()
        notify_subscriptions(subscription.alert, Alert.OK_STATE)
        subscription.notify.assert_called_with(
            subscription.alert,
            subscription.alert.query_rel,
            subscription.user,
            Alert.OK_STATE,
            ANY,
            ANY,
        )

# pylint: disable=no-self-use,inconsistent-return-statements
# pylint: disable=invalid-name,unused-argument
from django.conf import settings

from logical_replication.utils import is_synced_contrib_app


class LogicalReplicationRouter:
    """Router to prevent django content types
    from being created on slave envs

    Place first in list of routers
    """

    def allow_migrate(self, db, app_label, model_name=None, **_hints):
        if is_synced_contrib_app(app_label) and (
            not settings.IS_MASTER_ENV or db == "slave"
        ):
            return False

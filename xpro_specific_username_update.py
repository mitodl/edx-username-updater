import json
import sys

from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.core.exceptions import ImproperlyConfigured

from users.utils import usernameify, is_duplicate_username_error
from users.api import find_available_username

import username_update_lib as update_lib

User = get_user_model()


USERNAME_RETRY_ATTEMPTS = 10


class XproSpecificUpdater(update_lib.Updater):
    @staticmethod
    def get_users_with_specified_usernames():
        if not update_lib.USERNAMES_TO_REGENERATE:
            raise ImproperlyConfigured(
                "Need to set the USERNAMES_TO_REGENERATE env var to indicate which usernames should be regenerated "
                "(comma-separated)"
            )
        usernames = update_lib.USERNAMES_TO_REGENERATE.split(",")
        user_qset = User.objects.filter(username__in=usernames)
        if user_qset.count() != len(usernames):
            found_usernames = set(user_qset.values_list("username", flat=True))
            username_diff = set(usernames) - found_usernames
            raise ImproperlyConfigured(
                "Could not find users for the following usernames - {}".format(",".join(username_diff))
            )
        return user_qset

    def perform_username_updates(self, **kwargs):
        updated = []
        failed = []
        ignored = []

        for user in self.get_users_with_specified_usernames():
            old_username = user.username
            initial_new_username = usernameify(user.name, email=user.email)
            if old_username == initial_new_username:
                ignored.append({
                    "username": user.username
                })
                continue
            user.username = initial_new_username
            saved = False
            stop_retrying = False
            attempts = 0
            while not saved and not stop_retrying and attempts < USERNAME_RETRY_ATTEMPTS:
                try:
                    user.save()
                    saved = True
                except IntegrityError as exc:
                    if not is_duplicate_username_error(exc):
                        stop_retrying = True
                        failed.append({
                            "old_username": old_username,
                            "new_username": user.username,
                            "exception": str(exc)
                        })
                    user.username = find_available_username(initial_new_username)
                finally:
                    attempts += 1
            if saved:
                updated.append({
                    "old_username": old_username,
                    "new_username": user.username,
                })
            elif not stop_retrying:
                failed.append({
                    "old_username": old_username,
                    "new_username": initial_new_username,
                    "failure": "Ran out of attempts for finding and saving username ({})".format(
                        initial_new_username
                    ),
                })

        return {
            "updated": updated,
            "failed": failed,
            "ignored": ignored,
        }


updater = XproSpecificUpdater(
    result_file_settings=update_lib.get_xpro_username_change_settings()
)
result_filename, result_dict = updater.perform_updates_and_handle_results()

# Write the results to stdout
sys.stdout.write(json.dumps({
    "result_file": result_filename or "(Result file not written)",
    "results": result_dict
}))

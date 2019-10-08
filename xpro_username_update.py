import json
import sys
from collections import namedtuple

from django.db.models.functions import Length
from django.contrib.auth import get_user_model
from django.db import IntegrityError

from users.utils import usernameify, is_duplicate_username_error
from users.api import find_available_username

import username_update_lib as update_lib

User = get_user_model()


AUTOGEN_USERNAME_LENGTH = 26
USERNAME_RETRY_ATTEMPTS = 10

SuccessfulChange = namedtuple("SuccessfulChange", "old_username, new_username")
FailedChange = namedtuple("FailedChange", "username, new_username, failure")


def namedtuple_to_dict(ntuple):
    return dict(ntuple._asdict())


def ulid_username_user_qset():
    return (
        User.objects
        .annotate(username_length=Length("username"))
        .filter(
            username_length=AUTOGEN_USERNAME_LENGTH,
            username__regex=r"^[A-Z0-9]+$"
        )
        .order_by("created_on")
    )


def updated_username_gen():
    for user in ulid_username_user_qset():
        old_username = user.username
        initial_new_username = usernameify(user.name, email=user.email)
        user.username = initial_new_username
        saved = False
        failed = False
        attempts = 0
        while not saved and not failed and attempts < USERNAME_RETRY_ATTEMPTS:
            try:
                user.save()
                saved = True
            except IntegrityError as exc:
                if not is_duplicate_username_error(exc):
                    failed = True
                    yield FailedChange(
                        username=old_username,
                        new_username=user.username,
                        failure=str(exc),
                    )
                user.username = find_available_username(initial_new_username)
            finally:
                attempts += 1
        if saved:
            yield SuccessfulChange(
                old_username=old_username,
                new_username=user.username,
            )
        elif not failed:
            yield FailedChange(
                username=old_username,
                new_username=initial_new_username,
                failure="Ran out of attempts for finding and saving username ({})".format(
                    initial_new_username
                ),
            )


class XproUpdater(update_lib.Updater):
    def perform_username_updates(self, **kwargs):
        updated = []
        failed = []

        for update_result in updated_username_gen():
            result_dict = namedtuple_to_dict(update_result)
            if isinstance(update_result, SuccessfulChange):
                updated.append(result_dict)
            else:
                failed.append(result_dict)

        return {
            "updated": updated,
            "failed": failed
        }


updater = XproUpdater(
    result_file_settings=update_lib.get_xpro_username_change_settings()
)
result_filename, result_dict = updater.perform_updates_and_handle_results()

# Write the results to stdout
sys.stdout.write(json.dumps({
    "result_file": result_filename or "(Result file not written)",
    "results": result_dict
}))

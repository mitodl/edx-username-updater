import sys
import json

from django.contrib.auth import get_user_model
from django.db import transaction
from social_django.models import UserSocialAuth

from student.forms import validate_username

import username_update_lib as update_lib


User = get_user_model()


class EdxUsernameUpdater(update_lib.Updater):
    def perform_username_updates(self, username_update_list):
        updated = []
        not_found = []
        failed = []

        for username_update_dict in username_update_list:
            old_username = username_update_dict["old_username"]
            new_username = username_update_dict["new_username"]
            try:
                validate_username(new_username)
                with transaction.atomic():
                    update_count = User.objects.filter(username=old_username).update(username=new_username)
                    if update_count > 0:
                        UserSocialAuth.objects.filter(uid=old_username).update(uid=new_username)
            except Exception as exc:
                failed.append({
                    "old_username": old_username,
                    "new_username": new_username,
                    "exception": str(exc)
                })
            else:
                if update_count == 0:
                    not_found.append(username_update_dict)
                else:
                    updated.append(username_update_dict)
        return {
            "updated": updated,
            "failed": failed,
            "not_found": not_found
        }


updater = EdxUsernameUpdater(
    result_file_settings=update_lib.get_edx_username_change_settings()
)
result_filename, result_dict = updater.perform_updates_and_handle_results()

# Write the results to stdout
sys.stdout.write(json.dumps({
    "result_file": result_filename or "(Result file not written)",
    "results": result_dict
}))

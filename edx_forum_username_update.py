import sys
import json

from django.contrib.auth import get_user_model

from student.models import CourseEnrollment
from openedx.core.djangoapps.django_comment_common.comment_client.utils import perform_request as perform_forum_request
from openedx.core.djangoapps.django_comment_common.comment_client.user import User as CommentUser
from openedx.core.djangoapps.django_comment_common.comment_clientlms.lib.comment_client.thread import Thread
from openedx.core.djangoapps.django_comment_common.comment_client.comment import Comment

import username_update_lib as update_lib

User = get_user_model()


COMMENT_TYPE = "comment"
THREAD_TYPE = "thread"


class UpdateFailedException(Exception):
    def __init__(self, url, new_username):
        self.url = url
        self.new_username = new_username

    def __str__(self):
        return "Username update failed (username update attempted: {}, url: {})".format(
            self.new_username,
            self.url,
        )


def get_enrolled_course_ids(user):
    return [
        unicode(enrollment.course_id)
        for enrollment in CourseEnrollment.enrollments_for_user(user)
        if enrollment.is_active is True
    ]


def get_authored_threads_and_comments(comment_user, course_ids):
    for course_id in course_ids:
        involved_threads = [
            Thread.find(id=thread["id"]).retrieve(with_responses=True, recursive=True, mark_as_read=False)
            for thread in Thread.search({"course_id": course_id, "user_id": comment_user.id}).collection
        ]
        for thread in involved_threads:
            if thread["user_id"] == comment_user.id:
                yield thread.to_dict()
            children_to_scan = thread["children"]
            while children_to_scan:
                child = children_to_scan.pop(0)
                children_to_scan.extend(child["children"])
                if child["user_id"] == comment_user.id:
                    yield child


def update_comment_user_username(comment_user, new_username):
    user_detail_url = comment_user.url_with_id(params={"id": comment_user.id})
    response_data = perform_forum_request(
        "put",
        user_detail_url,
        data_or_params={u"username": new_username},
    )
    if response_data[u"username"] != new_username:
        raise UpdateFailedException(url=user_detail_url, new_username=new_username)


def update_thread_username(thread_id, new_username):
    thread_detail_url = Thread.url_with_id(params={"id": thread_id})
    response_data = perform_forum_request(
        "put",
        thread_detail_url,
        data_or_params={u"username": new_username},
    )
    if response_data[u"username"] != new_username:
        raise UpdateFailedException(url=thread_detail_url, new_username=new_username)


def update_comment_username(comment_id, new_username):
    comment_detail_url = Comment.url_for_comments(params={"parent_id": comment_id})
    response_data = perform_forum_request(
        "put",
        comment_detail_url,
        data_or_params={u"username": new_username},
    )
    if response_data[u"username"] != new_username:
        raise UpdateFailedException(url=comment_detail_url, new_username=new_username)


class EdxUsernameUpdater(update_lib.Updater):
    def perform_username_updates(self, username_update_list):
        updated = []
        failed = []

        for username_update_dict in username_update_list:
            old_username = username_update_dict["old_username"]
            new_username = username_update_dict["new_username"]
            try:
                user = User.objects.get(username=new_username)
                comment_user = CommentUser.from_django_user(user)
                update_comment_user_username(comment_user, new_username)
                enrolled_course_ids = get_enrolled_course_ids(user)
                authored_items = get_authored_threads_and_comments(comment_user, enrolled_course_ids)
                update_count = 0
                for authored_item in authored_items:
                    item_id = authored_item["id"]
                    item_type = str(authored_item.get("type"))
                    if item_type == THREAD_TYPE:
                        update_thread_username(item_id, new_username)
                        update_count += 1
                    elif item_type == COMMENT_TYPE:
                        update_comment_username(item_id, new_username)
                        update_count += 1
                updated.append({
                    "old_username": old_username,
                    "new_username": new_username,
                    "updated_item_count": update_count,
                })
            except Exception as exc:
                failed.append({
                    "old_username": old_username,
                    "new_username": new_username,
                    "exception": str(exc)
                })
        return {
            "updated": updated,
            "failed": failed,
        }


updater = EdxUsernameUpdater(
    result_file_settings=update_lib.get_edx_forum_username_change_settings()
)
result_filename, result_dict = updater.perform_updates_and_handle_results()

# Write the results to stdout
sys.stdout.write(json.dumps({
    "result_file": result_filename or "(Result file not written)",
    "results": result_dict
}))

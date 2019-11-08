import os
import json
from collections import namedtuple
from datetime import datetime
import pytz

from django.core.files.base import ContentFile
from django.core.files.storage import DefaultStorage
from django.core.exceptions import ImproperlyConfigured


FILENAME_DATE_FORMAT = "%Y%m%d_%H%M%S"
XPRO_RESULT_JSON_FILENAME_BASE = "xpro_username_changes"
EDX_RESULT_JSON_FILENAME_BASE = "edx_username_changes"
FORUM_RESULT_JSON_FILENAME_BASE = "edx_forum_username_changes"

RESULT_JSON_DIR_PATH = os.getenv("RESULT_JSON_DIR_PATH", ".")
SKIP_USERNAME_JSON_FILE_WRITE = os.getenv("SKIP_USERNAME_JSON_FILE_WRITE", None)
USERNAMES_TO_REGENERATE = os.getenv("USERNAMES_TO_REGENERATE", "")

ResultFileSettings = namedtuple(
    "ResultFileSettings", "input_filename_env, input_json_env, input_filename_base, output_filename_base"
)


def get_xpro_username_change_settings():
    return ResultFileSettings(
        input_filename_env=None,
        input_json_env=None,
        input_filename_base=None,
        output_filename_base=XPRO_RESULT_JSON_FILENAME_BASE,
    )


def get_edx_username_change_settings():
    return ResultFileSettings(
        input_filename_env="XPRO_RESULT_JSON_FILENAME",
        input_json_env="XPRO_RESULT_JSON_VALUE",
        input_filename_base=XPRO_RESULT_JSON_FILENAME_BASE,
        output_filename_base=EDX_RESULT_JSON_FILENAME_BASE,
    )


def get_edx_forum_username_change_settings():
    return ResultFileSettings(
        input_filename_env="EDX_RESULT_JSON_FILENAME",
        input_json_env="EDX_RESULT_JSON_VALUE",
        input_filename_base=EDX_RESULT_JSON_FILENAME_BASE,
        output_filename_base=FORUM_RESULT_JSON_FILENAME_BASE,
    )


def join_path(*path_parts):
    stripped_path_parts = list(
        map(lambda part: part.strip("/"), path_parts)
    )
    return "/".join(stripped_path_parts)


def write_json_file(dirpath, filename, json_data):
    return DefaultStorage().save(
        join_path(dirpath, filename),
        ContentFile(json.dumps(json_data).encode("utf8"))
    )


class Updater:
    def __init__(self, result_file_settings):
        self.settings = result_file_settings

    def perform_username_updates(self, username_update_list):
        raise NotImplementedError

    def get_previous_result_data(self):
        storage = DefaultStorage()
        result_json_filename = os.getenv(self.settings.input_filename_env, None)
        result_json_value = (
            {} if result_json_filename else json.loads(os.getenv(self.settings.input_json_env, "{}"))
        )
        if not result_json_filename and not result_json_value:
            raise ImproperlyConfigured(
                "Either {} (result file path/name) or {} (raw JSON value) need to be set".format(
                    self.settings.input_filename_env,
                    self.settings.input_json_env
                )
            )
        # If the update JSON is specified in an env var instead of a file, return that right away
        if result_json_value and not result_json_filename:
            # If raw result output was provided, just return the "results" portion
            if "results" in result_json_value and "updated" in result_json_value["results"]:
                return result_json_value["results"]
            return result_json_value
        # Try to find the result at one of several paths based on the value of the filename env var
        possible_xpro_result_file_paths = [
            result_json_filename,
            join_path(RESULT_JSON_DIR_PATH, result_json_filename),
            join_path(
                RESULT_JSON_DIR_PATH,
                "{}.json".format(result_json_filename),
            ),
        ]
        for path in possible_xpro_result_file_paths:
            if storage.exists(path):
                with storage.open(path) as f:
                    # If the file is found, parse the JSON and return
                    return json.loads(f.read())
        raise ImproperlyConfigured(
            "Could not find an xPro result JSON file at any of these paths: {}\n(env var {}={})".format(
                str(possible_xpro_result_file_paths),
                self.settings.input_filename_env,
                result_json_filename,
            )
        )

    def write_result_file(self, result_dict, run_dt):
        # Write the results to a file (unless skipped)
        if not SKIP_USERNAME_JSON_FILE_WRITE:
            return write_json_file(
                RESULT_JSON_DIR_PATH,
                "{}_{}.json".format(
                    self.settings.output_filename_base,
                    run_dt.strftime(FILENAME_DATE_FORMAT)
                ),
                result_dict
            )
        return None

    def perform_updates_and_handle_results(self):
        result_dict = {}
        previous_step_update_results = {}
        if self.settings.input_filename_env:
            previous_step_update_results = self.get_previous_result_data()
            result_dict["previous_step_file"] = os.getenv(self.settings.input_filename_env, None)
            result_dict["previous_step_run_date"] = previous_step_update_results.get("run_date")
        now = datetime.now(tz=pytz.UTC)
        result_dict["run_date"] = now.isoformat()
        result_dict.update(
            self.perform_username_updates(
                username_update_list=previous_step_update_results.get("updated", None)
            )
        )
        result_filename = self.write_result_file(result_dict=result_dict, run_dt=now)
        return result_filename, result_dict

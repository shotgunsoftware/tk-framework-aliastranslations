# Copyright (c) 2024 Autodesk
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the ShotGrid Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the ShotGrid Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Autodesk.

import os
import shutil
import subprocess
import tempfile

import sgtk

from .settings import TranslatorSettings

logger = sgtk.platform.get_logger(__name__)


class Translator(object):
    """
    Python wrapper to run the Alias file translations inside and outside of Alias.

    .. note:: Because of license issue, only the WREF translation can be run outside of Alias.
    """

    def __init__(self, source_path, output_path):
        """
        Class constructor.

        :param source_path: Path to the file we want to translate
        :param output_path: Path to the translated file
        """

        self.source_path = source_path
        self.output_path = output_path

        self.translation_type = self._get_translation_type_from_output_path()
        self.translator_settings = TranslatorSettings(self.translation_type)

    @property
    def translator_path(self):
        """
        Path to the executable used to translate the source file
        """
        return self.translator_settings.get_translator_path()

    def add_extra_param(self, param_name, param_value):
        """
        Add an extra parameter to the translator command line

        :param param_name:  Name of the parameter
        :param param_value: Value of the parameter
        """

        self.translator_settings._extra_params.append("-{name}".format(name=param_name))
        if param_value:
            self.translator_settings._extra_params.append(
                "{value}".format(value=param_value)
            )

    def is_valid(self):
        """
        Check if it's possible or not to run the translation according to the current environment

        :returns: False if it's not possible to run the translation, True otherwise.
        """

        current_engine = sgtk.platform.current_engine()

        if (
            current_engine.name != "tk-alias"
            and self.translation_type != "wref"
            and not self.translator_settings.license_settings
        ):
            logger.warning(
                "Couldn't run translation of %s outside of Alias because of license issue"
                % self.translation_type
            )
            return False

        return True

    def execute(self):
        """Run the translation command in a subprocess and wait for command to complete."""

        if not self.translator_path:
            raise ValueError("Couldn't translate file: missing translator path")

        # if we try to translate a file to another format than wref outside of Alias, raise an error because of the
        # license issue
        if not self.is_valid():
            logger.warning("Couldn't translate file: invalid conditions")
            return

        if not os.path.exists(self.source_path):
            raise ValueError("Couldn't translate file: it doesn't exist on disk.")

        # be sure the destination folder is created
        current_engine = sgtk.platform.current_engine()
        current_engine.ensure_folder_exists(os.path.dirname(self.output_path))

        # create a temporary output path that is local to ensure the translator can perform
        # all necessary file I/O operations. the temp file will be copied to the desired
        # destination once the translation is complete
        with tempfile.TemporaryDirectory() as temp_dir:
            # the temporary output path for the translation
            temp_path = os.path.join(temp_dir, os.path.basename(self.output_path))

            # build the command line which will be used to do the translation
            cmd = [self.translator_path]

            # get the license settings
            cmd.append("-productKey")
            cmd.append(self.translator_settings.license_settings.get("product_key", ""))
            cmd.append("-productVersion")
            cmd.append(
                self.translator_settings.license_settings.get("product_version", "")
            )
            cmd.append("-productLicenseType")
            cmd.append(
                self.translator_settings.license_settings.get(
                    "product_license_type", ""
                )
            )
            cmd.append("-productLicensePath")
            cmd.append(
                self.translator_settings.license_settings.get(
                    "product_license_path", ""
                )
            )

            cmd.append("-i")
            cmd.append(self.source_path)
            cmd.append("-o")
            cmd.append(temp_path)

            if self.translator_settings.extra_params:
                cmd.extend(self.translator_settings.extra_params)

            # run the translation. note that command arguments are not quoted using shlex.quote
            # because the Alias translators do not support quoted arguments and can handle
            # spaces in the file paths
            logger.info("Running translation command: {}".format(" ".join(cmd)))
            subprocess.check_call(cmd, stderr=subprocess.STDOUT, shell=False)

            # copy the translated file from the temp location to the desired destination
            # before exiting this scope, else the temp directory and file will be deleted
            shutil.copyfile(temp_path, self.output_path)

    def _get_translation_type_from_output_path(self):
        """
        Get the translation type according to the translated file extension

        :return: The translation type as a string
        """

        _, ext = os.path.splitext(self.output_path)
        return ext[1:].lower()

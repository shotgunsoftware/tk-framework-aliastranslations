# Copyright (c) 2020 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.
import os
import sgtk
import subprocess

from .settings import TranslatorSettings

logger = sgtk.platform.get_logger(__name__)


class Translator(object):

    def __init__(self, source_path, output_path):
        """
        """

        self.source_path = source_path
        self.output_path = output_path

        self.translation_type = self._get_translation_type_from_output_path()
        self.translator_settings = TranslatorSettings(self.translation_type)

    @property
    def translator_path(self):
        """
        """
        return self.translator_settings.get_translator_path()

    def add_extra_param(self, param_name, param_value):
        """
        """

        self.translator_settings._extra_params.append("{-name}".format(name=param_name))
        self.translator_settings._extra_params.append("{value}".format(name=param_value))

    def is_valid(self):
        """
        """

        current_engine = sgtk.platform.current_engine()

        if current_engine.name != "tk-alias" and self.translation_type == "wref":
            logger.warning(
                "Couldn't run translation of %s outside of Alias because of license issue" % self.translation_type
            )
            return False

        return True

    def execute(self):
        """
        """

        current_engine = sgtk.platform.current_engine()

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
        current_engine.ensure_folder_exists(os.path.dirname(self.output_path))

        # build the commande line which will be used to do the translation
        cmd = [self.translator_path]
        if current_engine.name == "tk-alias":
            cmd.extend(self.translator_settings.get_license_settings())

        cmd.append("-i")
        cmd.append(self.source_path)
        cmd.append("-o")
        cmd.append(self.output_path)

        if self.translator_settings.extra_params:
            cmd.extend(self.translator_settings.extra_params)

        # finally run the translation
        subprocess.check_call(cmd, stderr=subprocess.STDOUT, shell=True)

    def _get_translation_type_from_output_path(self):
        """
        :return:
        """

        _, ext = os.path.splitext(self.output_path)
        return ext[1:].lower()
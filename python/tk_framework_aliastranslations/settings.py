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

logger = sgtk.platform.get_logger(__name__)


class TranslatorSettings(object):
    """
    Class object to store all the settings needed by the translation process
    """

    # list of executables we have to use in order to run translations according to the translated file type
    _EXEC_NAME_LIST = {
        "wref": "AlToRef.exe",
        "igs": "AliasToIges.exe",
        "catpart": "AlToC5.exe",
        "jt": "AlToJt.bat",
        "stp": "AliasToStep.exe",
    }

    # list of extra parameters we need to use in order to run translation correctly according to the type of file
    # we want to have
    _EXTRA_PARAMS_LIST = {
        "jt": [
            "-e1s",
            "-g",
            "-xk",
            "-s",
            "1.0000",
            "-u",
            "128",
            "-m0",
            "-ta",
            "-t",
            "0.100000",
            "-t1t",
            "0.250000",
            "-t2t",
            "1.000000",
            "-tl",
            "1",
        ]
    }

    def __init__(self, translation_type=None):
        """
        Class constructor.

        :param translation_type: Type of the translation we want to run. It should correspond to the extension of the
                                 file we want to get
        """

        self.translation_type = translation_type
        self._exec_name = (
            self._EXEC_NAME_LIST.get(self.translation_type)
            if self.translation_type
            else None
        )
        self._exec_path = None
        self._extra_params = (
            self._EXTRA_PARAMS_LIST.get(self.translation_type, [])
            if self.translation_type
            else []
        )

    @property
    def exec_name(self):
        """
        Name of the executable we have to use to run the translation
        """
        return self._exec_name

    @property
    def extra_params(self):
        """
        List of extra parameters which will be used by the translation process
        """
        return self._extra_params

    def get_translator_path(self):
        """
        Get the path to the translator according to Alias installation folder.
        If we run the translation directly inside Alias, its installation path will be used to find the translator.
        Otherwise, use the ShotGrid software entity to try to determine a valid Alias install.

        :returns: The path to the translator living in the Alias installation folder
        """

        if self._exec_path:
            return self._exec_path

        current_engine = sgtk.platform.current_engine()

        if not self.exec_name:
            return None

        # if we are running the translation directly inside Alias, we can use the Alias root path.
        # Otherwise, we have to use the software entity to try to determine the path to the Alias installation folder
        root_path = None
        if current_engine.name == "tk-alias":
            logger.debug("Running translation inside Alias...")
            root_path = current_engine.alias_bindir
        else:
            logger.debug("Running translation outside of Alias...")
            software_launcher = sgtk.platform.create_engine_launcher(
                current_engine.sgtk, current_engine.context, "tk-alias"
            )
            software_versions = software_launcher.scan_software()
            for s in software_versions:
                bin_folder_path = os.path.dirname(s.path)
                if os.path.exists(bin_folder_path):
                    root_path = bin_folder_path
                    break

        if not root_path:
            logger.warning("Couldn't find Alias installation folder")
            return None

        # try to find the executable path. Sometimes, depending the software version, the translators are not in the
        # same folder
        exec_path = os.path.join(root_path, "translators", self.exec_name)
        if not os.path.exists(exec_path):
            exec_path = os.path.join(root_path, self.exec_name)

        if not os.path.exists(exec_path):
            logger.warning("Couldn't find translator path in Alias installation folder")
            return None

        self._exec_path = exec_path

        return exec_path

    @staticmethod
    def get_license_settings():
        """
        Get all the license settings needed by the translator executable in order to be executed

        :return: A list containing all the license information
        """

        import alias_api

        current_engine = sgtk.platform.current_engine()

        if current_engine.name != "tk-alias":
            raise ValueError("Can't get license settings outside of Alias")

        alias_info = alias_api.get_product_information()

        license_settings = [
            "-productKey",
            alias_info.get("product_key"),
            "-productVersion",
            alias_info.get("product_version"),
            "-productLicenseType",
            alias_info.get("product_license_type"),
            "-productLicensePath",
            alias_info.get("product_license_path"),
        ]

        return license_settings

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


"""
EdfToAl - Convert Edf file to Alias Wire file
Usage:
    EdfToAl  -i <Edf file>  -o <Wire file>
    -i            Input Edf filename (must be specified)
    -o            Output Wire filename (if not specified, stdout is used)
    -g <on/off>   Import ICEM molecules as Alias Groups (on is default)
        where 0 off
            1 on
    -l <on/off>   Log results to file (off is default)
        where 0 off
            1 on
    -r <path>   Redirect logfile results to a new path
    -t          Append a .txt extension to the logfile
    -h            Display this help information, then exit
"""



class TranslatorSettings(object):
    """Class object to store all the settings needed by the translation process."""

    # Alias translator executable file names. A default is provided for each type of file, and
    # will be used unless an environment variable is specified to override it. The environment
    # variables to override are defined as the keys of the dictionary (other than "default").
    # For example, if a user has the environment variable 'ALIAS_CATIA5_EXPORT_ATF' set, then
    # the AliasToCatia5.exe translator will be used
    _EXEC_NAME_LIST = {
        "wref": {
            "default": "AlToRef.exe",
        },
        "igs": {
            "default": "AliasToIges.exe",
        },
        "catpart": {
            "default": "AlToC5.exe",
            "ALIAS_CATIA5_EXPORT_ATF": "AliasToCatia5.exe",
        },
        "jt": {
            "default": "AlToJt.bat",
            "ALIAS_JT_EXPORT_ATF": "AliasToJt.exe",
        },
        "stp": {
            "default": "AliasToStep.exe",
        },
    }
    TRANSLATORS = {
        "wire": _EXEC_NAME_LIST,
        "edf": {
            "wire": {
                "default": "AlToEdf.exe",
                "extra_params": [
                    "-g", "1",  # Import ICEM molecules as Alias Groups (on is default)
                    "-l", "1",  # Log results to file (off is default)
                    # "-r", "C:\\Users\\qa\\Desktop\\edf",  # Redirect logfile results to a new path
                    "-t",  # Append a .txt extension to the logfile
                ]
            }
        }
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

    def __init__(self, translation_type=None, input_type=None, output_type=None):
        """
        Class constructor.

        :param translation_type: Type of the translation we want to run. It should correspond
                                 to the extension of the file we want to get.
        :type translation_type: str
        """

        self.translation_type = translation_type
        self.input_type = input_type
        self.output_type = output_type

        if input_type and output_type:
            exec_options = self.TRANSLATORS.get(input_type, {}).get(output_type, {})
        else:
            # Old method
            exec_options = (
                self._EXEC_NAME_LIST.get(self.translation_type)
                if self.translation_type
                else {}
            )

        self._exec_name = None
        for option_name, option_value in exec_options.items():
            if option_name == "default":
                continue
            if option_name in os.environ:
                self._exec_name = option_value
                break
        if self._exec_name is None:
            self._exec_name = exec_options.get("default")

        self._exec_path = None

        # TODO put these in the TRANSLATORS dictionary
        self._extra_params = (
            self._EXTRA_PARAMS_LIST.get(self.translation_type, [])
            if self.translation_type
            else []
        )
        self._extra_params.extend(self.TRANSLATORS.get(self.input_type, {}).get(self.output_type, {}).get("extra_params", []))

        self.license_settings = self.__get_license_settings()

    # -------------------------------------------------------------------------------------------------------
    # Static methods
    # -------------------------------------------------------------------------------------------------------

    @staticmethod
    def __get_license_settings():
        """
        Get all the license settings needed by the translator executable in order to be executed

        :return: A list containing all the license information
        """

        # current_engine = sgtk.platform.current_engine()

        # if current_engine.name != "tk-alias":
        #     return {}

        # else:

        try:
            import alias_api
        except ModuleNotFoundError:
            return {}

        alias_info = alias_api.get_product_information()
        return {
            "product_key": alias_info.get("product_key"),
            "product_version": alias_info.get("product_version"),
            "product_license_type": alias_info.get("product_license_type"),
            "product_license_path": alias_info.get("product_license_path"),
        }

    # -------------------------------------------------------------------------------------------------------
    # Properties
    # -------------------------------------------------------------------------------------------------------

    @property
    def exec_name(self):
        """
        Name of the executable we have to use to run the translation"""
        return self._exec_name

    @property
    def extra_params(self):
        """Get the list of extra parameters which will be used by the translation process."""
        return self._extra_params

    # -------------------------------------------------------------------------------------------------------
    # Public methods
    # -------------------------------------------------------------------------------------------------------

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

    def get_translator_command(self, input_path, output_path):
        """Return the command to run the ATF translator."""

        # build the command line which will be used to do the translation
        translator_path = self.get_translator_path()

        cmd = [translator_path]

        # get the license settings
        cmd.append("-productKey")
        cmd.append(self.license_settings.get("product_key", ""))
        cmd.append("-productVersion")
        cmd.append(
            self.license_settings.get("product_version", "")
        )
        cmd.append("-productLicenseType")
        cmd.append(
            self.license_settings.get(
                "product_license_type", ""
            )
        )
        cmd.append("-productLicensePath")
        cmd.append(
            self.license_settings.get(
                "product_license_path", ""
            )
        )

        cmd.append("-i")
        cmd.append(input_path)
        cmd.append("-o")
        cmd.append(output_path)

        if self.extra_params:
            cmd.extend(self.extra_params) 
        
        return cmd

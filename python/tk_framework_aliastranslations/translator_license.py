# Copyright (c) 2026 Autodesk
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the ShotGrid Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the ShotGrid Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Autodesk.

import os

import sgtk

# Alias 2027.1+ translators use product key/version only (no license type/path flags).
_NEW_TRANSLATOR_LICENSE_CLI_MIN_ALIAS_VERSION = "2027.1"

_LICENSE_SETTING_KEYS = (
    "product_key",
    "product_version",
    "product_license_type",
    "product_license_path",
)


def _version_component(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _version_cmp(version1, version2):
    """
    Compare dotted Alias version strings (same semantics as tk-framework-alias utils).

    :returns: 1 if version1 > version2, -1 if version1 < version2, else 0.
    :rtype: int
    """
    arr1 = [_version_component(part) for part in str(version1).split(".")]
    arr2 = [_version_component(part) for part in str(version2).split(".")]
    length = max(len(arr1), len(arr2))
    arr1.extend([0] * (length - len(arr1)))
    arr2.extend([0] * (length - len(arr2)))
    for left, right in zip(arr1, arr2):
        if left > right:
            return 1
        if right > left:
            return -1
    return 0


def normalize_license_settings(license_settings):
    """
    Return license settings with string values for translator command lines.

    :param license_settings: Raw license settings, e.g. from get_product_information().
    :type license_settings: dict

    :rtype: dict
    """
    if not license_settings:
        license_settings = {}

    normalized = dict(license_settings)
    for key in _LICENSE_SETTING_KEYS:
        normalized[key] = normalized.get(key) or ""
    return normalized


def _release_version_candidates(license_settings=None):
    """
    Collect Alias release strings used to choose translator licensing CLI options.

    ``engine.alias_version`` (e.g. ``2027.1`` from AboutBox) can differ from
    ``product_version`` (e.g. ``2027.0.0.F`` from ``AlProduct.full_version``).
    """
    license_settings = license_settings or {}
    candidates = []

    try:
        engine = sgtk.platform.current_engine()
    except Exception:
        engine = None

    if engine and engine.name == "tk-alias":
        alias_version = getattr(engine, "alias_version", None)
        if alias_version:
            candidates.append(str(alias_version).strip().split()[0])

    product_version = license_settings.get("product_version")
    if product_version:
        parts = str(product_version).split(".")
        if len(parts) >= 2:
            candidates.append(".".join(parts[:2]))
        if len(parts) >= 3:
            candidates.append(".".join(parts[:3]))

    return candidates


def uses_legacy_translator_license_cli(license_settings=None):
    """
    Return True when translator commands need ``-productLicenseType`` and ``-productLicensePath``.

    Legacy CLI is used only when every known release is older than Alias 2027.1.
    If ``engine.alias_version`` is 2027.1 but ``product_version`` is still 2027.0.x,
    the modern CLI is selected.
    """
    candidates = _release_version_candidates(license_settings)
    if not candidates:
        return True

    return all(
        _version_cmp(candidate, _NEW_TRANSLATOR_LICENSE_CLI_MIN_ALIAS_VERSION) < 0
        for candidate in candidates
    )


def uses_translator_license_type(license_settings=None):
    """Return True when translator commands must include ``-productLicenseType``."""
    return uses_legacy_translator_license_cli(license_settings)


def supplement_license_settings(license_settings):
    """
    Fill missing license fields from the environment or Alias install layout.

    License type fallbacks apply only when ``-productLicenseType`` is used (Alias < 2027.1).
    """
    settings = normalize_license_settings(license_settings)

    if uses_legacy_translator_license_cli(settings) and not settings["product_license_type"]:
        settings["product_license_type"] = (
            os.environ.get("ALIAS_PRODUCT_LIC_TYPE")
            or os.environ.get("ALIAS_PRODUCT_LICENSE_TYPE")
            or ""
        )

    if uses_legacy_translator_license_cli(settings):
        if not settings["product_license_path"]:
            settings["product_license_path"] = (
                os.environ.get("ALIAS_PRODUCT_LIC_PATH")
                or os.environ.get("ALIAS_PRODUCT_LICENSE_PATH")
                or ""
            )

        if not settings["product_license_path"]:
            try:
                engine = sgtk.platform.current_engine()
            except Exception:
                engine = None
            if engine and engine.name == "tk-alias":
                bindir = getattr(engine, "alias_bindir", None)
                if bindir:
                    settings["product_license_path"] = os.path.join(
                        os.path.dirname(bindir),
                        "AutoStudio",
                        "LICPATH.LIC",
                    )

    return settings


def append_license_arguments(cmd, license_settings):
    """
    Append product licensing arguments to a translator command line.

    :param cmd: Command argument list being built for subprocess.
    :type cmd: list
    :param license_settings: License settings dictionary.
    :type license_settings: dict
    """
    settings = supplement_license_settings(license_settings)

    cmd.append("-productKey")
    cmd.append(settings["product_key"])
    cmd.append("-productVersion")
    cmd.append(settings["product_version"])
    if uses_legacy_translator_license_cli(settings):
        cmd.append("-productLicenseType")
        cmd.append(settings["product_license_type"])
        cmd.append("-productLicensePath")
        cmd.append(settings["product_license_path"])

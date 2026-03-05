"""LookFileMaterialsAdd Node."""

from .Node import LookFileMaterialsAdd  # noqa


def GetEditor():  # noqa
    """Return the editor widget for the node."""

    from .Editor import LookFileMaterialsAddEditor

    return LookFileMaterialsAddEditor

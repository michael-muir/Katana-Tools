"""LookFileMaterialsAdd Upgrade."""

from __future__ import print_function

from Katana import Utils  # noqa

__all__ = ["Upgrade"]


def Upgrade(node):  # noqa
    """Upgrade the given node if it is out of date."""

    Utils.UndoStack.DisableCapture()
    try:
        pass
    except:  # noqa
        import traceback

        traceback.print_exc()
        print("Cannot upgrade LookFileMaterialsAdd node.")
    finally:
        Utils.UndoStack.EnableCapture()

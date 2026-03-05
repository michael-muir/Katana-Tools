"""LookFileMaterialsAdd2 Node.

This supertool reads the lookfiles from a list of assets defined by a CEL and loads their and
assigns their lookfile materials back onto the same components mimicing the behavior of
loading a lookfile into a LookFileManager - but without all the lookfile attributes.
"""

from .v1.Node import LookFileMaterialsAdd2


def GetEditor():
    """Get the LookFileMaterialsAdd2 node editor."""
    from .v1.Editor import LookFileMaterialsAdd2Editor

    return LookFileMaterialsAdd2Editor


PluginRegistry = [
    ("SuperTool", 2, "LookFileMaterialsAdd2", (LookFileMaterialsAdd2, GetEditor)),
]

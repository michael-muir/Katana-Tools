"""LookFileMaterialsAdd Config."""

from pathlib import Path

CURRENT_DIRECTORY = Path(__file__).resolve().parent

# fmt: off

ADD_BUTTON_SCRIPT = f"""\
with open('{CURRENT_DIRECTORY}/scripts/add_button.py') as file:
    exec(file.read())
"""

APPLY_OPSCRIPT = """\
location = Interface.GetOutputLocationPath()
mtlAssignAttr = Interface.GetAttr("materialAssign", location, 1)

if mtlAssignAttr then
    mtlAssign = mtlAssignAttr:getValue()
    Interface.SetAttr("materialAssign", StringAttribute(mtlAssign))
    Interface.DeleteAttr("material")
end
"""

RESET_OPSCRIPT = """\
resolvedAssetAttr = Interface.GetAttr('lookfile.resolvedAsset')

if resolvedAssetAttr then
    Interface.SetAttr('lookfile.asset', StringAttribute(resolvedAssetAttr:getValue()))
    Interface.DeleteAttr('lookfile.resolvedAsset')
    Interface.DeleteAttr('lookfile.resolvedPass')
end
"""

# fmt: on

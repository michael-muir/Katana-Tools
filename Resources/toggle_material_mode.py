"""
NAME: Material Action Change (Edit/Override)
ICON: icon.png
KEYBOARD_SHORTCUT:
SCOPE: Material

Coverts Material Edits/Overrides to Overrides/Edits.

"""

from Katana import Nodes3DAPI, NodegraphAPI, Utils, Widgets, KatanaFile

# ------------------------------------------------------------------------------
# Utility Helpers
# ------------------------------------------------------------------------------

def _attr_value(producer, attr_name):
    try:
        attr = producer.getAttribute(attr_name)
        return attr.getValue() if attr else None
    except Exception:
        return None


def _get_child(param, name):
    return param.getChild(name) if param else None


def _ensure_group(parent, name):
    group = parent.getChild(name)
    return group if group else parent.createChildGroup(name)


# ------------------------------------------------------------------------------
# CEL Utilities
# ------------------------------------------------------------------------------

def build_cel_for_material_override(node, material_path, start_path="/root/world/geo"):
    producer = Nodes3DAPI.GetGeometryProducer(node)
    root = producer.getProducerByPath(start_path)

    if not root:
        print("Invalid start path:", start_path)
        return ""

    results = []

    def _recurse(prod):
        assigned = _attr_value(prod, "materialAssign")
        if assigned == material_path:
            results.append(prod.getFullName())

        for child in prod.iterChildren():
            _recurse(child)

    _recurse(root)

    return f"({' '.join(results)})" if results else ""


def get_material_assigns_from_cel(node, cel, root_location="/root"):
    collector = Widgets.CollectAndSelectInScenegraph(cel, root_location)
    matches = collector.collectAndSelect(select=False, node=node)

    producer = Nodes3DAPI.GetGeometryProducer(node)
    results = []

    for path in matches:
        prod = producer.getProducerByPath(path)
        if not prod:
            continue

        val = _attr_value(prod, "materialAssign")
        if val:
            results.append(val)

    return sorted(set(results))


# ------------------------------------------------------------------------------
# Parameter Copy Helpers
# ------------------------------------------------------------------------------

def _is_enabled(param):
    enable = _get_child(param, "enable")
    return enable and enable.getValue(0) == 1


def _get_value_and_type(param):
    value = _get_child(param, "value")
    ptype = _get_child(param, "type")
    return value, ptype


def _cleanup_param(param, names):
    for name in names:
        child = param.getChild(name)
        if child:
            param.deleteChild(child)


# ------------------------------------------------------------------------------
# Conversion: Override → Edit
# ------------------------------------------------------------------------------

def convert_material_override_to_edit(node):
    if node.getType() != "Material":
        raise RuntimeError("Node must be a Material node")

    params = node.getParameters()
    action_param = _get_child(params, "action")

    if not action_param or action_param.getValue(0) != "override materials":
        print("Skipping (not override):", node.getName())
        return

    print("Converting:", node.getName(), "MaterialOverride → MaterialEdit")

    shaders = _get_child(params, "shaders")
    edit_params = _get_child(shaders, "parameters")

    overrides = _get_child(params, "overrides")
    attrs = _get_child(overrides, "attrs")
    override_params = _ensure_group(attrs, "materialOverride")

    if not (shaders and edit_params and overrides and attrs):
        print("Missing required parameter structure")
        return

    # Copy parameters
    for param in override_params.getChildren():
        if not _is_enabled(param):
            continue

        value, ptype = _get_value_and_type(param)
        if not (value and ptype):
            continue

        name = param.getName().replace("parameters___", "")
        new_param = _get_child(edit_params, name) or edit_params.createChildGroup(name)

        new_param.parseXML(param.getXML())
        _cleanup_param(new_param, ["isDynamicArray", "default", "__path", "__hints"])

    # Cleanup override params
    for child in override_params.getChildren():
        override_params.deleteChild(child)

    # Switch mode
    action_param.setValue("edit material", 0)

    _rename_node(node, to_edit=True)

    # Set edit locations
    cel = node.getParameter('overrides.CEL').getValue(0)
    mtl_assigns = get_material_assigns_from_cel(node, cel)

    if not mtl_assigns:
        print("Done:", node.getName())
        return

    node.getParameter('edit.location').setValue(mtl_assigns[0], 0)

    if len(mtl_assigns) > 1:
        _duplicate_nodes_for_materials(node, mtl_assigns)

    print("Done:", node.getName())


# ------------------------------------------------------------------------------
# Conversion: Edit → Override
# ------------------------------------------------------------------------------

def convert_material_edit_to_override(node):
    if node.getType() != "Material":
        raise RuntimeError("Node must be a Material node")

    params = node.getParameters()
    action_param = _get_child(params, "action")

    if not action_param or action_param.getValue(0) != "edit material":
        print("Skipping (not edit):", node.getName())
        return

    print("Converting:", node.getName(), "MaterialEdit → MaterialOverride")

    shaders = _get_child(params, "shaders")
    edit_params = _get_child(shaders, "parameters")

    overrides = _get_child(params, "overrides")
    attrs = _get_child(overrides, "attrs")
    override_params = _ensure_group(attrs, "materialOverride")

    if not (shaders and edit_params and overrides and attrs):
        print("Missing required parameter structure")
        return

    # Copy parameters
    for param in edit_params.getChildren():
        if not _is_enabled(param):
            continue

        value, ptype = _get_value_and_type(param)
        if not (value and ptype):
            continue

        name = param.getName()
        new_param = override_params.createChildGroup(f"parameters___{name}")
        new_param.parseXML(param.getXML())

        new_param.createChildString("__path", f"parameters.{name}")

        if value.getTupleSize() == 3 and ptype.getValue(0) == 'FloatAttr':
            new_param.createChildString("__hints", '{"widget":"color","panelWidget":"color"}')

        # Disable edit param
        param.getChild("enable").setValue(0, 0)

    # Switch mode
    action_param.setValue("override materials", 0)

    _rename_node(node, to_edit=False)

    # Build CEL
    material_path = node.getParameter('edit.location').getValue(0)
    cel = build_cel_for_material_override(node, material_path)

    if cel:
        node.getParameter('overrides.CEL').setValue(cel, 0)

    print("Done:", node.getName())


# ------------------------------------------------------------------------------
# Node Utilities
# ------------------------------------------------------------------------------

def _rename_node(node, to_edit=True):
    name = node.getParameter('name').getValue(0)

    if to_edit:
        newname = (name.replace('MO_', 'ME_')
                        .replace('MaterialOverride_', 'MaterialEdit_')
                        .replace('mo_', 'me_')
                        .replace('override_', 'edit_'))
    else:
        newname = (name.replace('ME_', 'MO_')
                        .replace('MaterialEdit_', 'MaterialOverride_')
                        .replace('me_', 'mo_')
                        .replace('edit_', 'override_'))

    node.setName(newname)
    node.getParameter('name').setValue(newname, 0)


def _duplicate_nodes_for_materials(node, material_paths):
    offset = 50
    node_xml = NodegraphAPI.BuildNodesXmlIO([node])
    parent = node.getParent()
    pos = NodegraphAPI.GetNodePosition(node)

    base_name = node.getName()
    first_name = material_paths[0].split('/')[-1]

    oport = node.getOutputPortByIndex(0)

    for i, path in enumerate(material_paths[1:], start=1):
        copied = KatanaFile.Paste(node_xml, parent)[0]
        copied.getParameter('edit.location').setValue(path, 0)

        mat_name = path.split('/')[-1]

        if first_name in base_name:
            newname = base_name.replace(first_name, mat_name)
        else:
            newname = f"ME_{mat_name}"

        copied.setName(newname)
        copied.getParameter('name').setValue(newname, 0)

        copied.getInputPortByIndex(0).connect(oport)
        oport = copied.getOutputPortByIndex(0)

        NodegraphAPI.SetNodePosition(
            copied,
            (pos[0] + 200, pos[1] - ((i - 1) * offset))
        )


# ------------------------------------------------------------------------------
# Entry Point
# ------------------------------------------------------------------------------

def convert_selected_materials():
    for node in NodegraphAPI.GetAllEditedNodes():
        if node.getType() != "Material":
            continue

        action = _get_child(node.getParameters(), "action")
        if not action:
            continue

        value = action.getValue(0)

        if value == "edit material":
            convert_material_edit_to_override(node)
        elif value == "override materials":
            convert_material_override_to_edit(node)


# ------------------------------------------------------------------------------
# Run
# ------------------------------------------------------------------------------

Utils.UndoStack.OpenGroup("Material Action Change (Edit/Override)")
try:
    convert_selected_materials()
finally:
    Utils.UndoStack.CloseGroup()

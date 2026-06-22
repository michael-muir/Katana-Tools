"""
NAME: Toggle Material Mode (Edit/Override)
SCOPE: Material
"""

from Katana import Nodes3DAPI, NodegraphAPI, Utils, Widgets

def build_cel_for_material_override(node, material_path, start_path="/root/world/geo"):
    results = []

    producer = Nodes3DAPI.GetGeometryProducer(node)

    # Get the starting location producer
    sgProducer = producer.getProducerByPath(start_path)
    if not sgProducer:
        print("Invalid start path:", start_path)
        return ""

    def recurse(prod):
        try:
            attr = prod.getAttribute("materialAssign")
            if attr:
                assigned = attr.getValue()
                if assigned == material_path:
                    results.append(prod.getFullName())
        except:
            pass

        for child in prod.iterChildren():
            recurse(child)

    recurse(sgProducer)

    # Build CEL string
    if not results:
        return ""

    # Space-separated paths wrapped in parentheses (CEL union)
    cel = "(" + " ".join(results) + ")"
    return cel


def get_material_assigns_from_cel(node, cel, root_location="/root"):
    """
    Evaluate a CEL, collect matching scene graph locations,
    then inspect each for materialAssign.

    Args:
        node: Katana node (typically view node)
        cel: CEL string
        root_location: root to evaluate CEL from

    Returns:
        List of unique materialAssign paths
    """

    results = []

    # Evaluate CEL → list of matching locations
    collector = Widgets.CollectAndSelectInScenegraph(cel, root_location)
    matches = collector.collectAndSelect(select=False, node=node)

    # Get geometry producer for attribute lookup
    producer = Nodes3DAPI.GetGeometryProducer(node)

    for path in matches:
        try:
            prod = producer.getProducerByPath(path)
            if not prod:
                continue

            attr = prod.getAttribute("materialAssign")
            if attr:
                val = attr.getValue()
                if val:
                    results.append(val)
        except:
            pass

    # Deduplicate + stable order
    return sorted(set(results))


def convert_material_override_to_edit(node):

    if node.getType() != "Material":
        raise RuntimeError("Node must be a Material node")

    params = node.getParameters()

    action_param = params.getChild("action")
    if not action_param or action_param.getValue(0) != "override materials":
        print("Skipping (not override):", node.getName())
        return

    print("Converting:", node.getName(), "from from MaterialOverride to MaterialEdit")

    # --- SOURCE (EDIT STRUCTURE) ---
    shaders_group = params.getChild("shaders")
    if not shaders_group:
        print("No shaders group found")
        return

    shader_name_param = shaders_group.getChild("__lastValue")
    if not shader_name_param:
        print("No shader name found")
        return

    shader_name = shader_name_param.getValue(0)

    edit_params = shaders_group.getChild("parameters")
    if not edit_params:
        print("No shader parameters found")
        return

    # --- DESTINATION (OVERRIDE STRUCTURE) ---
    overrides_group = params.getChild("overrides")
    if not overrides_group:
        print("No overrides group found")
        return

    attrs = overrides_group.getChild('attrs')
    if not attrs:
        print("No override attrs found")
        return

    override_params = attrs.getChild("materialOverride")
    if not override_params:
        override_params = attrs.createChildGroup("materialOverride")

    # --- COPY PARAMETERS ---
    for param in override_params.getChildren():
        name = param.getName()
        name = name.replace("parameters___", "")

        enable = param.getChild("enable")

        # enable
        if not enable or enable.getValue(0) != 1:
            continue

        value = param.getChild("value")
        ptype = param.getChild("type")

        if not value or not ptype:
                continue

        new_type = ptype.getValue(0)

        # --- CREATE GROUP ---
        new_param = edit_params.getChild(name)
        if not new_param:
            new_param = edit_params.createChildGroup(name)

        new_param.parseXML(param.getXML())

        # delete extra junk
        for childname in ['isDynamicArray', 'default', '__path', '__hints']:
            child = new_param.getChild(childname)
            if child:
                new_param.deleteChild(child)

    # --- CLEANUP OVERRIDES ---
    for child in override_params.getChildren():
        override_params.deleteChild(child)

    # --- SWITCH MODE ---
    action_param.setValue("edit material", 0)

    # --- MODIFY NODE NAME ---
    newname = node.getParameter('name').getValue(0).replace('MO_', 'ME_').replace('MaterialOverride_', 'MaterialEdit_')
    newname = newname.replace('mo_', 'me_').replace('override_', 'edit_')
    node.setName(newname)
    node.getParameter('name').setValue(newname, 0)

    # --- SET EDIT LOCATIONS ---
    CEL = node.getParameter('overrides.CEL').getValue(0)
    mtl_assigns = get_material_assigns_from_cel(node, CEL)
    if len(mtl_assigns) > 0:
        node.getParameter('edit.location').setValue(mtl_assigns[0], 0)

    if len(mtl_assigns) > 1:
        offset = 50
        node_xml = NodegraphAPI.BuildNodesXmlIO([node])
        parent = node.getParent()
        pos = NodegraphAPI.GetNodePosition(node)
        mtl_name = mtl_assigns[0].split('/')[-1]
        oport = node.getOutputPortByIndex(0)
        for i in range(1, len(mtl_assigns)):
            copied_node = KatanaFile.Paste(node_xml, parent)[0]
            copied_node.getParameter('edit.location').setValue(mtl_assigns[i], 0)
            aux_name = mtl_assigns[i].split('/')[-1]
            if mtl_name in newname:
                node_name = newname.replace(mtl_name, aux_name)
            else:
                node_name = 'ME_' + aux_name

            copied_node.getParameter('name').setValue(node_name, 0)
            copied_node.setName(node_name)
            copied_node.getInputPortByIndex(0).connect(oport)
            oport = copied_node.getOutputPortByIndex(0)
            NodegraphAPI.SetNodePosition(copied_node, (pos[0] + 200, pos[1] - ((i-1)*offset)))

    print("Done:", node.getName())


def convert_material_edit_to_override(node):

    if node.getType() != "Material":
        raise RuntimeError("Node must be a Material node")

    params = node.getParameters()

    action_param = params.getChild("action")
    if not action_param or action_param.getValue(0) != "edit material":
        print("Skipping (not edit):", node.getName())
        return

    print("Converting:", node.getName(), "from from MaterialEdit to MaterialOverride")

    # --- SOURCE (EDIT STRUCTURE) ---
    shaders_group = params.getChild("shaders")
    if not shaders_group:
        print("No shaders group found")
        return

    shader_name_param = shaders_group.getChild("__lastValue")
    if not shader_name_param:
        print("No shader name found")
        return

    shader_name = shader_name_param.getValue(0)

    edit_params = shaders_group.getChild("parameters")
    if not edit_params:
        print("No shader parameters found")
        return

    # --- DESTINATION (OVERRIDE STRUCTURE) ---
    overrides_group = params.getChild("overrides")
    if not overrides_group:
        print("No overrides group found")
        return

    attrs = overrides_group.getChild('attrs')
    if not attrs:
        print("No override attrs found")
        return

    override_params = attrs.getChild("materialOverride")
    if not override_params:
        override_params = attrs.createChildGroup("materialOverride")

    # --- COPY PARAMETERS ---
    for param in edit_params.getChildren():
        name = param.getName()

        enable = param.getChild("enable")

        # enable
        if not enable or enable.getValue(0) != 1:
            continue

        value = param.getChild("value")
        ptype = param.getChild("type")

        if not value or not ptype:
                continue

        new_type = ptype.getValue(0)

        # --- CREATE GROUP ---
        new_param = override_params.createChildGroup("parameters___" + name)

        new_param.parseXML(param.getXML())

        new_path = new_param.createChildString("__path", "parameters." + name )
        if value.getTupleSize() == 3 and new_type == 'FloatAttr':
            # assume it is a color
            new_hints = new_param.createChildString("__hints", '{"widget":"color", "panelWidget":"color"}')


        # --- CLEANUP - DISABLE EDIT PARAMETER ---
        enable.setValue(0, 0)

    # --- SWITCH MODE ---
    action_param.setValue("override materials", 0)

    # --- MODIFY NODE NAME ---
    newname = node.getParameter('name').getValue(0).replace('ME_', 'MO_').replace('MaterialEdit_', 'MaterialOverride_')
    newname = newname.replace('me_', 'mo_').replace('edit_', 'override_')
    node.setName(newname)
    node.getParameter('name').setValue(newname, 0)

    # --- SET OVERRIDES CEL ---
    material_path = node.getParameter('edit.location').getValue(0)
    CEL = build_cel_for_material_override(node, material_path)
    if len(CEL) > 0:
        node.getParameter('overrides.CEL').setValue(CEL, 0)

    print("Done:", node.getName())


def convert_selected_materials():
    for node in NodegraphAPI.GetAllEditedNodes():
        if node.getType() == "Material":
            params = node.getParameters()
            action_param = params.getChild("action")

            if action_param and action_param.getValue(0) == "edit material":
                convert_material_edit_to_override(node)
            elif action_param and action_param.getValue(0) == "override materials":
                convert_material_override_to_edit(node)


# Run
Utils.UndoStack.OpenGroup("Toggle Material Mode")
try:
    convert_selected_materials()
finally:
    Utils.UndoStack.CloseGroup()

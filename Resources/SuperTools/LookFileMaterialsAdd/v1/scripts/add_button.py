"""add_button.py"""

from pathlib import Path

from Katana import FnGeolib, GeoAPI, Nodes3DAPI

try:
    from PySide2 import QtWidgets
except ImportError:
    from PySide import QtGui as QtWidgets


# ------------------------------------------------------------
# Function to find lookfile materials loading path(s)
# ------------------------------------------------------------
def capture_mtl_load_path(producer):
    """returns a lookfile material with with the version in it."""
    locations = []

    import re

    ENDS_WITH_VERSION_DIR = re.compile(r"(?:^|[\\/])(?:_\d{3}|latest)$")

    def recurse(p):
        #        if not p:
        #            return

        full_path = p.getFullName()
        if bool(ENDS_WITH_VERSION_DIR.search(full_path)):
            locations.append(full_path)
        else:
            for child in p.iterChildren():
                recurse(child)

    recurse(producer)
    return locations


# ------------------------------------------------------------
# Check
# ------------------------------------------------------------
iport = node.getInputPortByIndex(0)  # noqa

if iport.getNumConnectedPorts() == 0:
    QtWidgets.QMessageBox.warning(
        None, "Collect components", "Please connect the node to node graph."
    )
    raise RuntimeError("Node disconnected")


# ------------------------------------------------------------
# Read CEL
# ------------------------------------------------------------

assetsParam = node.getParameter("assets")  # noqa
if assetsParam is None:
    raise RuntimeError("assets parameter not found")


cel = assetsParam.getValue(0).strip()
if not cel:
    QtWidgets.QMessageBox.warning(None, "Collect components", "The assets CEL is empty.")
    raise RuntimeError("Empty CEL")


# ------------------------------------------------------------
# Collect scene graph locations at this node
# ------------------------------------------------------------

runtime = FnGeolib.GetRegisteredRuntimeInstance()
txn = runtime.createTransaction()
client = txn.createClient()
op = Nodes3DAPI.GetOp(txn, node)  # noqa
txn.setClientOp(client, op)
runtime.commit(txn)

producer = Nodes3DAPI.GetGeometryProducer(node, graphState=None, portIndex=0)  # noqa
locations = GeoAPI.Util.CollectPathsFromCELStatement(producer, cel, interruptCallback=None)

if not locations:
    QtWidgets.QMessageBox.warning(
        None, "Collect components", "The assets CEL did not match any scene graph locations."
    )
    raise RuntimeError("No locations found")


# ------------------------------------------------------------
# Validate type == component
# ------------------------------------------------------------

nonComponents = []

for loc in locations:
    sgLocation = producer.getProducerByPath(loc)
    typeAttr = sgLocation.getAttribute("type")
    locType = None

    if typeAttr is not None:
        locType = typeAttr.getValue()

    if locType != "component":
        nonComponents.append(loc)

if nonComponents:
    QtWidgets.QMessageBox.warning(
        None,
        "Collect components",
        "The following locations are not of type 'component':\\n\\n" + "\\n".join(nonComponents),
    )
    # stop execution
    raise RuntimeError("Non-component locations found")

node.getParameter("watch_list").setValue(str(locations), 0)  # noqa


# ------------------------------------------------------------
# Build lookfile dictionary
# ------------------------------------------------------------

lookfileDict = {}

for loc in locations:
    sgLocation = producer.getProducerByPath(loc)
    attr = sgLocation.getAttribute("lookfile.asset")
    if attr is None:
        attr = sgLocation.getAttribute("lookfile.resolvedAsset")

    if attr is None:
        # silently ignore locations without a lookfile
        continue

    try:
        value = attr.getValue()
    except Exception:
        continue

    if not value:
        continue

    lookfileDict.setdefault(value, []).append(loc)


# ------------------------------------------------------------
# Find the internal nodes that need updated
# ------------------------------------------------------------

enableGroupMerge = None
hierarchyCopyStack = None
resetOp = None
applyOp = None

for child in node.getChildren():  # noqa
    if child.getName().startswith("LookFileOverrideEnable_GroupMerge"):
        enableGroupMerge = child
    if child.getName().startswith("HierarchyCopy_Stack"):
        hierarchyCopyStack = child
    if child.getName().startswith("OP_Reset_LookFile_State"):
        resetOp = child
    if child.getName().startswith("OP_Apply_LookFile_Mtls"):
        applyOp = child

if enableGroupMerge is None or hierarchyCopyStack is None or resetOp is None or applyOp is None:
    raise RuntimeError("Could not find internal nodes required to proceed.")

# ------------------------------------------------------------
# Delete All Child Nodes in Group Stacks
# ------------------------------------------------------------

lfNodes = enableGroupMerge.getChildNodes()
for lfNode in lfNodes:
    enableGroupMerge.deleteChildNode(lfNode)

hcNodes = hierarchyCopyStack.getChildNodes()
for hcNode in hcNodes:
    hierarchyCopyStack.deleteChildNode(hcNode)


# ------------------------------------------------------------
# Create LookFileOverrideEnable nodes
# ------------------------------------------------------------

overrideEnableNodes = []

for lookfile in sorted(lookfileDict.keys()):
    lfNode = enableGroupMerge.buildChildNode()
    lfNode.getParameter("lookfile").setValue(lookfile, 0)
    overrideEnableNodes.append(lfNode)


# ------------------------------------------------------------
# Build HierarchyCopy nodes to remap material paths to current
# ------------------------------------------------------------

for overrideNode in overrideEnableNodes:
    node_producer = Nodes3DAPI.GetGeometryProducer(overrideNode, graphState=None, portIndex=0)
    paths = capture_mtl_load_path(node_producer)

    if len(paths) > 0:
        source = paths[0]
        p = Path(source)

        hcNode = hierarchyCopyStack.buildChildNode()
        hcNode.getParameter("pruneSource").setValue(1.0, 0)
        hcNode.getParameter("copies.copy1.sourceLocation").setValue(source, 0)
        hcNode.getParameter("copies.copy1.destinationLocations").getChildByIndex(0).setValue(
            str(p.with_name("current")), 0
        )

# ------------------------------------------------------------
# Build componentsCEL and Set CEL on resetOp
# ------------------------------------------------------------

# CEL list of the component locations
componentsCEL = " ".join(locations)
resetOp.getParameter("CEL").setValue(componentsCEL, 0)


# ------------------------------------------------------------
# Build searchCEL
# ------------------------------------------------------------

# Each location with //*
searchCEL = " ".join([loc + "//*" for loc in locations])
applyOp.getParameter("CEL").setValue(searchCEL, 0)


# ------------------------------------------------------------
# Update UI With LookFile info
# ------------------------------------------------------------

lparam = node.getParameter("loaded_lookfiles")  # noqa
if lparam != None:
    for child in lparam.getChildren():
        lparam.deleteChild(child)

    count = 0
    for lookfile in sorted(lookfileDict.keys()):
        locations = lookfileDict[lookfile]
        mylist = "<li>".join([""] + locations)
        helpString = "{'help':'Assigned scene graph locations:<p>%s'}" % (mylist)

        child = lparam.createChildString(f"lookfile_{count}", lookfile)
        child.setHintString(helpString)
        count = count + 1

    lparam.setHintString("{'open':True, 'readOnly':True}")

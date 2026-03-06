"""LookFileMaterialsAdd Node."""

from __future__ import print_function

import ast
import logging
from pathlib import Path
from typing import Callable

from Katana import Callbacks, FnGeolib, NodegraphAPI, Nodes3DAPI, Utils

from .Upgrade import Upgrade  # noqa

LOG = logging.getLogger("laika.LookFileMaterialsAdd")

X_SPACE = 200
Y_SPACE = 50

# fmt: off



CURRENT_DIRECTORY = Path(__file__).resolve().parent

ADD_BUTTON_SCRIPT = f"""\
with open('{CURRENT_DIRECTORY}/scripts/add_button.py') as file:
    exec(file.read())
"""

RESET_OPSCRIPT = """\
resolvedAssetAttr = Interface.GetAttr('lookfile.resolvedAsset')

if resolvedAssetAttr then
    Interface.SetAttr('lookfile.asset', StringAttribute(resolvedAssetAttr:getValue()))
    Interface.DeleteAttr('lookfile.resolvedAsset')
    Interface.DeleteAttr('lookfile.resolvedPass')
end
"""

APPLY_OPSCRIPT = """\
mode = Interface.GetOpArg('user.version_mode'):getValue()
location = Interface.GetOutputLocationPath()
mtlAssignAttr = Interface.GetAttr("materialAssign", location, 1)

if mtlAssignAttr then
    mtlAssign = mtlAssignAttr:getValue()
    if mode == 'current' then
        mtlAssign = mtlAssign:gsub("/_%d%d%d/", "/current/")
        mtlAssign = mtlAssign:gsub("/latest/", "/current/")
    end
    Interface.SetAttr("materialAssign", StringAttribute(mtlAssign))
    Interface.DeleteAttr("material")
end
"""


_PARAMETER_HINTS = {
    "LookFileMaterialsAdd.assets": {
        "help": "List of components (or assets) of which to load the lookfile materials from.",
        "widget": "cel",
    },
    "LookFileMaterialsAdd.version_mode": {
        "help": "Specifies what version of the lookfile to reference for the materials.  The \
        version mode becomes part of the lookfile material path. \
        <li><b>version</b> - loads the version specified by the asset bundle or user and \
        the loaded version is part of the lookfile material path(s).   This means that if the \
        version changes from an asset bundle update or a change from the user, there is a \
        potential for material edits to break because the klf material paths can change.\
        <li><b>current</b> - auto updates the lookfile version with any asset bundle updates, \
        while replacing the klf version in the material paths to 'current' so that the material \
        paths do not change from underneath.  This prevents material edits from breaking, as the \
        klf material path version is locked to 'current'.",
        "label": "version mode",
        "widget": "popup",
        "options": ['version', 'current'],
        "default": "current"
    },
    "LookFileMaterialsAdd.add_button": {
        "widget":"scriptButton",
        "buttonText":"Add LookFile Materials from Scene Graph Selection",
        "scriptText": ADD_BUTTON_SCRIPT
    },
    "LookFileMaterialsAdd.watch_list": {
        "label": "watch list",
        "conditionalVisOps":{'conditionalVisOp': 'equalTo',\
                             'conditionalVisValue': '-1',\
                             'conditionalVisPath': '../version_mode'},
    },
    "LookFileMaterialsAdd.loaded_lookfiles": {
        "help":"List of the currently loaded lookfiles.   The displayed lookfile paths in the \
        loaded_lookfiles section are not updated with the 'current' version tag, but are the \
        actual versions that are being loaded into the scene.",
        "label": "loaded lookfiles",
        "readOnly":True,
        "open":True
    },
}

# fmt: on


class LookFileMaterialsAdd(NodegraphAPI.SuperTool):
    """LookFileMaterialsAdd node."""

    @property
    def _top_dot(self):
        if not hasattr(self, "_top_dot_cache"):
            self._find_child_nodes()
        return self._top_dot_cache

    @property
    def _enable_stack(self):
        if not hasattr(self, "_enable_groupmerge_cache"):
            self._find_child_nodes()
        return self._enable_groupmerge_cache

    @property
    def _copy_stack(self):
        if not hasattr(self, "_copy_stack_cache"):
            self._find_child_nodes()
        return self._copy_stack_cache

    @property
    def _apply_opscript(self):
        if not hasattr(self, "_apply_opscript_cache"):
            self._find_child_nodes()
        return self._apply_opscript_cache

    ###################################################################################

    def __init__(self):
        """Initialize."""

        # Toggle group node appearance
        self.hideNodegraphGroupControls()

        # setup ports
        self.addInputPort("in")
        self.addOutputPort("out")

        in_port = self.getSendPort("in")
        out_port = self.getReturnPort("out")

        # build user interface
        parameters = self.getParameters()
        parameters.createChildString("assets", "")
        parameters.createChildString("version_mode", "current")
        parameters.createChildString("add_button", "")
        parameters.createChildString("watch_list", "")
        parameters.createChildGroup("loaded_lookfiles")

        # build internals
        top_dot = NodegraphAPI.CreateNode("Dot", self)
        top_dot.setName("Top_Dot")
        NodegraphAPI.SetNodePosition(top_dot, (0, 0))
        in_port.connect(top_dot.getInputPortByIndex(0))
        next_out = top_dot.getOutputPortByIndex(0)

        groupmerge_node = NodegraphAPI.CreateNode("GroupMerge", self)
        groupmerge_node.setName("LookFileOverrideEnable_GroupMerge")
        groupmerge_node.setChildNodeType("LookFileOverrideEnable")
        NodegraphAPI.SetNodePosition(groupmerge_node, (X_SPACE, -Y_SPACE * 1))

        merge_node = NodegraphAPI.CreateNode("Merge", self)
        merge_node.addInputPort("i0")
        merge_node.addInputPort("i1")
        NodegraphAPI.SetNodePosition(merge_node, (0, -Y_SPACE * 3))
        next_out.connect(merge_node.getInputPortByIndex(0))
        groupmerge_node.getOutputPortByIndex(0).connect(merge_node.getInputPortByIndex(1))
        next_out = merge_node.getOutputPortByIndex(0)

        dot2_node = NodegraphAPI.CreateNode("Dot", self)
        NodegraphAPI.SetNodePosition(dot2_node, (0, -Y_SPACE * 4))
        next_out.connect(dot2_node.getInputPortByIndex(0))
        next_out = dot2_node.getOutputPortByIndex(0)

        # left branch
        dotl_node = NodegraphAPI.CreateNode("Dot", self)
        NodegraphAPI.SetNodePosition(dotl_node, (-X_SPACE, -Y_SPACE * 4))
        next_out.connect(dotl_node.getInputPortByIndex(0))
        left_out = dotl_node.getOutputPortByIndex(0)

        stack2_node = NodegraphAPI.CreateNode("GroupStack", self)
        stack2_node.setName("HierarchyCopy_Stack")
        stack2_node.setChildNodeType("HierarchyCopy")
        NodegraphAPI.SetNodePosition(stack2_node, (-X_SPACE / 2, -Y_SPACE * 5))
        left_out.connect(stack2_node.getInputPortByIndex(0))

        switch_node = NodegraphAPI.CreateNode("Switch", self)
        sw_in0 = switch_node.addInputPort("i0")
        sw_in1 = switch_node.addInputPort("i1")
        NodegraphAPI.SetNodePosition(switch_node, (-X_SPACE, -Y_SPACE * 6))
        switch_node.getParameter("in").setExpression(
            "ifelse(getParent().version_mode in ['current'], 1, 0)"
        )
        left_out.connect(sw_in0)
        sw_in1.connect(stack2_node.getOutputPortByIndex(0))
        left_out = switch_node.getOutputPortByIndex(0)

        # right branch
        dotr_node = NodegraphAPI.CreateNode("Dot", self)
        NodegraphAPI.SetNodePosition(dotr_node, (X_SPACE, -Y_SPACE * 4))
        next_out.connect(dotr_node.getInputPortByIndex(0))
        right_out = dotr_node.getOutputPortByIndex(0)

        reset_node = NodegraphAPI.CreateNode("OpScript", self)
        reset_node.setName("OP_Reset_LookFile_State")
        NodegraphAPI.SetNodePosition(reset_node, (X_SPACE, -Y_SPACE * 5))
        reset_node.getParameter("CEL").setExpression("=^/assets")
        reset_node.getParameter("script.lua").setValue(RESET_OPSCRIPT, 0)
        right_out.connect(reset_node.getInputPortByIndex(0))
        right_out = reset_node.getOutputPortByIndex(0)

        resolve_node = NodegraphAPI.CreateNode("LookFileResolve", self)
        NodegraphAPI.SetNodePosition(resolve_node, (X_SPACE, -Y_SPACE * 6))
        right_out.connect(resolve_node.getInputPortByIndex(0))
        right_out = resolve_node.getOutputPortByIndex(0)

        # main OpScript
        apply_node = NodegraphAPI.CreateNode("OpScript", self)
        apply_node.setName("OP_Apply_LookFile_Mtls")
        apply_node.addInputPort("i1")
        NodegraphAPI.SetNodePosition(apply_node, (0, -Y_SPACE * 7))
        apply_node.getParameter("script.lua").setValue(APPLY_OPSCRIPT, 0)
        apply_node.getParameters().createChildGroup("user")
        apply_node.getParameter("user").createChildString("version_mode", "")
        apply_node.getParameter("user.version_mode").setExpression("=^/version_mode")
        left_out.connect(apply_node.getInputPortByIndex(0))
        right_out.connect(apply_node.getInputPortByIndex(1))
        out_port.connect(apply_node.getOutputPortByIndex(0))

        self._is_new = True

    def delete(self):
        """Delete this node."""
        Nodes3DAPI.UnregisterPortOpClient(self._port_op_client)
        #        Utils.EventModule.UnregisterEventHandler(self._on_port_connect, "port_connect")
        super().delete()

    def upgrade(self):
        """Upgrade the node if it is out of date."""

        if not self.isLocked():
            Upgrade(self)
        else:
            print("Cannot upgrade locked LookFileMaterialsAdd %s" % self.getName())

    def polish(self):
        """Finish setting up the node."""

        # This will be called when a new node is created or when a scene is loaded. However,
        # when a scene is loaded all the nodes within the supertool will not be wired up yet.

        if hasattr(self, "_is_new"):
            self._init()
        else:
            Callbacks.addCallback(Callbacks.Type.onSceneLoad, self._init)
            pass

    def _init(self, *args, **kwargs):
        #        Utils.EventModule.RegisterEventHandler(self._on_port_connect, "port_connect")
        self._port_op_client = LookFileMaterialsAddPortOpClient(
            node=self, callback=self._on_lookfile_attribute_changed
        )
        Nodes3DAPI.RegisterPortOpClient(self._port_op_client)

    def _find_child_nodes(self):
        for child in self.getChildren():
            if child.getType() == "Dot" and child.getName().startswith("Top_Dot"):
                self._top_dot_cache = child
            if child.getType() == "GroupMerge" and child.getName().startswith(
                "LookFileOverrideEnable_GroupMerge"
            ):
                self._enable_groupmerge_cache = child
            if child.getType() == "GroupStack" and child.getName().startswith("HierachyCopy_Stack"):
                self._copy_stack_cache = child
            if child.getType() == "OpScript" and child.getName().startswith(
                "OP_Apply_LookFile_Mtls"
            ):
                self._apply_opscript_cache = child

#    def _on_port_connect(self, *argv, **kwargs):
#        if not hasattr(self, "_connect_active") or not self._connect_active:
#            self._connect_active = True
#            Utils.EventModule.RegisterEventHandler(self._on_connected_idle, "event_idle")
#
#    def _on_connected_idle(self, *argv, **kwargs):
#        Utils.EventModule.UnregisterEventHandler(self._on_connected_idle, "event_idle")
#        # do stuff
#        self._connect_active = False

    def _on_lookfile_attribute_changed(self, locations: set[str]):
        if self.getInputPortByIndex(0).getNumConnectedPorts() == 0:
            return

        stale = False
        self._find_child_nodes()

        producer = Nodes3DAPI.GetGeometryProducer(self._top_dot_cache, graphState=None, portIndex=0)
        lookfiles = []
        for location in locations:
            sgLocation = producer.getProducerByPath(location)
            resolvedAssetAttr = sgLocation.getAttribute("lookfile.resolvedAttr")
            if resolvedAssetAttr:
                lookfile = resolvedAssetAttr.getValue(0)
                if lookfile not in lookfiles:
                    lookfiles.append(lookfile)

        # compare incoming lookfiles against internal LookFileOverrideEnable nodes
        overrideEnableNodes = self._enable_groupmerge_cache.getChildNodes()
        for overrideNode in overrideEnableNodes:
            lookfile = overrideNode.getParameter("lookfile").getValue(0)
            if lookfile not in lookfiles:
                stale = True
                break

        if stale:
            self.update(locations)

    def addParameterHints(self, attrName, inputDict):  # noqa
        """This function will be called by Katana to allow you to provide hints
        to the UI to change how parameters are displayed."""

        inputDict.update(_PARAMETER_HINTS.get(attrName, {}))

    def update(self, locations):
        """Called when an update is required."""

        # disable undo recording
        Utils.UndoStack.DisableCapture()
        try:
            # pre-instantiating node for add_button.py
            node = self  # noqa

            with open(f"{CURRENT_DIRECTORY}/scripts/add_button.py") as file:
                exec(file.read())
        finally:
            Utils.UndoStack.EnableCapture()


class LookFileMaterialsAddPortOpClient(Nodes3DAPI.PortOpClient.PortOpClient):
    """A Port Op Client to monitor changes to submit settings in the scenegraph."""

    def __init__(
        self, node: NodegraphAPI.Node, callback: Callable[[set[str]], None], *args, **kwargs
    ):
        super().__init__(*args, **kwargs)

        self._callback = callback

        self._client = None
        self._node = node

    def opChanged(
        self,
        op: FnGeolib.GeolibRuntimeOp,
        graphState: NodegraphAPI.GraphState,
        txn: FnGeolib.GeolibRuntimeTransaction,
    ):
        """Method is called by Katana whenever the viewed Op Tree changes."""

        # print("LookFileMaterialsAddPortOpClient.opChanged")

        if self._client is None:
            # Create the Geolib Runtime Client.
            self._client = txn.createClient()
            if self._client is None:
                LOG.error(
                    "LookFileMaterialsAddPortOpClient: Failed to create Geolib Runtime Client."
                )
                return

            locations = []
            if len(self._node.getParameter("watch_list").getValue(0)) > 0:
                locations = ast.literal_eval(self._node.getParameter("watch_list").getValue(0))

                # print("locations to monitor = ", locations)

                # Set up the Client by marking the relevant location as active.
                self._client.setLocationsActive(locations)

                # Event handler to periodically process location events (i.e. the resulting
                # events of the asynchronous cooking in a background thread).
                Utils.EventModule.RegisterEventHandler(self._on_event_idle, "event_idle")

        txn.setClientOp(self._client, op)

    def _on_event_idle(self, *args, **kwargs):
        if self._client is None:
            return

        changed_locations = set()
        locationEvents = self._client.getLocationEvents()
        for locationEvent in locationEvents:
            locationPath = locationEvent.getLocationPath()

            # Ancestors of cooked locations will be cooked before the target location we are
            # interested in is cooked; the check skips those.
            locationData = locationEvent.getLocationData()
            if locationData is None:
                continue

            if not locationData.doesLocationExist():
                continue

            changed_locations.add(locationPath)

        if changed_locations:
            self._callback(changed_locations)

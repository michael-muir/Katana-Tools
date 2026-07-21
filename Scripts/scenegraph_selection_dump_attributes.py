import os
import tempfile

from Katana import NodegraphAPI, Nodes3DAPI, FnAttribute, ScenegraphManager


def attribute_to_string(attr):
    """Produce a deterministic representation of an attribute."""

    if attr is None:
        return "<None>"

    if isinstance(attr, FnAttribute.GroupAttribute):
        return "<Group>"

    try:
        return repr(attr.getData())
    except Exception:
        try:
            return attr.getXML()
        except Exception:
            return repr(attr)


def dump_group(group, fp, prefix=""):
    """
    Recursively dump a GroupAttribute while preserving child order.
    """

    for i in range(group.getNumberOfChildren()):

        child_name = group.getChildName(i)
        child = group.getChildByIndex(i)

        full_name = child_name if not prefix else prefix + "." + child_name

        if isinstance(child, FnAttribute.GroupAttribute):

            fp.write("{} <Group>\n".format(full_name))
            dump_group(child, fp, full_name)

        else:

            fp.write("{} = {}\n".format(
                full_name,
                attribute_to_string(child)
            ))


def dump_root_attributes(path="/root"):

    viewed = NodegraphAPI.GetViewNode()
    producer = Nodes3DAPI.GetGeometryProducer(viewed)
    root = producer.getProducerByPath(path)

    outfile = os.path.join(
        tempfile.gettempdir(),
        path[1:].replace('/', '-') + "_" + "katana_attributes.txt"
    )

    with open(outfile, "w") as fp:

        fp.write("Viewed Node : {}\n".format(viewed.getName()))
        fp.write("Location    : /\n")
        fp.write("=" * 80 + "\n\n")

        #
        # Attribute order is preserved by getAttributeNames()
        #
        for name in root.getAttributeNames():

            attr = root.getAttribute(name)

            if isinstance(attr, FnAttribute.GroupAttribute):

                fp.write("{} <Group>\n".format(name))
                dump_group(attr, fp, name)

            else:

                fp.write("{} = {}\n".format(
                    name,
                    attribute_to_string(attr)
                ))

    print("Wrote:", outfile)

## MAIN SCRIPT ###

sg = ScenegraphManager.getActiveScenegraph()
selected = sg.getSelectedLocations()

for location in selected:
    dump_root_attributes(location)

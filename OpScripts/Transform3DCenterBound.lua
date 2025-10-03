--[[
NAME: Transform3DCenterBound
SCOPE: Transform3D

(c) Michael Muir 2025

date: 10/02/2025

Author: Michael Muir
version 1.0.0

]]

function accumulateBounds(location)
    --[[  Recursively accumlate bounds from all descendant geometry.
         Calculate bounds no bounds are found.
    ]]
    local boundAttr = Interface.GetAttr("bound", location)
    if boundAttr then
        local bounds = boundAttr:getNearestSample(Interface.GetCurrentTime())
        if bounds[1] < minX then minX = bounds[1] end
        if bounds[3] < minY then minY = bounds[3] end
        if bounds[5] < minZ then minZ = bounds[5] end
        if bounds[2] > maxX then maxX = bounds[2] end
        if bounds[4] < maxY then maxY = bounds[4] end
        if bounds[6] < maxZ then maxZ = bounds[6] end
    else
        local pointAttr = Interface.GetAttr("geometry.point.P", location)
        if pointAttr ~= nil then
            local positions = pointAttr:getNearestSample(0)
            local count = #positions
            for i = 1, count, 3 do
                local x, y, z = positions[i], positions[i+1], positions[i+2]
                if x < minX then minX = x end
                if y < minY then minY = y end
                if z < minZ then minZ = z end
                if x > maxX then maxX = x end
                if y > maxY then maxY = y end
                if z > maxZ then maxZ = z end
            end
        end
    end

    -- Recurse into children
    local children = Interface.GetPotentialChildren(location)
    for _, child in ipairs(children:getNearestSample(0)) do
        accumulateBounds(location .. "/" .. child)
    end
end

----------
-- Main --
----------

local time = Interface.GetCurrentTime()

-- the following 3 items are user parameters of type Number Array ( size 3 )
local translate = Interface.GetOpArg('user.translate'):getNearestSample(time)
local rotate = Interface.GetOpArg('user.rotate'):getNearestSample(time)
local scale = Interface.GetOpArg('user.scale'):getNearestSample(time)

-- get bounds
local boundAttr = Interface.GetAttr("bound")
if not boundAttr then
    -- Initialize bounds to extreme values
    minX, minY, minZ = math.huge, math.huge, math.huge
    maxX, maxY, maxZ = -math.huge, -math.huge, -math.huge

    -- Walk and accumulate bounds from all descendants geometry
    accumulateBounds(Interface.GetInputLocationPath())

    -- If bounds were found, set them
    if minX < math.huge then
        bounds = {minX, maxX, minY, maxY, minZ, maxZ}
        Interface.SetAttr("bound", FloatAttribute(bounds, 6))
    else
        print("No point data found under to calculate bounds", startLocation)
        return
    end
else
    bounds = boundAttr:getNearestSample(time)
end

-- Compute center
local xmin, xmax, ymin, ymax, zmin, zmax = unpack(bounds)
cx = 0.5 * (xmin + xmax)
cy = 0.5 * (ymin + ymax)
cz = 0.5 * (zmin + zmax)
Interface.SetAttr("center", DoubleAttribute({cx, cy, cz}))

-- rebuild xform
local gb = GroupBuilder()
local currentXform = Interface.GetAttr("xform")
if currentXform then
    gb:update(currentXform)
end

-- set transform 3D attributes
gb:set("locationPath", StringAttribute(Interface.GetInputLocationPath()))
gb:set("pivot", DoubleAttribute({cx, cy, cz}))
gb:set("makeInteractive", IntAttribute(1))
gb:set("applyFirst", IntAttribute(1))

-- xform group
local xform = GroupBuilder()
xform:set("translate", DoubleAttribute(translate))
xform:set("rotateZ", DoubleAttribute({rotate[3], 0.0, 0.0, 1.0}))
xform:set("rotateY", DoubleAttribute({rotate[2], 0.0, 1.0, 0.0}))
xform:set("rotateX", DoubleAttribute({rotate[1], 0.0, 1.0, 0.0}))
xform:set("scale", DoubleAttribute(scale))
gb:set("xform", xform:build())

-- update xform
Interface.ExecOp("Transform", gb:build())

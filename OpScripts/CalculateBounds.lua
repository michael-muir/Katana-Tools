--[[
NAME: CalculateBounds
SCOPE: Bounds

(c) Michael Muir 2025

date: 10/02/2025

Author: Michael Muir
version 1.0.0

]]

-- Recursively compute bounds from all descendant geometry
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
        if bounds[4] > maxY then maxY = bounds[4] end
        if bounds[6] > maxZ then maxZ = bounds[6] end
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



-- Starting at the current location
local startLocation = Interface.GetInputLocationPath()

-- Initialize bounds to extreme values
minX, minY, minZ = math.huge, math.huge, math.huge
maxX, maxY, maxZ = -math.huge, -math.huge, -math.huge

-- Walk and accumulate bounds from all descendants
accumulateBounds(startLocation)

-- If bounds were found, set them
if minX < math.huge then
    boundsAttr = Interface.SetAttr("bound", FloatAttribute({minX, maxX, minY, maxY, minZ, maxZ}, 6))
    print("BOUNDSATTR", boundsAttr)
    --print(string.format(
    --    "Computed Component Bounds: (%.3f, %.3f, %.3f) to (%.3f, %.3f, %.3f)",
    --    minX, minY, minZ, maxX, maxY, maxZ
    --))
else
    print("No point data found under", startLocation)
end

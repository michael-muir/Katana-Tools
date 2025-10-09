-- Get user data
local numberAttributeName = Interface.GetOpArg("user.numberAttributeName"):getValue()
local numberAttributeType = Interface.GetOpArg("user.numberAttributeType"):getValue()
local floatValue = Interface.GetOpArg("user.floatValue"):getValue()
local colorValue = Interface.GetOpArg("user.colorValue"):getNearestSample(0)
local mathOperation = Interface.GetOpArg("user.mathOperation"):getValue()


-- Return if numberAttributeName is not set properly
if numberAttributeName:find("Drop Attribute Here") then
    return
end

-- Check to see if we need to cook the graph ( used to get default values of attributes on materials )
local attr = nil
if numberAttributeName:find("material.") then
    local OLP = Interface.GetOutputLocationPath()
    local mtlAttr = InterfaceUtils.CookDaps("material", OLP)
    attr = mtlAttr:getChildByName(numberAttributeName)
else
    attr = Interface.GetAttr(numberAttributeName)
end

if not attr then
    return
end

-- Setup dynamic function using a string expression built from the mathOperation using Lua's pcall
local op = mathOperation:match("^(%S+)")
local functionString = "return function(a,b) return a"..op.."b end"
local func, err = load(functionString)
local ok, pfunc = nil
if func then
    ok, pfunc = pcall(func)
else
    return
end

-- Execute dynamic function and set new values
if numberAttributeType == "float" then
    local currentValue = attr:getValue()
    local result = pfunc(currentValue, floatValue)
    Interface.SetAttr(numberAttributeName, FloatAttribute(result))

elseif numberAttributeType == "color" then
    local currentValue = attr:getNearestSample(0)

    local r_result = pfunc(currentValue[1], colorValue[1])
    local g_result = pfunc(currentValue[2], colorValue[2])
    local b_result = pfunc(currentValue[3], colorValue[3])
    print(r_result, g_result, b_result)

    Interface.SetAttr(numberAttributeName, FloatAttribute({r_result, g_result, b_result}))
end


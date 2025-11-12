"""Duplicate Door and Open Properties."""

__title__ = 'Duplicate Door'
__doc__ = 'Duplicates selected door and opens properties dialog'

from pyrevit import revit, DB, UI, forms, script
from pychilizer import select, units

doc = revit.doc
uidoc = revit.uidoc
logger = script.get_logger()
output = script.get_output()

# Get door from selection or prompt user
def get_door():
    # Check pre-selection first
    pre_selection = select.preselection_with_filter(DB.BuiltInCategory.OST_Doors)
    if pre_selection:
        if forms.alert(
            "You have selected {} door(s). Use the first one?".format(len(pre_selection)),
            yes=True, no=True
        ):
            return pre_selection[0]
    
    # Otherwise prompt for selection
    try:
        with forms.WarningBar(title="Select a door to duplicate"):
            ref = uidoc.Selection.PickObject(
                UI.Selection.ObjectType.Element,
                select.CatFilter(DB.BuiltInCategory.OST_Doors),
                "Select a door to duplicate"
            )
        door = doc.GetElement(ref.ElementId)
        if isinstance(door, DB.FamilyInstance) and door.Category and \
           door.Category.Id.IntegerValue == int(DB.BuiltInCategory.OST_Doors):
            return door
    except Exception as e:
        logger.debug("Selection cancelled or failed: {}".format(e))
        return None
    return None

# Get the door
door = get_door()
if not door:
    forms.alert("No door selected. Please select a door to duplicate.", ok=True, exitscript=True)

# Calculate a small offset to make the duplicate visible
# Use a small offset in the view's X direction (about 1 foot or 300mm)
if units.is_metric(doc):
    offset_distance = units.convert_length_to_internal(0.3, doc)  # 300mm
else:
    offset_distance = units.convert_length_to_internal(1.0, doc)  # 1 foot

# Get door location to determine offset direction
door_location = door.Location.Point if door.Location else door.get_BoundingBox(None).Min
# Use a simple offset in X direction
offset = DB.XYZ(offset_distance, 0, 0)

# Duplicate the door
with revit.Transaction("Duplicate Door"):
    try:
        # Copy the door element
        new_door_ids = DB.ElementTransformUtils.CopyElement(doc, door.Id, offset)
        
        if not new_door_ids or len(new_door_ids) == 0:
            forms.alert("Failed to duplicate door.", ok=True, exitscript=True)
        
        new_door_id = new_door_ids[0]
        new_door = doc.GetElement(new_door_id)
        
        # Select the new door
        selection = revit.get_selection()
        selection.set_to([new_door_id])
        
        # Refresh the view to show the new door
        uidoc.RefreshActiveView()
        
        # Open properties dialog
        # Use PostCommand to trigger the Properties command
        try:
            prop_cmd = UI.RevitCommandId.LookupPostableCommandId(UI.PostableCommand.Properties)
            if prop_cmd:
                revit.ui.PostCommand(prop_cmd)
            else:
                # Fallback: just inform user
                forms.alert(
                    "Door duplicated successfully!\n\n"
                    "The new door has been selected. Press PP to open the Properties panel.",
                    ok=True
                )
        except Exception as e:
            logger.warning("Could not open properties dialog automatically: {}".format(e))
            forms.alert(
                "Door duplicated successfully!\n\n"
                "The new door has been selected. Press PP to open the Properties panel.",
                ok=True
            )
        
        print("Duplicated door: {0}".format(output.linkify(new_door_id)))
        
    except Exception as e:
        logger.error("Error duplicating door: {}".format(e))
        forms.alert("Error duplicating door:\n{}".format(str(e)), ok=True, exitscript=True)


# -*- coding: ascii -*-
#  TEMPLATE: Revit API Exploration Button

#  This template shows :
#   Imports & environment setup
#   Collectors & Filters
#   Element iteration & parameter access
#   User interactions (selection, dropdowns, inputs)
#   Transactions (modifying elements)
#   Creating elements (walls)
#   Output formatting + logging
#   Multiple examples kept but disabled for switching ON/OFF

__title__ = 'Test'
__doc__   = 'Trying different things and showing API basics'

# ALWAYS IMPORT LIBRARIES

# DB      = All Revit API classes (Walls, Views, FamilyInstance, etc.)
# forms   = PyRevit dialogs (input forms, selection windows, alerts)
# script  = Logger + Output Panel Tools
from pyrevit import revit, DB, forms, script

doc   = revit.doc      # Main document (ALWAYS needed)
uidoc = revit.uidoc    # Only needed for user selection / UI
logger = script.get_logger()  # For console logging (great for debugging)
output = script.get_output()  # Lets you format tables, link elements, etc.

# HOW TO GET ELEMENTS IN REVIT (MOST IMPORTANT PATTERN)

#   DB.FilteredElementCollector(doc)
#       .OfClass(DB.SomeClass)           # Filter by TYPE
#       .OfCategory(DB.BuiltInCategory)  # (Optional)
#       .WhereElementIsNotElementType()  # (Optional)
#       .ToElements()                    # Return list

# Example patterns are kept below for reference:
# elements = DB.FilteredElementCollector(doc).OfClass(DB.Wall).ToElements()
# elements = DB.FilteredElementCollector(doc).OfClass(DB.FamilyInstance).OfCategory(DB.BuiltInCategory.OST_Doors).ToElements()

# USER CHOOSES WHAT TO TEST (SWITCH BETWEEN FEATURES)

action = forms.CommandSwitchWindow.show(
    {
        "List Walls": "List all walls in model",
        "List Doors": "List all doors in model",
        "Modify Elements": "Move selected elements by 5 meter",
        "Create Wall": "Create a simple test wall",
        "Parameter Report": "Show parameters for selected element"
    },
    message="Choose what to test"
)

if not action:
    forms.alert("Cancelled")
    script.exit()

# ACTION 1: LIST ALL WALLS
if action == "List Walls":

    walls = DB.FilteredElementCollector(doc).OfClass(DB.Wall).ToElements()

    output.print_md("## List of Walls")
    output.print_table(
        table_data=[[w.Id, w.Name] for w in walls],
        columns=["ID", "Wall Name"]
    )
    logger.info("Found {} walls".format(len(walls)))

# ACTION 2: LIST ALL DOORS
elif action == "List Doors":

    doors = (DB.FilteredElementCollector(doc)
             .OfClass(DB.FamilyInstance)
             .OfCategory(DB.BuiltInCategory.OST_Doors)
             .ToElements())

    output.print_md("## List of Doors")
    output.print_table(
        table_data=[[d.Id, d.Name] for d in doors],
        columns=["ID", "Door Name"]
    )
    logger.info("Found {} doors".format(len(doors)))

# ACTION 3: MODIFY SELECTED ELEMENTS
# Move selected elements by (5 meter, 0, 0)

elif action == "Modify Elements":

    selection = uidoc.Selection.GetElementIds()

    if not selection:
        forms.alert("Select elements first.")
        script.exit()

    elements = [doc.GetElement(id) for id in selection]

    # Vector: 5 meter in X direction
    move_vector = DB.XYZ(5, 0, 0)

    with revit.Transaction("Move elements"):
        for element in elements:
            DB.ElementTransformUtils.MoveElement(doc, element.Id, move_vector)

    forms.alert("{} elements moved 5 meter.".format(len(elements)))

# ACTION 4: CREATE A TEST WALL

elif action == "Create Wall":

    # Pick two points from screen
    click_pts = forms.get_picked_points(
        message="Pick 2 points to define a wall"
    )

    if len(click_pts) != 2:
        forms.alert("Need exactly 2 points.")
        script.exit()

    level = DB.FilteredElementCollector(doc) \
        .OfClass(DB.Level).FirstElement()

    with revit.Transaction("Create Test Wall"):
        wall = DB.Wall.Create(doc, DB.Line.CreateBound(click_pts[0], click_pts[1]), level.Id, False)

    output.print_md("### Created Wall:")
    output.linkify(wall.Id)
    logger.info("Wall created.")

# ACTION 5: REPORT PARAMETERS

elif action == "Parameter Report":

    selection = uidoc.Selection.GetElementIds()

    if not selection:
        forms.alert("Select ONE element.")
        script.exit()

    element = doc.GetElement(selection[0])

    output.print_md("## Parameter Report for: {} (ID {})".format(element.Name, element.Id))

    params = element.Parameters

    rows = []
    for p in params:
        try:
            val = p.AsValueString() or p.AsString() or "-"
        except:
            val = "-"
        rows.append([p.Definition.Name, val])

    output.print_table(rows, columns=["Parameter", "Value"])
    logger.info("Parameter report complete.")

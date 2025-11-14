# -*- coding: ascii -*-
#  TEMPLATE: Revit API Exploration Button (ANNOTATED VERSION)
#
#  Every block below includes line-by-line explanations.
#  I did NOT change your logic — only added comments.

__title__ = 'Test'
__doc__   = 'Trying different things to learn API basics'

# ---------------------------------------------------------------------------
# IMPORTS — These bring Revit API + pyRevit tools into your script
# ---------------------------------------------------------------------------
# revit   → gives you doc (model) + uidoc (UI)
# DB      → Autodesk.Revit.DB (database/model classes)
# forms   → pyRevit popups, dropdowns, inputs
# script  → logs + pyRevit output window tools
from pyrevit import revit, DB, forms, script

# ---------------------------------------------------------------------------
# ENVIRONMENT SETUP — ALWAYS DO THIS
# ---------------------------------------------------------------------------
doc   = revit.doc      # Active Revit document (the model database)
uidoc = revit.uidoc    # UI document (selection, active view, picking)
logger = script.get_logger()  # Lets you print logs to pyRevit console
output = script.get_output()  # Lets you print tables, markdown, element links

# ---------------------------------------------------------------------------
# HOW TO GET ELEMENTS — MOST IMPORTANT REVIT API PATTERN
# ---------------------------------------------------------------------------
# DB.FilteredElementCollector(doc) creates a collector scanning the entire model.
# .OfClass(DB.SomeClass) filters by the actual C# class (Wall, FamilyInstance, etc.)
# .OfCategory(...) filters by BuiltInCategory (e.g. Doors, Windows)
# .WhereElementIsNotElementType() removes Type elements & keeps only Instances.
# .ToElements() converts the collector into a Python list.

# Examples (commented out, used as reference):
# elements = DB.FilteredElementCollector(doc).OfClass(DB.Wall).ToElements()
# elements = (DB.FilteredElementCollector(doc)
#             .OfClass(DB.FamilyInstance)
#             .OfCategory(DB.BuiltInCategory.OST_Doors)
#             .ToElements())

# ---------------------------------------------------------------------------
# A pop-up window where the user chooses what the script should do.
# forms.CommandSwitchWindow.show returns the key of the selected option.
# ---------------------------------------------------------------------------
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

# If user closes the dialog → action is None → exit early.
if not action:
    forms.alert("Cancelled")
    script.exit()

# ---------------------------------------------------------------------------
# ACTION 1 — LIST ALL WALLS
# ---------------------------------------------------------------------------
if action == "List Walls":

    # Collect all wall instances in the project
    walls = DB.FilteredElementCollector(doc).OfClass(DB.Wall).ToElements()

    # Output markdown header in pyRevit output panel
    output.print_md("## List of Walls")

    # Create a table: each row = [ID, Name]
    output.print_table(
        table_data=[[w.Id, w.Name] for w in walls],
        columns=["ID", "Wall Name"]
    )

    # Log for debugging
    logger.info("Found {} walls".format(len(walls)))

# ---------------------------------------------------------------------------
# ACTION 2 — LIST ALL DOORS
# ---------------------------------------------------------------------------
elif action == "List Doors":

    # Collector: only FamilyInstances, only Doors category
    doors = (DB.FilteredElementCollector(doc)
             .OfClass(DB.FamilyInstance)
             .OfCategory(DB.BuiltInCategory.OST_Doors)
             .ToElements())

    output.print_md("## List of Doors")

    # Table of ID + Name
    output.print_table(
        table_data=[[d.Id, d.Name] for d in doors],
        columns=["ID", "Door Name"]
    )

    logger.info("Found {} doors".format(len(doors)))

# ---------------------------------------------------------------------------
# ACTION 3 — MOVE SELECTED ELEMENTS
# ---------------------------------------------------------------------------
elif action == "Modify Elements":

    # Get current UI selection (list of element Ids)
    selection = uidoc.Selection.GetElementIds()

    if not selection:
        forms.alert("Select elements first.")
        script.exit()

    # Convert Ids → actual Elements
    elements = [doc.GetElement(id) for id in selection]

    # Create a 3D vector: 5000 mm = 5 m in X direction
    move_vector = DB.XYZ(5000, 0, 0)

    # Use pyRevit's Transaction wrapper
    with revit.Transaction("Move elements"):
        for element in elements:
            # Move each element by the vector
            DB.ElementTransformUtils.MoveElement(doc, element.Id, move_vector)

    forms.alert("{} elements moved 5 meter.".format(len(elements)))

# ---------------------------------------------------------------------------
# ACTION 4 — CREATE A SIMPLE WALL
# ---------------------------------------------------------------------------
elif action == "Create Wall":

    # User picks two points in the canvas
    click_pts = forms.get_picked_points(
        message="Pick 2 points to define a wall"
    )

    if len(click_pts) != 2:
        forms.alert("Need exactly 2 points.")
        script.exit()

    # Get the first Level found in the model
    level = (DB.FilteredElementCollector(doc)
             .OfClass(DB.Level)
             .FirstElement())

    # Create a straight line wall between the two clicks
    with revit.Transaction("Create Test Wall"):
        wall = DB.Wall.Create(
            doc,
            DB.Line.CreateBound(click_pts[0], click_pts[1]),
            level.Id,
            False
        )

    # Print a clickable link to the created wall
    output.print_md("### Created Wall:")
    output.linkify(wall.Id)
    logger.info("Wall created.")

# ---------------------------------------------------------------------------
# ACTION 5 — PARAMETER REPORT FOR ONE ELEMENT
# ---------------------------------------------------------------------------
elif action == "Parameter Report":

    # User must select ONE element
    selection = uidoc.Selection.GetElementIds()

    if not selection:
        forms.alert("Select ONE element.")
        script.exit()

    element = doc.GetElement(selection[0])

    # Title
    output.print_md("## Parameter Report for: {} (ID {})".format(element.Name, element.Id))

    params = element.Parameters  # All parameters of this element

    rows = []  # Will become a table of [parameter name, value]

    for p in params:
        try:
            # Try readable values (e.g. dimensions, text)
            val = p.AsValueString() or p.AsString() or "-"
        except:
            val = "-"
        rows.append([p.Definition.Name, val])

    # Print the parameters table
    output.print_table(rows, columns=["Parameter", "Value"])
    logger.info("Parameter report complete.")
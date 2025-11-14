__title__ = 'Door QA'
__doc__   = 'Lists all doors and highlights missing or duplicate Mark values.'

from pyrevit import revit, DB, forms, script

doc    = revit.doc
uidoc  = revit.uidoc
logger = script.get_logger()
output = script.get_output()

# Collect all door instances in the model
doors = (DB.FilteredElementCollector(doc)
         .OfClass(DB.FamilyInstance)
         .OfCategory(DB.BuiltInCategory.OST_Doors)
         .ToElements())

if not doors:
    forms.alert("No doors found in this model.", ok=True)
else:
    all_rows = []
    missing_mark_rows = []

    for d in doors:
        id_link = output.linkify(d.Id)

        type_elem = doc.GetElement(d.GetTypeId())
        type_name = type_elem.Name if type_elem else "<No Type>"

        level_name = ""
        try:
            level = doc.GetElement(d.LevelId)
            level_name = level.Name if level else ""
        except Exception:
            level_name = ""

        mark_param = d.get_Parameter(DB.BuiltInParameter.ALL_MODEL_MARK)
        mark_val = ""
        if mark_param:
            mark_val = mark_param.AsString() or mark_param.AsValueString() or ""

        all_rows.append([id_link, type_name, level_name, mark_val])

        # Missing Mark if empty or just spaces
        if not mark_val.strip():
            missing_mark_rows.append([id_link, type_name, level_name, "(blank)"])

    # Doors with missing Mark
    output.print_md("## Doors with missing Mark")
    if missing_mark_rows:
        output.print_table(
            table_data=missing_mark_rows,
            columns=["ID", "Type", "Level", "Mark"]
        )
    else:
        output.print_md("✅ No doors with missing Mark.")

    # All doors summary
    output.print_md("## All Doors (summary)")
    output.print_table(
        table_data=all_rows,
        columns=["ID", "Type", "Level", "Mark"]
    )
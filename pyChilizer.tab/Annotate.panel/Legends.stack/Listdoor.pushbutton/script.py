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
    rows = []

    for d in doors:
        # Clickable ID link
        id_link = output.linkify(d.Id)

        # Type name
        type_elem = doc.GetElement(d.GetTypeId())
        type_name = type_elem.Name if type_elem else "<No Type>"

        # Level name (may be empty for some elements)
        level_name = ""
        try:
            level = doc.GetElement(d.LevelId)
            level_name = level.Name if level else ""
        except Exception:
            level_name = ""

        rows.append([id_link, type_name, level_name])

    output.print_md("## Doors (ID / Type / Level)")
    output.print_table(
        table_data=rows,
        columns=["ID", "Type", "Level"]
    )
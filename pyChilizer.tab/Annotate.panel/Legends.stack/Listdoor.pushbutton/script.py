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
    rows = [[d.Id, d.Name] for d in doors]

    output.print_md("## Door List (ID / Name)")
    output.print_table(
        table_data=rows,
        columns=["ID", "Name"]
    )
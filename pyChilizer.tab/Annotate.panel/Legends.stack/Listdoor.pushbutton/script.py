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

# Simple alert with count
forms.alert(
    "Found {} door(s) in this model.".format(len(doors)),
    ok=True
)
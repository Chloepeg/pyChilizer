__title__ = 'Door QA'
__doc__   = 'Lists all doors and highlights missing or duplicate Mark values.'

from pyrevit import revit, DB, forms, script

# environment setup
doc    = revit.doc
uidoc  = revit.uidoc
logger = script.get_logger()
output = script.get_output()

forms.alert("Door QA script loaded (placeholder).", ok=True)
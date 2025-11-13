__title__ = 'Rename views'
__doc__ = 'shows a table of all the views that are placed on sheets in this project'

#import libraries and reference the RevitAPI and RevitAPIUI
from pyrevit import revit, DB, forms, script
doc = revit.doc
logger = script.get_logger()
output = script.get_output()

def list_views_on_sheets():
    """collect all the viewports and show their views in a table"""
    viewports = DB.FilteredElementCollector(doc).OfClass(DB.Viewport).ToElements()
   
    if not viewports:
        forms.alert("No viewports placed on sheets in the project.", ok=True)
        return

    rows = []
    for vp in viewports:
        try:
            #view displayed by this viewport
            view = doc.GetElement(vp.ViewId)
            #sheet hosting this viewport
            sheet = doc.GetElement(vp.SheetId)

            if not view or not sheet:
                continue

            view_name = view.Name
            #get view type as string if possible
            view_type = view.ViewType.ToString() if hasattr(view, 'ViewType') else 'Unknown'

            sheet_number = sheet.SheetNumber
            sheet_name = sheet.Name

            rows.append([sheet_number, sheet_name, view_name, view_type])
        except Exception as e:
            logger.debug("Failed to read viewport {}: {}".format(vp.Id, e))
            continue

    if not rows:
        forms.alert("No views found on sheets in the project.", ok=True)
        return

    #sort rows by sheet number then view name
    rows.sort(key=lambda r: (r[0], r[2]))

    #Print table in pyrevit output window
    columns = ["Sheet Number", "Sheet Name", "View Name", "View Type"]

    output.print_table(
        table_data=rows,
        columns=columns,
        title="Views Placed on Sheets"
    )

#Run the main function when the button is clicked
list_views_on_sheets()
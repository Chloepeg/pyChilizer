__title__ = 'Debug Tags'
__doc__ = 'Shows all tag-like elements in the active view.'

from pyrevit import revit, DB, script

doc = revit.doc
output = script.get_output()
logger = script.get_logger()


def run():
    view = doc.ActiveView

    # I try to collect all IndependentTag in this view.
    tags = (DB.FilteredElementCollector(doc, view.Id)
            .WhereElementIsNotElementType()
            .ToElements())

    rows = []

    for el in tags:
        # I am only interested in annotation like things,
        # but for now I list everything and filter later.
        if not isinstance(el, DB.IndependentTag):
            continue

        tag = el

        tag_id = tag.Id.IntegerValue

        # Class name and category name for this tag
        class_name = tag.GetType().ToString()
        cat_name = ""
        if tag.Category:
            try:
                cat_name = tag.Category.Name
            except:
                cat_name = ""

        # Try to find what this tag points to
        referenced = []
        # Newer style multi reference
        try:
            refs = tag.GetTaggedElementIds()
            for r in refs:
                eid = r.ElementId
                if eid and eid != DB.ElementId.InvalidElementId:
                    elem = doc.GetElement(eid)
                    rc = elem.Category.Name if elem and elem.Category else ""
                    referenced.append("{} (cat: {})".format(eid.IntegerValue, rc))
        except:
            pass

        # Older style single reference
        if not referenced:
            try:
                ref = tag.TaggedElementId
                if ref and ref.ElementId and ref.ElementId != DB.ElementId.InvalidElementId:
                    elem = doc.GetElement(ref.ElementId)
                    rc = elem.Category.Name if elem and elem.Category else ""
                    referenced.append("{} (cat: {})".format(ref.ElementId.IntegerValue, rc))
            except:
                pass

        if not referenced:
            ref_text = "no referenced elements"
        else:
            ref_text = "; ".join(referenced)

        rows.append([
            tag_id,
            class_name,
            cat_name,
            ref_text
        ])

    output.print_md("## Tag debug for view: " + view.Name)
    if rows:
        output.print_table(
            table_data=rows,
            columns=["Tag ID", "Tag class", "Tag category", "References"]
        )
    else:
        output.print_md("No IndependentTag elements found in this view.")

    logger.info("Debugged {} tag elements.".format(len(rows)))


run()
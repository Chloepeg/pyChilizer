__title__ = 'Debug Tags'
__doc__ = 'Shows all tag-like elements in the active view.'

from pyrevit import revit, DB, script

doc = revit.doc
output = script.get_output()
logger = script.get_logger()


def run():
    # I look at the active view only.
    view = doc.ActiveView

    # I collect all elements in this view, then I will filter for IndependentTag.
    elems = (DB.FilteredElementCollector(doc, view.Id)
             .WhereElementIsNotElementType()
             .ToElements())

    rows = []

    for el in elems:
        # I only care about IndependentTag elements for now.
        if not isinstance(el, DB.IndependentTag):
            continue

        tag = el

        # Tag id as string, so I do not rely on IntegerValue.
        tag_id_text = str(tag.Id)

        # I record the .NET class name and category name for the tag.
        class_name = tag.GetType().ToString()
        cat_name = ""
        if tag.Category:
            try:
                cat_name = tag.Category.Name
            except:
                cat_name = ""

        # Now I try to find which elements this tag is pointing at.
        referenced = []

        # First I try the newer multi reference method.
        try:
            refs = tag.GetTaggedElementIds()
            for r in refs:
                try:
                    eid = r.ElementId
                    if eid and eid != DB.ElementId.InvalidElementId:
                        elem = doc.GetElement(eid)
                        ref_cat = ""
                        if elem and elem.Category:
                            try:
                                ref_cat = elem.Category.Name
                            except:
                                ref_cat = ""
                        referenced.append(str(eid) + " (cat: " + ref_cat + ")")
                except:
                    continue
        except:
            pass

        # If that did not work, I try the older single reference property.
        if not referenced:
            try:
                ref = tag.TaggedElementId
                if ref and ref.ElementId and ref.ElementId != DB.ElementId.InvalidElementId:
                    elem = doc.GetElement(ref.ElementId)
                    ref_cat = ""
                    if elem and elem.Category:
                        try:
                            ref_cat = elem.Category.Name
                        except:
                            ref_cat = ""
                    referenced.append(str(ref.ElementId) + " (cat: " + ref_cat + ")")
            except:
                pass

        if not referenced:
            ref_text = "no referenced elements"
        else:
            ref_text = "; ".join(referenced)

        rows.append([
            tag_id_text,
            class_name,
            cat_name,
            ref_text
        ])

    output.print_md("## Tag debug for view: " + view.Name)
    if rows:
        output.print_table(
            table_data=rows,
            columns=["Tag Id", "Tag class", "Tag category", "References"]
        )
    else:
        output.print_md("No IndependentTag elements found in this view.")

    logger.info("Debugged " + str(len(rows)) + " tag elements in view '" + view.Name + "'.")


run()
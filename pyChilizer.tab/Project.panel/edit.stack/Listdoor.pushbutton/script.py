__title__ = 'Door Tag QA'

__doc__ = 'Compares door tags in plan views and elevation views.'

from pyrevit import revit, DB, script
# I import only what I need:
# revit gives me access to the model.
# DB gives me the Revit API classes.
# script lets me print tables and logs.

doc = revit.doc
# This is the active Revit document.

logger = script.get_logger()
# I use this if I want to print messages in the pyRevit console.

output = script.get_output()
# This lets me print tables in the output window.


def safe_name(elem, fallback=""):
    # Some Revit elements do not have a Name property.
    # Instead of letting the script crash, I return a fallback string.
    if not elem:
        return fallback
    try:
        return elem.Name
    except:
        try:
            return str(elem.Id)
        except:
            return fallback


def get_views_of_type(vtype):
    # I want all views of a specific type, for example all floor plans.
    # I also skip templates because those do not contain tags.
    allviews = DB.FilteredElementCollector(doc).OfClass(DB.View).ToElements()
    views = []
    for v in allviews:
        if not v.IsTemplate and v.ViewType == vtype:
            views.append(v)
    return views


def get_doors():
    # This collects every placed door instance in the model.
    return (DB.FilteredElementCollector(doc)
            .OfClass(DB.FamilyInstance)
            .OfCategory(DB.BuiltInCategory.OST_Doors)
            .WhereElementIsNotElementType()
            .ToElements())


def get_tags_in_view(view):
    # This collects all annotation tags placed inside one specific view.
    # I only want door tags or multi category tags.
    tags = (DB.FilteredElementCollector(doc, view.Id)
            .OfClass(DB.IndependentTag)
            .WhereElementIsNotElementType()
            .ToElements())

    result = []
    for t in tags:
        cat = t.Category
        if not cat:
            continue
        try:
            bic = DB.BuiltInCategory(cat.Id.IntegerValue)
        except:
            continue
        if bic == DB.BuiltInCategory.OST_DoorTags or bic == DB.BuiltInCategory.OST_MultiCategoryTags:
            result.append(t)
    return result


def map_tags_to_doors(views):
    # I need to know which door each tag belongs to.
    # So I build a dictionary that stores:
    # door_id : list of tag texts found in the given views.
    tag_map = {}

    for view in views:
        tags = get_tags_in_view(view)

        for tag in tags:
            tagged_ids = set()

            # I try to get the element ids this tag points to.
            try:
                refs = tag.GetTaggedElementIds()
                for r in refs:
                    eid = r.ElementId
                    if eid and eid != DB.ElementId.InvalidElementId:
                        tagged_ids.add(eid)
            except:
                pass

            # I get the printed text of the tag.
            try:
                text = tag.TagText or ""
            except:
                text = ""

            # I store the text under each door id.
            for eid in tagged_ids:
                if eid not in tag_map:
                    tag_map[eid] = []
                if text and text not in tag_map[eid]:
                    tag_map[eid].append(text)

    return tag_map


def run():
    # This is the main function that will run when I click the pyRevit button.

    doors = get_doors()
    # I collect all doors in the model.

    plan_views = get_views_of_type(DB.ViewType.FloorPlan)
    # All plan views.

    elev_views = get_views_of_type(DB.ViewType.Elevation)
    # All elevation views.

    plan_tags = map_tags_to_doors(plan_views)
    elev_tags = map_tags_to_doors(elev_views)
    # These tell me what tags each door has in plans and elevation views.

    all_rows = []
    inconsistent_rows = []

    for d in doors:
        eid = d.Id
        id_link = output.linkify(eid)
        # This makes the ID clickable in the output window.

        type_elem = doc.GetElement(d.GetTypeId())
        type_name = safe_name(type_elem, "No Type")

        level_elem = doc.GetElement(d.LevelId)
        level_name = safe_name(level_elem, "")

        # I gather tag texts from plans.
        p_tags = plan_tags.get(eid, [])
        p_text = ", ".join(p_tags) if p_tags else ""

        # I gather tag texts from elevations.
        e_tags = elev_tags.get(eid, [])
        e_text = ", ".join(e_tags) if e_tags else ""

        # I check if the tagging is consistent across plan and elevation.
        if not p_text and not e_text:
            status = "OK"
        elif p_text and e_text:
            if p_text == e_text:
                status = "OK"
            else:
                status = "Inconsistent"
        else:
            status = "Inconsistent"

        row = [
            id_link,
            type_name,
            level_name,
            p_text if p_text else "No tag",
            e_text if e_text else "No tag",
            status
        ]

        all_rows.append(row)

        if status == "Inconsistent":
            inconsistent_rows.append(row)

    # Now I print the results.

    output.print_md("## Door Tag Consistency")

    output.print_md("### Doors with inconsistent tagging")
    if inconsistent_rows:
        output.print_table(
            table_data=inconsistent_rows,
            columns=["ID", "Type", "Level", "Tag in Plans", "Tag in Elevations", "Status"]
        )
    else:
        output.print_md("No inconsistencies found.")

    output.print_md("### All doors summary")
    output.print_table(
        table_data=all_rows,
        columns=["ID", "Type", "Level", "Tag in Plans", "Tag in Elevations", "Status"]
    )

    logger.info("Finished checking door tags. Count: " + str(len(all_rows)))


run()
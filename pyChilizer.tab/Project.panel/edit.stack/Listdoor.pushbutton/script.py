__title__ = 'Door Tag QA'
# This is what I see on the pyRevit button.

__doc__ = 'Checks tag consistency for all plan and elevation views.'
# This shows up in the tooltip.

from pyrevit import revit, DB, script

doc = revit.doc
# This is the active Revit document.

logger = script.get_logger()
# I use this to print messages to the console.

output = script.get_output()
# This lets me print tables in the output panel.


def safe_name(elem, fallback=""):
    # Some elements do not have a Name property.
    # I return a fallback string instead of crashing.
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
    # I get all views of a specific type.
    # I skip template views because they do not contain tags.
    allviews = DB.FilteredElementCollector(doc).OfClass(DB.View).ToElements()
    views = []
    for v in allviews:
        if not v.IsTemplate and v.ViewType == vtype:
            views.append(v)
    return views


def get_doors():
    # I collect every placed door instance in the entire model.
    return (DB.FilteredElementCollector(doc)
            .OfClass(DB.FamilyInstance)
            .OfCategory(DB.BuiltInCategory.OST_Doors)
            .WhereElementIsNotElementType()
            .ToElements())


def extract_tag_text(tag):
    # I try to get the text printed on the tag.
    # Some tags store text in TagText.
    try:
        t = tag.TagText
        if t:
            return t
    except:
        pass

    # If TagText is empty, I check if the tag has formatted text.
    try:
        fmt = tag.GetFormattedText()
        if fmt:
            return fmt
    except:
        pass

    # If everything fails, return empty.
    return ""


def get_door_tag_map(views):
    # This builds a dictionary that maps:
    # door id : list of tag texts found in the given views.

    tag_map = {}

    for view in views:
        # I collect every IndependentTag in this view.
        tags = DB.FilteredElementCollector(doc, view.Id) \
                    .OfClass(DB.IndependentTag) \
                    .WhereElementIsNotElementType() \
                    .ToElements()

        for tag in tags:
            # First, I get the element ids this tag references.
            door_ids = set()
            try:
                refs = tag.GetTaggedElementIds()
                for r in refs:
                    eid = r.ElementId
                    if eid and eid != DB.ElementId.InvalidElementId:
                        # Check if the referenced element is a door.
                        elem = doc.GetElement(eid)
                        if isinstance(elem, DB.FamilyInstance):
                            cat = elem.Category
                            if cat and cat.Id.IntegerValue == DB.BuiltInCategory.OST_Doors:
                                door_ids.add(eid)
            except:
                pass

            # If this tag does not reference any door, skip it.
            if not door_ids:
                continue

            # I extract the printed text from the tag.
            text = extract_tag_text(tag)

            # I store this tag text for each referenced door.
            for did in door_ids:
                if did not in tag_map:
                    tag_map[did] = []
                if text and text not in tag_map[did]:
                    tag_map[did].append(text)

    return tag_map


def run():
    # This runs when I click the button.

    doors = get_doors()

    # I get all plan views.
    plan_views = get_views_of_type(DB.ViewType.FloorPlan)

    # I get all elevation views.
    elev_views = get_views_of_type(DB.ViewType.Elevation)

    # I map tags in plans and elevations.
    plan_tags = get_door_tag_map(plan_views)
    elev_tags = get_door_tag_map(elev_views)

    all_rows = []
    inconsistent = []

    for door in doors:
        did = door.Id
        id_link = output.linkify(did)

        type_elem = doc.GetElement(door.GetTypeId())
        type_name = safe_name(type_elem, "No Type")

        level_elem = doc.GetElement(door.LevelId)
        level_name = safe_name(level_elem, "")

        # Get tag text found in all plan views.
        p_list = plan_tags.get(did, [])
        p_text = ", ".join(p_list) if p_list else ""

        # Get tag text found in all elevation views.
        e_list = elev_tags.get(did, [])
        e_text = ", ".join(e_list) if e_list else ""

        # Determine if tags are consistent.
        if not p_text and not e_text:
            status = "OK"
        elif p_text and e_text and p_text == e_text:
            status = "OK"
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
            inconsistent.append(row)

    # Print results.
    output.print_md("## Door Tag Consistency Across All Plans and Elevations")

    output.print_md("### Inconsistent Doors")
    if inconsistent:
        output.print_table(
            table_data=inconsistent,
            columns=["ID", "Type", "Level", "Plan Tag", "Elevation Tag", "Status"]
        )
    else:
        output.print_md("No inconsistencies found.")

    output.print_md("### All Doors")
    output.print_table(
        table_data=all_rows,
        columns=["ID", "Type", "Level", "Plan Tag", "Elevation Tag", "Status"]
    )

    logger.info("Finished checking door tags.")


run()
__title__ = 'Door Tag QA'
__doc__   = 'Check doors in the active view for missing door tags.'

from pyrevit import revit, DB, forms, script

doc    = revit.doc
uidoc  = revit.uidoc
logger = script.get_logger()
output = script.get_output()


def get_doors_in_view(view):
    """Return all door instances visible in the view."""
    return (DB.FilteredElementCollector(doc, view.Id)
            .OfClass(DB.FamilyInstance)
            .OfCategory(DB.BuiltInCategory.OST_Doors)
            .WhereElementIsNotElementType()
            .ToElements())


def get_door_tags_in_view(view):
    """Return all door tag annotations in the given view."""
    return (DB.FilteredElementCollector(doc, view.Id)
            .OfClass(DB.IndependentTag)
            .OfCategory(DB.BuiltInCategory.OST_DoorTags)
            .WhereElementIsNotElementType()
            .ToElements())


def get_tagged_door_ids(tags):
    """Return a set of ElementIds of doors that are tagged."""
    tagged_ids = set()

    for tag in tags:
        try:
            refs = tag.GetTaggedElementIds()
            for r in refs:
                eid = r.ElementId
                if eid and eid != DB.ElementId.InvalidElementId:
                    tagged_ids.add(eid)
        except:
            pass

    return tagged_ids


def run_tag_qa():
    view = doc.ActiveView

    doors = get_doors_in_view(view)
    if not doors:
        forms.alert("No doors found in this view.", ok=True)
        return

    tags = get_door_tags_in_view(view)
    tagged_ids = get_tagged_door_ids(tags)

    untagged_rows = []
    all_rows = []

    for d in doors:
        id_link = output.linkify(d.Id)

        # Type name
        type_elem = doc.GetElement(d.GetTypeId())
        try:
            type_name = type_elem.Name
        except:
            type_name = "<No Type>"

        # Level
        try:
            level = doc.GetElement(d.LevelId)
            level_name = level.Name
        except:
            level_name = ""

        # Tagged or not
        is_tagged = d.Id in tagged_ids
        tagged_text = "Yes" if is_tagged else "No"

        # Build master list
        all_rows.append([
            id_link,
            type_name,
            level_name,
            tagged_text
        ])

        # Build untagged list
        if not is_tagged:
            untagged_rows.append([
                id_link,
                type_name,
                level_name
            ])

    output.print_md("## Door Tag QA for view: '{}'".format(view.Name))

    # Ungtagged doors
    output.print_md("### Doors WITHOUT a tag in this view")
    if untagged_rows:
        output.print_table(
            table_data=untagged_rows,
            columns=["ID", "Type", "Level"]
        )
    else:
        output.print_md("All doors in this view have a tag.")

    # Full list
    output.print_md("### All doors in this view (tag status)")
    output.print_table(
        table_data=all_rows,
        columns=["ID", "Type", "Level", "Tagged?"]
    )

    logger.info("Tag QA complete for view '{}'".format(view.Name))


# Run
run_tag_qa()
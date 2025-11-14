__title__ = 'Door Tag QA'

__doc__ = 'Checks if doors are tagged in plans and elevations.'

from pyrevit import revit, DB, script

doc = revit.doc
logger = script.get_logger()
output = script.get_output()


def safe_name(elem, fallback=""):
    # I want to get elem.Name but avoid crashes if it does not exist.
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
    # I collect all views of a given type and ignore templates.
    allviews = DB.FilteredElementCollector(doc).OfClass(DB.View).ToElements()
    views = []
    for v in allviews:
        if not v.IsTemplate and v.ViewType == vtype:
            views.append(v)
    return views


def get_doors():
    # I collect every door instance in the model.
    return (DB.FilteredElementCollector(doc)
            .OfClass(DB.FamilyInstance)
            .OfCategory(DB.BuiltInCategory.OST_Doors)
            .WhereElementIsNotElementType()
            .ToElements())


def get_tagged_door_ids_in_views(views, door_id_set):
    # For a list of views, I want to know which doors are tagged at least once.
    tagged_door_ids = set()

    for view in views:
        # I get all IndependentTag elements in this view.
        tags = (DB.FilteredElementCollector(doc, view.Id)
                .OfClass(DB.IndependentTag)
                .WhereElementIsNotElementType()
                .ToElements())

        for tag in tags:
            # I try to get all element ids that this tag references.
            ref_ids = set()

            try:
                refs = tag.GetTaggedElementIds()
                for r in refs:
                    eid = r.ElementId
                    if eid and eid != DB.ElementId.InvalidElementId:
                        ref_ids.add(eid)
            except:
                # Some older tags use a single TaggedElementId property.
                try:
                    ref = tag.TaggedElementId
                    if ref and ref.ElementId and ref.ElementId != DB.ElementId.InvalidElementId:
                        ref_ids.add(ref.ElementId)
                except:
                    pass

            # I only care if the referenced element is a door.
            for eid in ref_ids:
                if eid in door_id_set:
                    tagged_door_ids.add(eid)

    return tagged_door_ids


def get_mark_value(door):
    # I try to read the Mark parameter, since this is usually what the tag shows.
    try:
        p = door.get_Parameter(DB.BuiltInParameter.ALL_MODEL_MARK)
        if p:
            s = p.AsString()
            if s:
                return s
            s2 = p.AsValueString()
            if s2:
                return s2
    except:
        pass
    return ""


def run():
    # This is what runs when I click the button.

    doors = get_doors()
    if not doors:
        output.print_md("No doors found in the model.")
        return

    # I build a set of all door ids to check against tags.
    door_ids = set(d.Id for d in doors)

    # I get all plan views and all elevation views.
    plan_views = get_views_of_type(DB.ViewType.FloorPlan)
    elev_views = get_views_of_type(DB.ViewType.Elevation)

    # For plans: which doors have at least one tag.
    doors_tagged_in_plans = get_tagged_door_ids_in_views(plan_views, door_ids)

    # For elevations: which doors have at least one tag.
    doors_tagged_in_elevs = get_tagged_door_ids_in_views(elev_views, door_ids)

    all_rows = []
    inconsistent_rows = []

    for door in doors:
        did = door.Id
        id_link = output.linkify(did)

        type_elem = doc.GetElement(door.GetTypeId())
        type_name = safe_name(type_elem, "No Type")

        level_elem = doc.GetElement(door.LevelId)
        level_name = safe_name(level_elem, "")

        mark_val = get_mark_value(door)

        plan_tagged = did in doors_tagged_in_plans
        elev_tagged = did in doors_tagged_in_elevs

        plan_text = "Yes" if plan_tagged else "No"
        elev_text = "Yes" if elev_tagged else "No"

        # I consider it consistent only if both plan and elevation have the same state:
        # both tagged, or both untagged.
        if plan_tagged == elev_tagged:
            status = "OK"
        else:
            status = "Inconsistent"

        row = [
            id_link,
            type_name,
            level_name,
            mark_val if mark_val else "",
            plan_text,
            elev_text,
            status
        ]

        all_rows.append(row)

        if status == "Inconsistent":
            inconsistent_rows.append(row)

    # I print the results.
    output.print_md("## Door Tag Presence, Plans vs Elevations")

    output.print_md("### Doors with inconsistent tagging")
    if inconsistent_rows:
        output.print_table(
            table_data=inconsistent_rows,
            columns=["ID", "Type", "Level", "Mark", "Tagged in Plans", "Tagged in Elevations", "Status"]
        )
    else:
        output.print_md("No inconsistencies found.")

    output.print_md("### All doors")
    output.print_table(
        table_data=all_rows,
        columns=["ID", "Type", "Level", "Mark", "Tagged in Plans", "Tagged in Elevations", "Status"]
    )

    logger.info("Finished checking door tag presence for {} doors.".format(len(all_rows)))


run()
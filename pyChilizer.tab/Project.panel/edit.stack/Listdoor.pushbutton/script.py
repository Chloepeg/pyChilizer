__title__ = 'Door Tag QA'
__doc__ = 'Checks if doors are tagged in any plan and any elevation view.'

from pyrevit import revit, DB, script

doc = revit.doc
logger = script.get_logger()
output = script.get_output()


def safe_name(elem, fallback=""):
    # I try to get a clean name for an element.
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
    # I collect all non template views of a given type.
    allviews = DB.FilteredElementCollector(doc).OfClass(DB.View).ToElements()
    views = []
    for v in allviews:
        if not v.IsTemplate and v.ViewType == vtype:
            views.append(v)
    return views


def get_doors():
    # I collect every door instance in the whole model.
    return (DB.FilteredElementCollector(doc)
            .OfClass(DB.FamilyInstance)
            .OfCategory(DB.BuiltInCategory.OST_Doors)
            .WhereElementIsNotElementType()
            .ToElements())


def get_mark_value(door):
    # I try to read the Mark parameter of a door.
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


def get_tagged_door_ids_in_views(views, door_id_set):
    """
    For a list of views, I return a set of door ids that have at least
    one tag in any of those views.

    I use tag.GetTaggedLocalElements(), like in the tutorial guy,
    to get the elements that the tag is attached to.
    """
    tagged_door_ids = set()

    for view in views:
        # I collect all IndependentTag elements in this view.
        tags = (DB.FilteredElementCollector(doc, view.Id)
                .OfClass(DB.IndependentTag)
                .WhereElementIsNotElementType()
                .ToElements())

        for tag in tags:
            tagged_elems = []

            # First, I try GetTaggedLocalElements, which should give me elements.
            try:
                elems = tag.GetTaggedLocalElements()
                if elems:
                    # In some versions this is an IEnumerable, so I loop it.
                    for e in elems:
                        tagged_elems.append(e)
            except:
                tagged_elems = []

            # As a fallback, if that did not work, I try the id based methods.
            if not tagged_elems:
                ref_ids = set()
                # Newer style multi reference
                try:
                    refs = tag.GetTaggedElementIds()
                    for r in refs:
                        eid = r.ElementId
                        if eid and eid != DB.ElementId.InvalidElementId:
                            ref_ids.add(eid)
                except:
                    pass
                # Older style single reference
                if not ref_ids:
                    try:
                        ref = tag.TaggedElementId
                        if ref and ref.ElementId and ref.ElementId != DB.ElementId.InvalidElementId:
                            ref_ids.add(ref.ElementId)
                    except:
                        pass

                for eid in ref_ids:
                    elem = doc.GetElement(eid)
                    if elem:
                        tagged_elems.append(elem)

            # Now I have a list of elements that this tag points to.
            # I only care if they are doors that are in my door_id_set.
            for elem in tagged_elems:
                if not isinstance(elem, DB.FamilyInstance):
                    continue
                cat = elem.Category
                if not cat:
                    continue
                # I check that the element is a door and in my door set.
                if cat.Id.IntegerValue == int(DB.BuiltInCategory.OST_Doors):
                    if elem.Id in door_id_set:
                        tagged_door_ids.add(elem.Id)

    return tagged_door_ids


def run():
    # This is the main function that runs when I click the button.

    doors = get_doors()
    if not doors:
        output.print_md("No doors found in the model.")
        return

    # I store all door ids in a set so it is cheap to check membership.
    door_ids = set(d.Id for d in doors)

    # I collect all plan views and all elevation views.
    plan_views = get_views_of_type(DB.ViewType.FloorPlan)
    elev_views = get_views_of_type(DB.ViewType.Elevation)

    # Now I find which doors are tagged in any plan, and in any elevation.
    doors_tagged_in_plans = get_tagged_door_ids_in_views(plan_views, door_ids)
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

        # I call it consistent only if both sides match:
        # both Yes or both No.
        if plan_tagged == elev_tagged:
            status = "OK"
        else:
            status = "Inconsistent"

        row = [
            id_link,
            type_name,
            level_name,
            mark_val,
            plan_text,
            elev_text,
            status
        ]

        all_rows.append(row)

        if status == "Inconsistent":
            inconsistent_rows.append(row)

    # I print my results.
    output.print_md("## Door tag presence in plans and elevations")

    output.print_md("### Doors with inconsistent tagging")
    if inconsistent_rows:
        output.print_table(
            table_data=inconsistent_rows,
            columns=["Door Id", "Type", "Level", "Mark", "Tagged in plans", "Tagged in elevations", "Status"]
        )
    else:
        output.print_md("No inconsistencies found.")

    output.print_md("### All doors")
    output.print_table(
        table_data=all_rows,
        columns=["Door Id", "Type", "Level", "Mark", "Tagged in plans", "Tagged in elevations", "Status"]
    )

    logger.info("Finished checking door tags for " + str(len(all_rows)) + " doors.")


run()
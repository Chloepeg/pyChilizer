__title__ = 'Door Tag QA'
__doc__ = 'check door tags for inconsistencies between views.'

from pyrevit import revit, DB, script

doc = revit.doc
logger = script.get_logger()
output = script.get_output()


def safe_name(elem, fallback=""):
    # This helper function safely gets the element’s Name.
    # Beginners hit errors when an element doesn't have .Name, so we protect against that.
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
    # This gets ALL views of a specific ViewType (e.g. all plans or all elevations)
    # The filter goes through the entire model and picks views matching the desired type.
    return [
        v for v in DB.FilteredElementCollector(doc)
        .OfClass(DB.View)
        if not v.IsTemplate and v.ViewType == vtype
        # We skip view templates because they’re not real views you can tag things in.
    ]


def get_doors():
    # This collects every door instance in the whole model.
    # FamilyInstance + category = doors → gives us only real placed doors, not types.
    return (
        DB.FilteredElementCollector(doc)
        .OfClass(DB.FamilyInstance)
        .OfCategory(DB.BuiltInCategory.OST_Doors)
        .WhereElementIsNotElementType()
        .ToElements()
    )


def get_tags_in_view(view):
    # This collects all tag annotations inside ONE specific view.
    # Revit stores tags as IndependentTag elements.
    tags = (
        DB.FilteredElementCollector(doc, view.Id)
        .OfClass(DB.IndependentTag)
        .WhereElementIsNotElementType()
        .ToElements()
    )

    # We only want tags that CAN represent doors (Door Tags or Multi-category Tags)
    doorlike = []
    for t in tags:
        cat = t.Category
        if not cat:
            continue
        try:
            bic = DB.BuiltInCategory(cat.Id.IntegerValue)
        except:
            continue

        if bic in (
            DB.BuiltInCategory.OST_DoorTags,
            DB.BuiltInCategory.OST_MultiCategoryTags
        ):
            doorlike.append(t)
    return doorlike


def map_tags_to_doors(views):
    # This is where things get interesting.
    # Our goal is to map EACH DOOR → ITS TAG TEXT(S) in all views provided.

    tag_map = {}   # dictionary: door_id → list of tag text strings

    for view in views:
        # For each view, grab the tags inside it
        tags = get_tags_in_view(view)

        for tag in tags:

            # Step 1: figure out WHICH ELEMENT the tag points to.
            tagged_ids = set()
            try:
                refs = tag.GetTaggedElementIds()
                # A tag can sometimes reference more than one element (multi-tags)
                for r in refs:
                    eid = r.ElementId
                    if eid and eid != DB.ElementId.InvalidElementId:
                        tagged_ids.add(eid)
            except:
                pass

            # Step 2: read the actual text shown on the tag (TagText)
            try:
                text = tag.TagText or ""
            except:
                text = ""

            # Step 3: connect this tag text to the door(s) it points to
            for eid in tagged_ids:
                if eid not in tag_map:
                    tag_map[eid] = []
                if text and text not in tag_map[eid]:
                    tag_map[eid].append(text)

    return tag_map


def run():
    # Main function — this runs when the button is clicked.

    doors = get_doors()
    # First, grab all doors in the whole model.

    plan_views = get_views_of_type(DB.ViewType.FloorPlan)
    # All plan views (every single one).

    elev_views = get_views_of_type(DB.ViewType.Elevation)
    # All elevation views.

    # For each view type, build:
    #   door_id → list of tag text
    plan_tag_map = map_tags_to_doors(plan_views)
    elev_tag_map = map_tags_to_doors(elev_views)

    all_rows = []         # This will hold ALL the doors
    inconsistent_rows = []  # Only doors where plan/elev tag doesnt match

    for d in doors:
        eid = d.Id
        id_link = output.linkify(eid)
        # Makes the ID clickable in the output window.

        type_elem = doc.GetElement(d.GetTypeId())
        type_name = safe_name(type_elem, "<No Type>")
        # Clean type name.

        level = doc.GetElement(d.LevelId)
        level_name = safe_name(level, "")
        # Clean level name.

        # Tag text from any plan view
        plan_tags = plan_tag_map.get(eid, [])
        plan_text = ", ".join(plan_tags) if plan_tags else ""

        # Tag text from any elevation
        elev_tags = elev_tag_map.get(eid, [])
        elev_text = ", ".join(elev_tags) if elev_tags else ""

        # Consistency logic:
        # Case A: no tags anywhere → OK
        # Case B: tags in both → OK if same, else inconsistent Even possible ? 
        # Case C: only tagged in one → inconsistent
        if not plan_text and not elev_text:
            status = "OK"
        elif plan_text and elev_text:
            status = "OK" if plan_text == elev_text else "Inconsistent"
        else:
            status = "Inconsistent"

        row = [
            id_link,
            type_name,
            level_name,
            plan_text or "No tag",
            elev_text or "No tag",
            status
        ]

        all_rows.append(row)
        if status == "Inconsistent":
            inconsistent_rows.append(row)

    # Now we print the results to the pyRevit output panel

    output.print_md("## Door Tag Consistency (All Plans vs All Elevations)")

    output.print_md("### Inconsistent Doors Only")
    if inconsistent_rows:
        output.print_table(
            table_data=inconsistent_rows,
            columns=["ID", "Type", "Level", "Plan Tag", "Elevation Tag", "Status"]
        )
    else:
        output.print_md("No inconsistencies found.")

    output.print_md("### Full Door Tag Summary")
    output.print_table(
        table_data=all_rows,
        columns=["ID", "Type", "Level", "Plan Tag", "Elevation Tag", "Status"]
    )

    logger.info(
        "Door Tag QA complete. {} doors checked, {} inconsistent."
        .format(len(all_rows), len(inconsistent_rows))
    )


run()
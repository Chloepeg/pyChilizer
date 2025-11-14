__title__ = 'Door Tags In View'
__doc__ = 'Shows which doors in the active view have a tag.'

from pyrevit import revit, DB, script

doc = revit.doc
uidoc = revit.uidoc
logger = script.get_logger()
output = script.get_output()


def safe_name(elem, fallback=""):
    if not elem:
        return fallback
    try:
        return elem.Name
    except:
        try:
            return str(elem.Id)
        except:
            return fallback


def get_doors_in_view(view):
    # I collect all door instances visible in this view.
    doors = (DB.FilteredElementCollector(doc, view.Id)
             .OfClass(DB.FamilyInstance)
             .OfCategory(DB.BuiltInCategory.OST_Doors)
             .WhereElementIsNotElementType()
             .ToElements())
    return doors


def get_tagged_door_ids_in_view(view, door_ids):
    # I want to know which of these doors have at least one tag in this view.
    tagged_door_ids = set()

    tags = (DB.FilteredElementCollector(doc, view.Id)
            .OfClass(DB.IndependentTag)
            .WhereElementIsNotElementType()
            .ToElements())

    for tag in tags:
        ref_ids = set()

        # First try the newer multi reference method.
        try:
            refs = tag.GetTaggedElementIds()
            for r in refs:
                eid = r.ElementId
                if eid and eid != DB.ElementId.InvalidElementId:
                    ref_ids.add(eid)
        except:
            # Older style: single TaggedElementId
            try:
                ref = tag.TaggedElementId
                if ref and ref.ElementId and ref.ElementId != DB.ElementId.InvalidElementId:
                    ref_ids.add(ref.ElementId)
            except:
                pass

        for eid in ref_ids:
            if eid in door_ids:
                tagged_door_ids.add(eid)

    return tagged_door_ids


def run():
    # I work in the active view only.
    view = doc.ActiveView

    doors = get_doors_in_view(view)
    if not doors:
        output.print_md("No doors found in this view.")
        return

    door_ids = set(d.Id for d in doors)

    tagged_ids = get_tagged_door_ids_in_view(view, door_ids)

    rows = []
    for d in doors:
        did = d.Id
        id_link = output.linkify(did)

        type_elem = doc.GetElement(d.GetTypeId())
        type_name = safe_name(type_elem, "No Type")

        level_elem = doc.GetElement(d.LevelId)
        level_name = safe_name(level_elem, "")

        is_tagged = "Yes" if did in tagged_ids else "No"

        rows.append([
            id_link,
            type_name,
            level_name,
            is_tagged
        ])

    output.print_md("## Door tags in view: " + view.Name)
    output.print_table(
        table_data=rows,
        columns=["Door ID", "Type", "Level", "Tagged in this view?"]
    )

    logger.info("Checked {} doors in view '{}'.".format(len(rows), view.Name))


run()
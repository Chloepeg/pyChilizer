__title__ = 'Door QA'
__doc__   = 'Check doors for missing or duplicate Tag (Mark) values and show a summary.'

from pyrevit import revit, DB, forms, script

# Environment setup
doc    = revit.doc
uidoc  = revit.uidoc
logger = script.get_logger()
output = script.get_output()

# Collect all door instances in the model
doors = (DB.FilteredElementCollector(doc)
         .OfClass(DB.FamilyInstance)
         .OfCategory(DB.BuiltInCategory.OST_Doors)
         .ToElements())

if not doors:
    forms.alert("No doors found in this model.", ok=True)
else:
    # door_infos will store info for all doors
    door_infos = []
    missing_tag_rows = []
    duplicate_tag_rows = []
    # tag_map will map Tag (Mark) value -> list of door infos
    tag_map = {}

    for d in doors:
        # Clickable ID in pyRevit output
        id_link = output.linkify(d.Id)

        # Type name (defensive: some weird elements may not have Name)
        type_elem = doc.GetElement(d.GetTypeId())
        type_name = "<No Type>"
        if type_elem:
            try:
                type_name = type_elem.Name
            except AttributeError:
                type_name = str(type_elem.Id)

        # Level name (may be empty or level may not have Name)
        level_name = ""
        try:
            level = doc.GetElement(d.LevelId)
            if level:
                try:
                    level_name = level.Name
                except AttributeError:
                    level_name = str(level.Id)
        except Exception:
            level_name = ""

        # Tag value in Revit door tag: underlying parameter is Mark
        mark_param = d.get_Parameter(DB.BuiltInParameter.ALL_MODEL_MARK)
        tag_val = ""
        if mark_param:
            try:
                tag_val = mark_param.AsString() or mark_param.AsValueString() or ""
            except Exception:
                tag_val = ""

        info = {
            "id_link": id_link,
            "type_name": type_name,
            "level_name": level_name,
            "tag": tag_val,
        }
        door_infos.append(info)

        # Missing Tag: empty or only spaces
        if not tag_val.strip():
            missing_tag_rows.append([
                id_link,
                type_name,
                level_name,
                "(blank)"
            ])
        else:
            # Track non-empty Tags for duplicate detection
            key = tag_val.strip()
            if key not in tag_map:
                tag_map[key] = []
            tag_map[key].append(info)

    # Build duplicate_tag_rows
    for tag_value, infos in tag_map.items():
        if len(infos) > 1:
            for info in infos:
                duplicate_tag_rows.append([
                    info["id_link"],
                    info["type_name"],
                    info["level_name"],
                    tag_value
                ])

    # Doors with missing Tag
    output.print_md("## Doors with missing Tag (Mark)")
    if missing_tag_rows:
        output.print_table(
            table_data=missing_tag_rows,
            columns=["ID", "Type", "Level", "Tag"]
        )
    else:
        output.print_md("No doors with missing Tag.")

    # Doors with duplicate Tag
    output.print_md("## Doors with duplicate Tag (Mark) values")
    if duplicate_tag_rows:
        output.print_table(
            table_data=duplicate_tag_rows,
            columns=["ID", "Type", "Level", "Tag"]
        )
    else:
        output.print_md("No duplicate door Tags found.")

    # All doors summary
    output.print_md("## All Doors (summary)")
    all_rows = []
    for info in door_infos:
        all_rows.append([
            info["id_link"],
            info["type_name"],
            info["level_name"],
            info["tag"]
        ])

    output.print_table(
        table_data=all_rows,
        columns=["ID", "Type", "Level", "Tag"]
    )

    # Log summary only (no blocking popup)
    num_missing    = len(missing_tag_rows)
    num_duplicates = len(duplicate_tag_rows)

    logger.info(
        "Door QA: {} doors total, {} with missing Tag, {} duplicate Tag rows."
        .format(len(doors), num_missing, num_duplicates)
    )
__title__ = 'Door QA'
__doc__   = 'Check doors for missing or duplicate Mark values and show a summary.'

from pyrevit import revit, DB, forms, script

# environment setup
doc    = revit.doc
uidoc  = revit.uidoc
logger = script.get_logger()
output = script.get_output()

# Collect all doors in the model
doors = (DB.FilteredElementCollector(doc)
         .OfClass(DB.FamilyInstance)
         .OfCategory(DB.BuiltInCategory.OST_Doors)
         .ToElements())

if not doors:
    forms.alert("No doors found in this model.", ok=True)
else:
    # door_infos will store info for all doors
    door_infos = []
    missing_mark_rows = []
    duplicate_mark_rows = []
    # mark_map will map Mark value -> list of door infos
    mark_map = {}

    for d in doors:
        # Clickable ID in pyRevit output
        id_link = output.linkify(d.Id)

        # Type name, some elements do not have name)
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

        # Mark parameter (door tag value)
        mark_param = d.get_Parameter(DB.BuiltInParameter.ALL_MODEL_MARK)
        mark_val = ""
        if mark_param:
            try:
                mark_val = mark_param.AsString() or mark_param.AsValueString() or ""
            except Exception:
                mark_val = ""

        info = {
            "id_link": id_link,
            "type_name": type_name,
            "level_name": level_name,
            "mark": mark_val,
        }
        door_infos.append(info)

        # Missing Mark: empty or only spaces
        if not mark_val.strip():
            missing_mark_rows.append([
                id_link,
                type_name,
                level_name,
                "(blank)"
            ])
        else:
            # Track non-empty Marks for duplicate detection
            key = mark_val.strip()
            if key not in mark_map:
                mark_map[key] = []
            mark_map[key].append(info)

    # Build duplicate_mark_rows
    for mark_value, infos in mark_map.items():
        if len(infos) > 1:
            for info in infos:
                duplicate_mark_rows.append([
                    info["id_link"],
                    info["type_name"],
                    info["level_name"],
                    mark_value
                ])

    # Doors with missing Mark
    output.print_md("## Doors with missing Mark")
    if missing_mark_rows:
        output.print_table(
            table_data=missing_mark_rows,
            columns=["ID", "Type", "Level", "Mark"]
        )
    else:
        output.print_md("No doors with missing Mark.")

    # Doors with duplicate Mark
    output.print_md("## Doors with duplicate Mark values")
    if duplicate_mark_rows:
        output.print_table(
            table_data=duplicate_mark_rows,
            columns=["ID", "Type", "Level", "Mark"]
        )
    else:
        output.print_md("No duplicate door Marks found.")

    # All doors summary
    output.print_md("## All Doors (summary)")
    all_rows = []
    for info in door_infos:
        all_rows.append([
            info["id_link"],
            info["type_name"],
            info["level_name"],
            info["mark"]
        ])

    output.print_table(
        table_data=all_rows,
        columns=["ID", "Type", "Level", "Mark"]
    )

    # Summary popup and logging
    num_missing    = len(missing_mark_rows)
    num_duplicates = len(duplicate_mark_rows)

    msg = "Door QA complete.\n"
    msg += "- {} door(s) with missing Mark.\n".format(num_missing)
    msg += "- {} door row(s) with duplicate Mark values.".format(num_duplicates)

    forms.alert(msg, ok=True)

    logger.info(
        "Door QA: {} doors total, {} missing Mark, {} duplicate rows."
        .format(len(doors), num_missing, num_duplicates)
    )

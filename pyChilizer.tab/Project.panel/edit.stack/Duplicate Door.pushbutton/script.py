"""Prep door placement based on a selected door."""

__title__ = 'Duplicate Door'
__doc__ = 'Pick a door, duplicate its type, open properties, and start placement.'

from Autodesk.Revit.UI.Selection import ISelectionFilter, ObjectType
from pyrevit import revit, DB, UI, forms, script

doc = revit.doc
uidoc = revit.uidoc
logger = script.get_logger()


DOOR_CATEGORY_ID = DB.ElementId(DB.BuiltInCategory.OST_Doors)


def _is_door(elem):
    if not isinstance(elem, DB.FamilyInstance):
        return False
    cat = elem.Category
    if not cat:
        return False
    return cat.Id == DOOR_CATEGORY_ID


class DoorSelectionFilter(ISelectionFilter):
    def AllowElement(self, elem):
        return _is_door(elem)

    def AllowReference(self, reference, point):
        return True


def _get_preselected_door():
    selected_ids = uidoc.Selection.GetElementIds()
    if not selected_ids:
        return None
    for eid in selected_ids:
        elem = doc.GetElement(eid)
        if _is_door(elem):
            return elem
    return None


def _get_unique_type_name(base_name, family):
    existing_names = set()
    for sid in family.GetFamilySymbolIds():
        sym = doc.GetElement(sid)
        if sym:
            existing_names.add(sym.Name)

    if base_name not in existing_names:
        return base_name

    counter = 1
    while True:
        candidate = "{} ({})".format(base_name, counter)
        if candidate not in existing_names:
            return candidate
        counter += 1


def _duplicate_symbol(symbol):
    default_name = "{} Copy".format(symbol.Name)
    new_name = forms.ask_for_string(
        default=_get_unique_type_name(default_name, symbol.Family),
        prompt="Provide a name for the new door type (Cancel to reuse existing type)."
    )
    if not new_name:
        return symbol, False

    new_name = _get_unique_type_name(new_name, symbol.Family)

    with DB.Transaction(doc, "Duplicate Door Type") as t:
        t.Start()
        new_symbol_id = symbol.Duplicate(new_name)
        new_symbol = doc.GetElement(new_symbol_id)
        if not new_symbol.IsActive:
            new_symbol.Activate()
            doc.Regenerate()
        t.Commit()

    logger.info("Duplicated door type '{}' to '{}'".format(symbol.Name, new_name))
    return new_symbol, True


def _ensure_symbol_active(symbol):
    if symbol.IsActive:
        return
    with DB.Transaction(doc, "Activate Door Type") as t:
        t.Start()
        symbol.Activate()
        doc.Regenerate()
        t.Commit()


# Get door from selection or prompt user
def get_door():
    preselected = _get_preselected_door()
    if preselected:
        if forms.alert(
            "Use the pre-selected door?",
            yes=True,
            no=True
        ):
            return preselected

    # Otherwise prompt for selection
    try:
        with forms.WarningBar(title="Select a door to base the duplicate on"):
            ref = uidoc.Selection.PickObject(
                ObjectType.Element,
                DoorSelectionFilter(),
                "Select a door to base the duplicate on"
            )
        door = doc.GetElement(ref.ElementId)
        if _is_door(door):
            return door
    except Exception as e:
        logger.debug("Selection cancelled or failed: {}".format(e))
        return None
    return None


# Main flow
door = get_door()
if not door:
    forms.alert("No door selected. Please select a door to duplicate.", ok=True, exitscript=True)

source_symbol = door.Symbol
if not source_symbol:
    forms.alert("Selected door has no type.", ok=True, exitscript=True)

duplicate_type = forms.alert(
    "Create a new door type based on '{}' before placement?".format(source_symbol.Name),
    yes=True,
    no=True
)

if duplicate_type:
    target_symbol, duplicated = _duplicate_symbol(source_symbol)
else:
    target_symbol = source_symbol
    duplicated = False

_ensure_symbol_active(target_symbol)

if not target_symbol:
    forms.alert("Could not prepare door type.", ok=True, exitscript=True)

# Start placement
try:
    uidoc.PostRequestForElementTypePlacement(target_symbol)
except Exception as err:
    logger.error("Could not start door placement: {}".format(err))
    forms.alert(
        "Couldn't start door placement automatically.\n"
        "Activate the type '{}' manually and place the door.".format(target_symbol.Name),
        ok=True,
        exitscript=True
    )

# Bring Properties / Type Properties forward so user can tweak settings
prop_cmd = UI.RevitCommandId.LookupPostableCommandId(UI.PostableCommand.Properties)
if prop_cmd:
    try:
        revit.ui.PostCommand(prop_cmd)
    except Exception as err:
        logger.debug("Properties command failed: {}".format(err))

type_cmd = UI.RevitCommandId.LookupPostableCommandId(UI.PostableCommand.TypeProperties)
if type_cmd:
    try:
        revit.ui.PostCommand(type_cmd)
    except Exception as err:
        logger.debug("Type Properties command failed: {}".format(err))

msg = "Door placement started using type '{}'.".format(target_symbol.Name)
if duplicated:
    msg += "\nType Properties dialog has been opened so you can adjust parameters before placing."
else:
    msg += "\nReuse existing type. Adjust properties as needed before placing."

try:
    forms.toast(msg, title="Duplicate Door", appid="pyChilizer")
except Exception:
    logger.info(msg)


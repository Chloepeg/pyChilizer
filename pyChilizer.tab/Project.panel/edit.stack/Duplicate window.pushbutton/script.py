"""Prep window placement based on a selected window."""

__title__ = 'Duplicate window'
__doc__ = 'Pick a window, duplicate its type, open properties, and start placement.'

from Autodesk.Revit.UI.Selection import ISelectionFilter, ObjectType
from pyrevit import revit, DB, UI, forms, script

doc = revit.doc
uidoc = revit.uidoc
logger = script.get_logger()


WINDOW_CATEGORY_ID = DB.ElementId(DB.BuiltInCategory.OST_Windows)


def _is_window(elem):
    if not isinstance(elem, DB.FamilyInstance):
        return False
    cat = elem.Category
    if not cat:
        return False
    return cat.Id == WINDOW_CATEGORY_ID


def _get_symbol_name(symbol):
    if not symbol:
        return "Window Type"
    param = symbol.get_Parameter(DB.BuiltInParameter.SYMBOL_NAME_PARAM)
    if param:
        try:
            name_val = param.AsString()
            if name_val:
                return name_val
        except Exception:
            pass
    try:
        return symbol.Name
    except AttributeError:
        return "Window Type"


class WindowSelectionFilter(ISelectionFilter):
    def AllowElement(self, elem):
        return _is_window(elem)

    def AllowReference(self, reference, point):
        return True


def _get_preselected_window():
    selected_ids = uidoc.Selection.GetElementIds()
    if not selected_ids:
        return None
    for eid in selected_ids:
        elem = doc.GetElement(eid)
        if _is_window(elem):
            return elem
    return None


def _generate_unique_type_name(base_name, family):
    existing = set()
    for sid in family.GetFamilySymbolIds():
        sym = doc.GetElement(sid)
        if sym:
            existing.add(_get_symbol_name(sym))

    if base_name and base_name not in existing:
        return base_name

    counter = 1
    base = base_name or "New Window Type"
    while True:
        candidate = "{} ({})".format(base, counter)
        if candidate not in existing:
            return candidate
        counter += 1


def _duplicate_symbol(symbol):
    symbol_name = _get_symbol_name(symbol)
    family = symbol.Family
    default_name = _generate_unique_type_name("{} Copy".format(symbol_name), family)
    new_name = forms.ask_for_string(
        default=default_name,
        prompt="Provide a name for the new window type (leave blank to use default)."
    )
    if not new_name:
        new_name = default_name
    new_name = _generate_unique_type_name(new_name, family)

    with DB.Transaction(doc, "Duplicate Window Type") as t:
        t.Start()
        duplicated = symbol.Duplicate(new_name)
        if isinstance(duplicated, DB.ElementId):
            new_symbol = doc.GetElement(duplicated)
        else:
            new_symbol = duplicated
        if not new_symbol.IsActive:
            new_symbol.Activate()
            doc.Regenerate()
        t.Commit()

    logger.info("Duplicated window type '{}' -> '{}'".format(symbol_name, new_name))
    return new_symbol


def _change_window_type(window, new_symbol):
    """change the window instance to use the new symbol."""
    with DB.Transaction(doc, "Change Window symbol") as t:
        t.Start()
        window.ChangeTypeId(new_symbol.Id)
        t.Commit()
    logger.info("Changed window '{}' to use type '{}'".format(_get_symbol_name(window), _get_symbol_name(new_symbol)))


# Get window from selection or prompt user
def get_window():
    preselected = _get_preselected_window()
    if preselected:
        if forms.alert(
            "Use the pre-selected window?",
            yes=True,
            no=True
        ):
            return preselected

    # Otherwise prompt for selection
    try:
        with forms.WarningBar(title="Select a window to duplicate and change"):
            ref = uidoc.Selection.PickObject(
                ObjectType.Element,
                WindowSelectionFilter(),
                "Select a window to duplicate and change"
            )
        window = doc.GetElement(ref.ElementId)
        if _is_window(window):
            return window
    except Exception as e:
        logger.debug("Selection cancelled or failed: {}".format(e))
        return None
    return None


# Main flow
window = get_window()
if not window:
    forms.alert("No window selected. Please select a door to duplicate.", ok=True, exitscript=True)

type_id = window.GetTypeId()
source_symbol = doc.GetElement(type_id) if type_id else None
if not source_symbol:
    forms.alert("Selected window has no type.", ok=True, exitscript=True)

try:
    target_symbol = _duplicate_symbol(source_symbol)
except Exception as dup_err:
    logger.error("Failed to duplicate window type: {}".format(dup_err))
    forms.alert(
        "Could not duplicate the selected window type.\n"
        "Details: {}".format(dup_err),
        ok=True,
        exitscript=True
    )
    target_symbol = None

if not target_symbol:
    forms.alert("Could not prepare window type.", ok=True, exitscript=True)

# Change the existing window to the new type
try:
    _change_window_type(window, target_symbol)
except Exception as err:
    logger.error("Could not change window type: {}".format(err))
    forms.alert("Could not change the window to the new type.\n"
                "Details: {}".format(err),
                ok=True,
                exitscript=True
    )

# Open the standard Revit Type Properties dialog for the active type
type_cmd = UI.RevitCommandId.LookupPostableCommandId(UI.PostableCommand.TypeProperties)
if type_cmd:
    try:
        revit.ui.PostCommand(type_cmd)
    except Exception as err:
        logger.debug("Type Properties command failed: {}".format(err))

# Toggle the Properties palette (same as pressing PP)
toggle_cmd = UI.RevitCommandId.LookupPostableCommandId(UI.PostableCommand.TogglePropertiesPalette)
if toggle_cmd:
    try:
        revit.ui.PostCommand(toggle_cmd)
    except Exception as err:
        logger.debug("Toggle Properties command failed: {}".format(err))

target_symbol_name = _get_symbol_name(target_symbol)

msg = "Window changed to duplicated type '{}'.".format(target_symbol_name)
msg += "\nType Properties opened. Properties palette toggled (press PP if it closed instead)."

try:
    forms.toast(msg, title="Duplicate Window", appid="pyChilizer")
except Exception:
    logger.info(msg)


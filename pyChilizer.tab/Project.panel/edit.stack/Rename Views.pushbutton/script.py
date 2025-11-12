"""Batch rename views with find/replace support."""

__title__ = 'Rename Views'
__doc__ = 'Edit view names in bulk using a grid and find/replace.'

import clr
clr.AddReference('PresentationFramework')
clr.AddReference('PresentationCore')
clr.AddReference('WindowsBase')

from System.Collections.ObjectModel import ObservableCollection
from System.Windows import RoutedEventArgs

from pyrevit import revit, DB, forms, script

doc = revit.doc
logger = script.get_logger()
output = script.get_output()


class ViewRow(object):
    """Simple container for view data."""

    def __init__(self, view):
        self.Id = view.Id
        self.CurrentName = view.Name
        self.NewName = view.Name
        self.ViewType = str(view.ViewType)


class RenameViewsWindow(forms.WPFWindow):
    """WPF window hosting the rename grid."""

    def __init__(self, data_rows):
        xaml_file = script.get_bundle_file('RenameViewsWindow.xaml')
        forms.WPFWindow.__init__(self, xaml_file)
        self.view_rows = data_rows
        self.ViewsGrid.ItemsSource = self.view_rows
        self.FindTextBox.Text = ''
        self.ReplaceTextBox.Text = ''

        # Wire events
        self.FindReplaceButton.Click += self.apply_find_replace
        self.ResetButton.Click += self.reset_names
        self.OkButton.Click += self.accept_changes
        self.CancelButton.Click += self.cancel_window

    def _commit_grid_edits(self):
        try:
            self.ViewsGrid.CommitEdit()
            self.ViewsGrid.CommitEdit()
        except AttributeError:
            pass

    def apply_find_replace(self, sender, args):
        self._commit_grid_edits()
        find_value = self.FindTextBox.Text or ''
        replace_value = self.ReplaceTextBox.Text or ''
        if not find_value:
            return

        for row in self.view_rows:
            if row.NewName:
                row.NewName = row.NewName.replace(find_value, replace_value)
        self.ViewsGrid.Items.Refresh()

    def reset_names(self, sender, args):
        self._commit_grid_edits()
        for row in self.view_rows:
            row.NewName = row.CurrentName
        self.ViewsGrid.Items.Refresh()

    def accept_changes(self, sender, args):
        self._commit_grid_edits()
        self.DialogResult = True
        self.Close()

    def cancel_window(self, sender, args):
        self.DialogResult = False
        self.Close()


def collect_views():
    """Gather renameable views."""
    views = (
        DB.FilteredElementCollector(doc)
        .OfClass(DB.View)
        .ToElements()
    )
    renameable = []
    for view in views:
        if view.IsTemplate:
            continue
        if isinstance(view, DB.ViewSheet):
            continue
        if view.IsAssemblyView:
            continue
        # Skip system views like Project Browser, etc.
        if view.ViewType == DB.ViewType.Internal:
            continue
        renameable.append(view)
    return sorted(renameable, key=lambda v: v.Name)


def ensure_unique_names(rows):
    """Validate that new names are unique and non-empty."""
    rename_map = {}
    for row in rows:
        new_name = (row.NewName or '').strip()
        if not new_name or new_name == row.CurrentName:
            continue
        rename_map[row.Id] = new_name

    if not rename_map:
        return {}, None

    # Check duplicates within selection
    new_names = list(rename_map.values())
    if len(new_names) != len(set(new_names)):
        return None, "Duplicate names detected in the proposed changes."

    # Check duplicates against other views
    rename_ids = set(rename_map.keys())
    existing_names = {
        view.Name
        for view in collect_views()
        if view.Id not in rename_ids
    }
    conflicts = [name for name in new_names if name in existing_names]
    if conflicts:
        return None, "These names already exist: {}".format(", ".join(conflicts))

    return rename_map, None


def apply_renames(rename_map):
    """Rename views using a single transaction."""
    if not rename_map:
        forms.alert("No changes to apply.", ok=True)
        return

    with revit.Transaction("Rename Views"):
        for elid, new_name in rename_map.items():
            view = doc.GetElement(elid)
            if view:
                old_name = view.Name
                view.Name = new_name
                logger.info("Renamed view '{}' -> '{}'".format(old_name, new_name))
                output.print_md("* {} ➜ {} ({})".format(old_name, new_name, output.linkify(view.Id)))


def main():
    views = collect_views()
    if not views:
        forms.alert("No views available for renaming.", ok=True, exitscript=True)

    rows = ObservableCollection([ViewRow(view) for view in views])
    window = RenameViewsWindow(rows)
    result = window.ShowDialog()

    if not result:
        script.exit()

    rename_map, error = ensure_unique_names(rows)
    if error:
        forms.alert(error, ok=True, exitscript=True)

    apply_renames(rename_map)


if __name__ == "__main__":
    main()


from typing import Dict, Optional, TYPE_CHECKING, Iterable, Mapping, Callable, Tuple, Union, Collection, List, Any

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import GObject


if TYPE_CHECKING:
    from typing_extensions import TypedDict

    class _ListDataDictBase(TypedDict):
        id: str
        type: type

    class ListDataDict(_ListDataDictBase, total=False):
        renderer: Gtk.CellRenderer
        render_attrs: Mapping[str, int]
        view_props: Mapping[str, object]
        celldata_func: Tuple[Callable[[Gtk.TreeViewColumn, Gtk.CellRenderer, Gtk.TreeModelFilter, Gtk.TreeIter, Any],
                                      None], Any]
else:
    ListDataDict = dict


# noinspection PyAttributeOutsideInit
class GenericList(GObject.Object):
    def __init__(self, data: Iterable[ListDataDict], headers_visible: bool = True, visible: bool = False) -> None:
        super().__init__()
        self._view = Gtk.TreeView(headers_visible=headers_visible, visible=visible)
        self.selection = self._view.get_selection()
        self._load(data)

    def _load(self, data: Iterable[ListDataDict]) -> None:
        self.ids: Dict[str, int] = {}
        self.columns: Dict[str, Gtk.TreeViewColumn] = {}

        types = [row["type"] for row in data]

        self.liststore = Gtk.ListStore(*types)
        self.filter = self.liststore.filter_new()
        self._view.set_model(self.filter)

        for i, row in enumerate(data):
            self.ids[row["id"]] = i

            if "renderer" not in row:
                continue

            column = Gtk.TreeViewColumn()
            column.pack_start(row["renderer"], True)
            column.set_attributes(row["renderer"], **row["render_attrs"])

            if "view_props" in row:
                column.set_properties(**row["view_props"])

            if "celldata_func" in row:
                func, user_data = row["celldata_func"]
                column.set_cell_data_func(row["renderer"], func, user_data)

            self.columns[row["id"]] = column
            self.append_column(column)

    def append_column(self, column: Gtk.TreeViewColumn) -> None:
        self._view.append_column(column)

    def set_headers_visible(self, visible: bool) -> None:
        self._view.set_headers_visible(visible)

    def set_has_tooltip(self, has_tooltip: bool) -> None:
        self._view.set_has_tooltip(has_tooltip)

    def get_pointer(self) -> Tuple[int, int]:
        return self._view.get_pointer()

    def get_cursor(self) -> Tuple[Optional[Gtk.TreePath], Optional[Gtk.TreeViewColumn]]:
        return self._view.get_cursor()

    def get_window(self) -> Optional[Gdk.Window]:
        return self._view.get_window()

    def set_cursor(self, path: Gtk.TreePath) -> None:
        self._view.set_cursor(path)

    def show(self) -> None:
        self._view.show()

    def get_path_at_pos(self, x: int, y: int) -> Optional[Tuple[Optional[Gtk.TreePath], Optional[Gtk.TreeViewColumn], int, int]]:
        return self._view.get_path_at_pos(x, y)

    def get_scale_factor(self) -> int:
        return self._view.get_scale_factor()

    def get_cell_area(self, path: Optional[Gtk.TreePath], column: Optional[Gtk.TreeViewColumn]) -> Gdk.Rectangle:
        return self._view.get_cell_area(path, column)

    def get_column(self, n: int) -> Optional[Gtk.TreeViewColumn]:
        return self._view.get_column(n)

    def destroy(self) -> None:
        self._view.destroy()

    @property
    def view(self) -> Gtk.TreeView:
        return self._view

    def selected(self) -> Optional[Gtk.TreeIter]:
        model, tree_iter = self.selection.get_selected()
        if tree_iter is not None:
            tree_iter = model.convert_iter_to_child_iter(tree_iter)
        return tree_iter

    def delete(self, tree_iter: Gtk.TreeIter) -> bool:
        if self.liststore.iter_is_valid(tree_iter):
            self.liststore.remove(tree_iter)
            return True
        else:
            return False

    def _add(self, **columns: object) -> Collection[object]:
        items: Dict[int, object] = {}
        for k, v in self.ids.items():
            items[v] = None

        for k, val in columns.items():
            if k in self.ids:
                items[self.ids[k]] = val
            else:
                raise Exception(f"Invalid key {k}")

        return items.values()

    def append(self, **columns: object) -> Gtk.TreeIter:
        vals = self._add(**columns)
        return self.liststore.append(vals)

    def prepend(self, **columns: object) -> Gtk.TreeIter:
        vals = self._add(**columns)
        return self.liststore.prepend(vals)

    def get_conditional(self, **cols: object) -> List[Gtk.TreeIter]:
        ret = []
        for tree_row in self.liststore:
            row_data = self.get(tree_row.iter)
            for key in cols:
                if row_data[key] == cols[key]:
                    ret.append(tree_row.iter)

        return ret

    def set(self, tree_iter: Gtk.TreeIter, **cols: object) -> None:
        for k, v in cols.items():
            self.liststore.set(tree_iter, self.ids[k], v)

    def get(self, tree_iter: Gtk.TreeIter, *items: str) -> Dict[str, Any]:
        ret = {}
        if len(items) == 0:
            for k, v in self.ids.items():
                ret[k] = self.liststore.get(tree_iter, v)[0]
        else:
            for i in range(len(items)):
                if items[i] in self.ids:
                    ret[items[i]] = self.liststore.get(tree_iter, self.ids[items[i]])[0]
        return ret

    def get_iter(self, path: Optional[Gtk.TreePath]) -> Optional[Gtk.TreeIter]:
        if path is None:
            return None

        try:
            return self.liststore.get_iter(path)
        except ValueError:
            return None

    def clear(self) -> None:
        self.liststore.clear()

    def compare(self, iter_a: Optional[Gtk.TreeIter], iter_b: Optional[Gtk.TreeIter]) -> bool:
        if iter_a is not None and iter_b is not None:
            assert self.liststore is not None
            return self.liststore.get_path(iter_a) == self.liststore.get_path(iter_b)
        else:
            return False

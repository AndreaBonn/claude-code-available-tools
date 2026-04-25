"""TUI module — full-screen Textual app for browsing Claude Code resources."""

from __future__ import annotations

from rich.text import Text
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal
from textual.widgets import Footer, Header, Input, Static, Tree
from textual.widgets.tree import TreeNode

from cctools.scanner import CATEGORIES, Resource, group_by_category, scan_all


class DetailPanel(Static):
    """Right-side panel showing details of the selected resource."""

    DEFAULT_CSS = """
    DetailPanel {
        padding: 1 2;
        width: 1fr;
        overflow-y: auto;
    }
    """

    def show_legend(self) -> None:
        """Display the initial legend when no resource is selected."""
        legend = Text()
        legend.append("cctools — Resource Explorer\n\n", style="bold cyan")
        legend.append("Select a resource from the sidebar.\n\n", style="dim")
        legend.append("Scope badges:\n", style="bold")
        legend.append("  ● ", style="green")
        legend.append("Global (from ~/.claude/)\n")
        legend.append("  ◆ ", style="yellow")
        legend.append("Project (from ./.claude/)\n")
        legend.append("\nKeys: ", style="bold")
        legend.append("/ filter  ", style="dim")
        legend.append("r refresh  ", style="dim")
        legend.append("q quit", style="dim")
        self.update(legend)

    def show_resource(self, resource: Resource) -> None:
        """Display full details of a resource."""
        detail = Text()

        # Name + scope badge
        if resource.scope == "global":
            detail.append("● ", style="green")
            detail.append("Global", style="green")
        else:
            detail.append("◆ ", style="yellow")
            detail.append("Project", style="yellow")

        cat_icon = ""
        cat_label = resource.category
        for cat_id, label, icon in CATEGORIES:
            if cat_id == resource.category:
                cat_icon = icon
                cat_label = label
                break

        detail.append(f"  {cat_icon} {cat_label}\n\n", style="dim")
        detail.append(resource.name, style="bold white")
        detail.append("\n\n")

        if resource.description:
            detail.append("Description\n", style="bold")
            detail.append(f"{resource.description}\n\n")

        detail.append("Source\n", style="bold")
        detail.append(f"{resource.source}\n\n", style="italic")

        if resource.extra:
            detail.append("Extra metadata\n", style="bold")
            for k, v in resource.extra.items():
                val_str = str(v)
                if len(val_str) > 200:
                    val_str = val_str[:200] + "..."
                detail.append(f"  {k}: ", style="bold dim")
                detail.append(f"{val_str}\n")

        self.update(detail)


class SidebarTree(Tree[Resource]):
    """Left sidebar with collapsible category nodes."""

    DEFAULT_CSS = """
    SidebarTree {
        width: 42;
        border-right: solid $accent;
        overflow-y: auto;
    }
    """

    def __init__(self) -> None:
        super().__init__(label="Resources", id="sidebar")
        self.show_root = False


class CtoolsApp(App[int]):
    """Main Textual application for cctools."""

    TITLE = "cctools — Claude Code Tools Explorer"
    CSS = """
    #body {
        height: 1fr;
        layout: horizontal;
    }
    #filter-bar {
        dock: bottom;
        height: 3;
        display: none;
    }
    #filter-bar.visible {
        display: block;
    }
    """

    BINDINGS = [
        Binding(key="q", action="quit", description="Quit"),
        Binding(key="slash", action="open_filter", description="Filter /"),
        Binding(key="r", action="refresh", description="Refresh"),
    ]

    def __init__(
        self,
        filter_term: str = "",
    ) -> None:
        super().__init__()
        self._initial_filter = filter_term
        self._resources: list[Resource] = []
        self._node_to_resource: dict[int, Resource] = {}
        self._filter_term: str = filter_term

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal(id="body"):
            yield SidebarTree()
            yield DetailPanel(id="detail")
        yield Input(
            placeholder="Type to filter... (Escape to close)",
            id="filter-input",
            classes="",
        )
        yield Footer()

    def on_mount(self) -> None:
        """Initial scan and tree population."""
        filter_input = self.query_one("#filter-input", Input)
        filter_input.display = False
        if self._initial_filter:
            self._filter_term = self._initial_filter

        detail = self.query_one("#detail", DetailPanel)
        detail.show_legend()

        self._do_refresh()
        self.set_interval(interval=3.0, callback=self._periodic_refresh)

    def _periodic_refresh(self) -> None:
        """Periodic refresh callback."""
        self._do_refresh()

    def _resource_key(self, r: Resource) -> tuple[str, str, str, str]:
        return (r.category, r.name, r.scope, str(r.source))

    def _do_refresh(self) -> None:
        """Scan resources and rebuild tree if changed."""
        new_resources = scan_all()
        new_keys = {self._resource_key(r) for r in new_resources}
        old_keys = {self._resource_key(r) for r in self._resources}

        if new_keys == old_keys and self._resources:
            return  # No changes

        self._resources = new_resources
        self._rebuild_tree()

    def _rebuild_tree(self) -> None:
        """Rebuild the sidebar tree from current resources and filter."""
        tree = self.query_one(SidebarTree)
        # Remember current selection
        selected_name: str | None = None
        if tree.cursor_node and tree.cursor_node.id is not None:
            node_id = id(tree.cursor_node)
            if node_id in self._node_to_resource:
                selected_name = self._node_to_resource[node_id].name

        tree.clear()
        self._node_to_resource.clear()

        # Apply filter
        resources = self._resources
        if self._filter_term:
            term = self._filter_term.lower()
            resources = [
                r for r in resources if term in r.name.lower() or term in r.description.lower()
            ]

        groups = group_by_category(resources)
        has_filter = bool(self._filter_term)

        restore_node: TreeNode[Resource] | None = None

        for cat_id, cat_label, cat_icon in CATEGORIES:
            cat_resources = groups.get(cat_id, [])
            count = len(cat_resources)
            label = Text()
            label.append(f"{cat_icon} ", style="bold")
            label.append(f"{cat_label} ", style="bold")
            if count > 0:
                label.append(f"({count})", style="bold green")
            else:
                label.append("(0)", style="dim")

            cat_node = tree.root.add(label)

            for r in cat_resources:
                badge_sym, badge_style = (
                    ("● ", "green") if r.scope == "global" else ("◆ ", "yellow")
                )
                item_label = Text()
                item_label.append(badge_sym, style=badge_style)
                item_label.append(r.name)

                leaf = cat_node.add_leaf(item_label, data=r)
                self._node_to_resource[id(leaf)] = r

                if selected_name and r.name == selected_name:
                    restore_node = leaf

            # Expand if filter active or few items
            if has_filter or (0 < count <= 8):
                cat_node.expand()

        if restore_node:
            tree.select_node(restore_node)

    # --- Event handlers ---

    def on_tree_node_highlighted(self, event: Tree.NodeHighlighted[Resource]) -> None:
        """Update detail panel when a tree node is highlighted."""
        node = event.node
        node_id = id(node)
        detail = self.query_one("#detail", DetailPanel)

        if node_id in self._node_to_resource:
            detail.show_resource(self._node_to_resource[node_id])
        else:
            detail.show_legend()

    def action_open_filter(self) -> None:
        """Show the filter input bar."""
        filter_input = self.query_one("#filter-input", Input)
        filter_input.display = True
        filter_input.value = self._filter_term
        filter_input.focus()

    def on_input_changed(self, event: Input.Changed) -> None:
        """Live filter as user types."""
        if event.input.id == "filter-input":
            self._filter_term = event.value
            self._rebuild_tree()

    def key_escape(self) -> None:
        """Close filter bar and clear filter on Escape."""
        filter_input = self.query_one("#filter-input", Input)
        if filter_input.display:
            filter_input.display = False
            self._filter_term = ""
            filter_input.value = ""
            self._rebuild_tree()
            self.query_one(SidebarTree).focus()

    def action_refresh(self) -> None:
        """Manual refresh."""
        self._resources = []  # Force rebuild
        self._do_refresh()


def run(filter_term: str = "", from_slash: bool = False) -> int:
    """Launch the TUI application.

    Parameters
    ----------
    filter_term : str
        Initial filter term.
    from_slash : bool
        Accepted for API compatibility with inline.run() but unused in TUI.

    Returns
    -------
    int
        Exit code.
    """
    app = CtoolsApp(filter_term=filter_term)
    app.run()
    return 0

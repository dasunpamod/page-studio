"""Tests for Python Tkinter code generation and syntax validity."""
import unittest
import py_compile
import tempfile
import os
from pagestudio.core.state import ProjectState
from pagestudio.core.models import WidgetInstance, MenuBarSpec, MenuItemSpec
from pagestudio.core.generator import CodeGenerator

class TestCodeGenerator(unittest.TestCase):

    def test_syntax_validity_all_widgets(self):
        """Generates code with every widget type and compiles it with py_compile."""
        state = ProjectState("All Widgets Test", 800, 600)
        
        # Add one of each major widget
        widget_types = [
            "Button", "Entry", "Label", "Checkbutton", "Radiobutton",
            "Combobox", "Listbox", "Text", "Progressbar", "Scale",
            "Separator", "Frame", "LabelFrame", "Canvas", "Scrolledtext",
            "Scrolledlistbox", "Scrolledtreeview", "TNotebook"
        ]
        
        for i, wtype in enumerate(widget_types):
            w = WidgetInstance.create(wtype, 20, 20 + i * 35)
            state.add_widget(w)

        with tempfile.TemporaryDirectory() as tmpdir:
            gui_path, sup_path = CodeGenerator.generate_all(state, "test_app", tmpdir)

            self.assertTrue(os.path.exists(gui_path))
            self.assertTrue(os.path.exists(sup_path))

            # Validate that generated Python files compile without any SyntaxError
            try:
                py_compile.compile(gui_path, doraise=True)
                py_compile.compile(sup_path, doraise=True)
            except py_compile.PyCompileError as e:
                self.fail(f"Generated Python code failed syntax compilation: {e}")

    def test_support_preserves_custom_code(self):
        """Ensure reconciling doesn't wipe existing user logic in support module."""
        state = ProjectState("Preserve Test", 400, 300)
        btn = WidgetInstance.create("Button", 10, 10, name_hint="btn_action")
        btn.events["command"] = "on_action"
        state.add_widget(btn)

        existing_support = (
            "def on_action():\n"
            "    # USER_CUSTOM_CODE_HERE\n"
            "    return 42\n"
        )

        sup_code = CodeGenerator.generate_support_code(state, "preserve_test", existing_support)
        self.assertIn("def on_action():", sup_code)
        self.assertIn("# USER_CUSTOM_CODE_HERE", sup_code)

    def test_hierarchical_code_generation(self):
        """Widgets must be parented to container and containers generated first."""
        state = ProjectState("Hierarchy Test", 600, 400)
        # Add button first in widget_order, but parented to a frame added second
        btn = WidgetInstance.create("Button", 20, 20, name_hint="nested_btn")
        frame = WidgetInstance.create("Frame", 10, 10, name_hint="parent_panel")
        btn.parent_id = frame.id

        # Intentionally add child first then parent to verify topological sorting
        state.widgets[btn.id] = btn
        state.widget_order.append(btn.id)
        state.widgets[frame.id] = frame
        state.widget_order.append(frame.id)

        gui_code = CodeGenerator.generate_gui_code(state, "hier_app", "hier_app_support")
        
        # Verify parent_panel is instantiated before nested_btn
        pos_panel = gui_code.find("self.parent_panel = ttk.Frame(self.root)")
        pos_btn = gui_code.find("self.nested_btn = ttk.Button(self.parent_panel")
        self.assertNotEqual(pos_panel, -1)
        self.assertNotEqual(pos_btn, -1)
        self.assertLess(pos_panel, pos_btn, "Container must be instantiated before child widget!")

    def test_relative_placement_code(self):
        """Verify emitting relx, rely, relwidth, relheight when is_relative is true."""
        state = ProjectState("Relative Test", 800, 600)
        btn = WidgetInstance.create("Button", 100, 50, name_hint="rel_btn")
        btn.is_relative = True
        btn.rel_x = 0.125
        btn.rel_y = 0.0833
        btn.rel_width = 0.25
        btn.rel_height = 0.05
        state.add_widget(btn)

        gui_code = CodeGenerator.generate_gui_code(state, "rel_app", "rel_app_support")
        self.assertIn("self.rel_btn.place(relx=0.1250, rely=0.0833, relwidth=0.2500, relheight=0.0500)", gui_code)

    def test_scrolled_widgets_generation(self):
        """Scrolled widgets generate frame containers with scrollbars and proper widgets."""
        state = ProjectState("Scrolled Test", 800, 600)
        stext = WidgetInstance.create("Scrolledtext", 10, 10, name_hint="my_text")
        slist = WidgetInstance.create("Scrolledlistbox", 250, 10, name_hint="my_list")
        stree = WidgetInstance.create("Scrolledtreeview", 10, 200, name_hint="my_tree")
        stree.properties["columns"] = [{"id": "c1", "heading": "Title", "width": 120}]
        state.add_widget(stext)
        state.add_widget(slist)
        state.add_widget(stree)

        gui_code = CodeGenerator.generate_gui_code(state, "scrolled_app", "scrolled_app_support")
        
        # Scrolledtext
        self.assertIn("self.my_text_frame = ttk.Frame(self.root)", gui_code)
        self.assertIn("self.my_text_vbar = ttk.Scrollbar(self.my_text_frame, orient=\"vertical\")", gui_code)
        self.assertIn("self.my_text = tk.Text(self.my_text_frame", gui_code)

        # Scrolledlistbox
        self.assertIn("self.my_list_frame = ttk.Frame(self.root)", gui_code)
        self.assertIn("self.my_list = tk.Listbox(self.my_list_frame", gui_code)

        # Scrolledtreeview
        self.assertIn("self.my_tree_frame = ttk.Frame(self.root)", gui_code)
        self.assertIn("self.my_tree_hbar = ttk.Scrollbar(self.my_tree_frame, orient=\"horizontal\")", gui_code)
        self.assertIn("self.my_tree = ttk.Treeview(self.my_tree_frame", gui_code)
        self.assertIn('self.my_tree.heading("c1", text="Title")', gui_code)

    def test_menu_code_generation(self):
        """MenuBarSpec with cascades, commands, and accelerators is cleanly generated."""
        state = ProjectState("Menu App", 600, 400)
        item_new = MenuItemSpec(id="m1", item_type="command", label="New", command="on_new", accelerator="Ctrl+N")
        item_sep = MenuItemSpec(id="m2", item_type="separator")
        item_chk = MenuItemSpec(id="m3", item_type="checkbutton", label="Auto-save", variable="menu_autosave_var")
        cascade_file = MenuItemSpec(id="m0", item_type="cascade", label="File", children=[item_new, item_sep, item_chk])
        menu_spec = MenuBarSpec(id="menu_root", items=[cascade_file])
        state.menus["main_menu"] = menu_spec

        gui_code = CodeGenerator.generate_gui_code(state, "menu_app", "menu_app_support")
        self.assertIn("self.menubar = tk.Menu(self.root)", gui_code)
        self.assertIn("self.root.configure(menu=self.menubar)", gui_code)
        self.assertIn('self.menubar.add_cascade(label="File"', gui_code)
        self.assertIn('command=support.on_new', gui_code)
        self.assertIn('accelerator="Ctrl+N"', gui_code)
        self.assertIn('variable=support.menu_autosave_var', gui_code)

        sup_code = CodeGenerator.generate_support_code(state, "menu_app")
        self.assertIn("def on_new():", sup_code)
        self.assertIn("menu_autosave_var = None", sup_code)

    def test_notebook_tabs_generation(self):
        """TNotebook generates tab frames and child widgets parented to specific tab frames."""
        state = ProjectState("Notebook App", 600, 400)
        nb = WidgetInstance.create("TNotebook", 10, 10, name_hint="main_nb")
        nb.properties["tabs"] = [
            {"id": "tab_home", "text": "Home"},
            {"id": "tab_profile", "text": "Profile"}
        ]
        state.add_widget(nb)

        child_btn = WidgetInstance.create("Button", 20, 20, name_hint="home_btn")
        child_btn.parent_id = nb.id
        child_btn.container_tab_or_pane = "0"
        state.add_widget(child_btn)

        gui_code = CodeGenerator.generate_gui_code(state, "nb_app", "nb_app_support")
        self.assertIn("self.main_nb = ttk.Notebook(self.root)", gui_code)
        self.assertIn("self.main_nb_t0 = ttk.Frame(self.main_nb)", gui_code)
        self.assertIn('self.main_nb.add(self.main_nb_t0, text="Home")', gui_code)
        self.assertIn("self.main_nb_t1 = ttk.Frame(self.main_nb)", gui_code)
        self.assertIn('self.main_nb.add(self.main_nb_t1, text="Profile")', gui_code)
        # child_btn parented to tab 0 frame
        self.assertIn("self.home_btn = ttk.Button(self.main_nb_t0", gui_code)

    def test_support_delimiters_and_reconciliation(self):
        """Reconciliation uses sentinels to replace variable block and preserve callbacks."""
        state = ProjectState("Reconcile App", 500, 400)
        entry = WidgetInstance.create("Entry", 10, 10, name_hint="username")
        entry.properties["text"] = "admin"
        state.add_widget(entry)

        # Initial support generation
        code1 = CodeGenerator.generate_support_code(state, "reconcile_app")
        self.assertIn(CodeGenerator.DELIM_BEGIN, code1)
        self.assertIn(CodeGenerator.DELIM_END, code1)
        self.assertIn("username_var = None", code1)
        self.assertIn('username_var = tk.StringVar(value="admin")', code1)

        # User adds custom logic to the file
        custom_code = code1 + "\n\ndef custom_helper():\n    return 'secret_token'\n"

        # Now add another widget in state
        chk = WidgetInstance.create("Checkbutton", 10, 50, name_hint="remember_me")
        chk.events["command"] = "on_toggle_remember"
        state.add_widget(chk)

        # Reconcile support code
        code2 = CodeGenerator.generate_support_code(state, "reconcile_app", custom_code)
        self.assertIn(CodeGenerator.DELIM_BEGIN, code2)
        self.assertIn(CodeGenerator.DELIM_END, code2)
        # Check that both variables are present in the updated block
        self.assertIn("username_var = None", code2)
        self.assertIn("remember_me_var = None", code2)
        # Check that custom user helper is preserved
        self.assertIn("def custom_helper():", code2)
        self.assertIn("return 'secret_token'", code2)
        # Check that new callback stub is appended
        self.assertIn("def on_toggle_remember():", code2)

if __name__ == "__main__":
    unittest.main()

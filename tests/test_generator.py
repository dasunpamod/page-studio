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

    def test_all_42_widgets_syntax_and_runtime_execution(self):
        """Generates full code for an extreme test project with all 42 widgets and executes it."""
        from pagestudio.core.models import WIDGET_CATALOG
        import subprocess
        import sys

        self.assertEqual(len(WIDGET_CATALOG), 42)
        state = ProjectState("All 42 Widgets App", 1000, 1000)

        for idx, (wtype, spec) in enumerate(WIDGET_CATALOG.items()):
            w = WidgetInstance.create(wtype, 10 + (idx % 3) * 300, 10 + (idx // 3) * 50, name_hint=f"{wtype.lower()}_{idx}")
            state.add_widget(w)

        with tempfile.TemporaryDirectory() as tmpdir:
            gui_path, sup_path = CodeGenerator.generate_all(state, "all_42_app", tmpdir)

            # 1. py_compile check
            py_compile.compile(gui_path, doraise=True)
            py_compile.compile(sup_path, doraise=True)

            # 2. Modify mainloop for fast headless termination
            with open(gui_path, "r", encoding="utf-8") as f:
                code = f.read()
            code = code.replace("root.mainloop()", "root.after(50, root.destroy)\n    root.mainloop()")
            with open(gui_path, "w", encoding="utf-8") as f:
                f.write(code)

            # 3. Subprocess execution
            env = os.environ.copy()
            env["PYTHONPATH"] = tmpdir + os.pathsep + env.get("PYTHONPATH", "")
            res = subprocess.run([sys.executable, gui_path], env=env, capture_output=True, text=True, timeout=5)
            self.assertEqual(res.returncode, 0, f"Process exited with error:\nSTDOUT:\n{res.stdout}\nSTDERR:\n{res.stderr}")

    def test_extreme_nesting_combinations_syntax_and_execution(self):
        """
        Test extreme nesting:
        A Toplevel containing a TNotebook, with tabs containing TPanedwindow,
        containing Frames, containing ScrolledTreeview, ScrolledText, Combobox, and Buttons.
        """
        import subprocess
        import sys

        state = ProjectState("Extreme Nesting App", 900, 700)

        # 1. Toplevel window
        top = WidgetInstance.create("Toplevel", 50, 50, name_hint="my_toplevel")
        top.width = 800
        top.height = 600
        state.add_widget(top)

        # 2. TNotebook inside Toplevel
        nb = WidgetInstance.create("TNotebook", 10, 10, name_hint="my_notebook")
        nb.width = 760
        nb.height = 540
        nb.parent_id = top.id
        nb.properties["tabs"] = [
            {"id": "tab1", "text": "Dashboard"},
            {"id": "tab2", "text": "Settings"}
        ]
        state.add_widget(nb)

        # 3. TPanedwindow inside Tab 0 of TNotebook
        pw = WidgetInstance.create("TPanedwindow", 10, 10, name_hint="my_paned")
        pw.width = 720
        pw.height = 480
        pw.parent_id = nb.id
        pw.container_tab_or_pane = "0"
        state.add_widget(pw)

        # 4. Frame inside TPanedwindow
        frame = WidgetInstance.create("Frame", 10, 10, name_hint="inner_frame")
        frame.width = 340
        frame.height = 450
        frame.parent_id = pw.id
        state.add_widget(frame)

        # 5. ScrolledTreeview inside Frame
        stree = WidgetInstance.create("Scrolledtreeview", 10, 10, name_hint="nested_tree")
        stree.width = 300
        stree.height = 120
        stree.parent_id = frame.id
        stree.properties["columns"] = [{"id": "col1", "heading": "ID"}, {"id": "col2", "heading": "Name"}]
        state.add_widget(stree)

        # 6. ScrolledText inside Frame
        stext = WidgetInstance.create("Scrolledtext", 10, 140, name_hint="nested_text")
        stext.width = 300
        stext.height = 100
        stext.parent_id = frame.id
        state.add_widget(stext)

        # 7. Combobox inside Frame
        cb = WidgetInstance.create("Combobox", 10, 250, name_hint="nested_combo")
        cb.width = 180
        cb.parent_id = frame.id
        state.add_widget(cb)

        # 8. Button inside Frame
        btn = WidgetInstance.create("Button", 10, 290, name_hint="nested_action_btn")
        btn.parent_id = frame.id
        btn.events["command"] = "on_extreme_click"
        state.add_widget(btn)

        with tempfile.TemporaryDirectory() as tmpdir:
            gui_path, sup_path = CodeGenerator.generate_all(state, "extreme_app", tmpdir)

            # Compile check
            py_compile.compile(gui_path, doraise=True)
            py_compile.compile(sup_path, doraise=True)

            with open(gui_path, "r", encoding="utf-8") as f:
                gui_code = f.read()

            # Verify hierarchy references
            self.assertIn("self.my_toplevel = tk.Toplevel(self.root)", gui_code)
            self.assertIn("self.my_toplevel.geometry(\"800x600+50+50\")", gui_code)
            self.assertIn("self.my_notebook = ttk.Notebook(self.my_toplevel)", gui_code)
            self.assertIn("self.my_paned = ttk.PanedWindow(self.my_notebook_t0", gui_code)
            self.assertIn("self.inner_frame = ttk.Frame(self.my_paned)", gui_code)
            self.assertIn("self.nested_tree_frame = ttk.Frame(self.inner_frame)", gui_code)
            self.assertIn("self.nested_text_frame = ttk.Frame(self.inner_frame)", gui_code)
            self.assertIn("self.nested_combo = ttk.Combobox(self.inner_frame", gui_code)
            self.assertIn("self.nested_action_btn = ttk.Button(self.inner_frame", gui_code)

            # Subprocess execution test
            gui_code_headless = gui_code.replace("root.mainloop()", "root.after(50, root.destroy)\n    root.mainloop()")
            with open(gui_path, "w", encoding="utf-8") as f:
                f.write(gui_code_headless)

            env = os.environ.copy()
            env["PYTHONPATH"] = tmpdir + os.pathsep + env.get("PYTHONPATH", "")
            res = subprocess.run([sys.executable, gui_path], env=env, capture_output=True, text=True, timeout=5)
            self.assertEqual(res.returncode, 0, f"Execution failed: {res.stderr}")

    def test_relative_mode_floats_no_none(self):
        """Verify relative placement emits valid non-None float values formatted cleanly."""
        state = ProjectState("Relative Floats App", 800, 600)
        state.is_relative_mode = True

        for i in range(5):
            w = WidgetInstance.create("Button", 50 * i, 40 * i, name_hint=f"btn_rel_{i}")
            # Leave rel_* values as None to verify automatic float calculation
            w.rel_x = None
            w.rel_y = None
            w.rel_width = None
            w.rel_height = None
            state.add_widget(w)

        gui_code = CodeGenerator.generate_gui_code(state, "rel_floats_app", "rel_floats_app_support")
        import re
        # Check place statement exists and does not contain None
        place_matches = re.findall(r"\.place\((.*?)\)", gui_code)
        self.assertGreater(len(place_matches), 0)
        for args in place_matches:
            self.assertNotIn("None", args)
            self.assertIn("relx=", args)
            self.assertIn("rely=", args)
            self.assertIn("relwidth=", args)
            self.assertIn("relheight=", args)
            # Verify float format e.g. 0.2500
            for param in ["relx", "rely", "relwidth", "relheight"]:
                m = re.search(rf"{param}=([0-9]+\.[0-9]+)", args)
                self.assertIsNotNone(m, f"Failed to match float for {param} in {args}")

    def test_menubar_complex_cascades_checkbuttons_radiobuttons(self):
        """Menubar with nested cascades, checkbuttons, radiobuttons, commands, accelerators."""
        state = ProjectState("Menu Rich App", 700, 500)

        item_open = MenuItemSpec(id="m_open", item_type="command", label="Open", command="cmd_open", accelerator="Ctrl+O")
        item_save = MenuItemSpec(id="m_save", item_type="command", label="Save", command="cmd_save", accelerator="Ctrl+S")
        cascade_file = MenuItemSpec(id="m_file", item_type="cascade", label="File", children=[item_open, item_save])

        item_chk = MenuItemSpec(id="m_chk", item_type="checkbutton", label="Word Wrap", variable="wrap_var", command="on_wrap_toggle")
        item_r1 = MenuItemSpec(id="m_r1", item_type="radiobutton", label="Light Mode", variable="theme_var", value="light")
        item_r2 = MenuItemSpec(id="m_r2", item_type="radiobutton", label="Dark Mode", variable="theme_var", value="dark")
        cascade_view = MenuItemSpec(id="m_view", item_type="cascade", label="View", children=[item_chk, item_r1, item_r2])

        menubar = MenuBarSpec(id="main_menu", items=[cascade_file, cascade_view])
        state.menus["main_menu"] = menubar

        gui_code = CodeGenerator.generate_gui_code(state, "menu_rich_app", "menu_rich_app_support")
        sup_code = CodeGenerator.generate_support_code(state, "menu_rich_app")

        # GUI verification
        self.assertIn('self.menubar.add_cascade(label="File"', gui_code)
        self.assertIn('self.menubar.add_cascade(label="View"', gui_code)
        self.assertIn('command=support.cmd_open', gui_code)
        self.assertIn('accelerator="Ctrl+O"', gui_code)
        self.assertIn('variable=support.wrap_var', gui_code)
        self.assertIn('variable=support.theme_var', gui_code)
        self.assertIn('value="light"', gui_code)
        self.assertIn('value="dark"', gui_code)

        # Support verification
        self.assertIn("wrap_var = None", sup_code)
        self.assertIn("theme_var = None", sup_code)
        self.assertIn("wrap_var = tk.BooleanVar(value=False)", sup_code)
        self.assertIn('theme_var = tk.StringVar(value="dark")', sup_code)
        self.assertIn("def cmd_open():", sup_code)
        self.assertIn("def cmd_save():", sup_code)
        self.assertIn("def on_wrap_toggle():", sup_code)

    def test_support_sentinel_replacement_and_user_code_untouched(self):
        """User code outside sentinels is preserved 100%, and new widgets add variables and stubs."""
        state = ProjectState("Preserve App", 400, 300)
        e1 = WidgetInstance.create("Entry", 10, 10, name_hint="username")
        state.add_widget(e1)

        code1 = CodeGenerator.generate_support_code(state, "preserve_app")

        # User adds custom import, function, and comment
        user_additions = (
            "# USER IMPORT\n"
            "import math\n\n"
            "# USER CUSTOM LOGIC\n"
            "def calculate_tax(amount):\n"
            "    return amount * 0.15\n"
        )
        existing = code1 + "\n" + user_additions

        # Add a new widget and re-generate
        b2 = WidgetInstance.create("Button", 10, 50, name_hint="submit_btn")
        b2.events["command"] = "on_submit_action"
        state.add_widget(b2)

        c3 = WidgetInstance.create("Checkbutton", 10, 90, name_hint="terms_agreed")
        state.add_widget(c3)

        code2 = CodeGenerator.generate_support_code(state, "preserve_app", existing)

        # Verify sentinels are intact
        self.assertEqual(code2.count(CodeGenerator.DELIM_BEGIN), 1)
        self.assertEqual(code2.count(CodeGenerator.DELIM_END), 1)

        # Verify new variables in the delimited block
        self.assertIn("username_var = None", code2)
        self.assertIn("terms_agreed_var = None", code2)

        # Verify user code is 100% untouched
        self.assertIn("# USER IMPORT\nimport math", code2)
        self.assertIn("def calculate_tax(amount):", code2)
        self.assertIn("return amount * 0.15", code2)

        # Verify new stub added
        self.assertIn("def on_submit_action():", code2)

if __name__ == "__main__":
    unittest.main()


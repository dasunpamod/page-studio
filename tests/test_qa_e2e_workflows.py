"""
PageStudio - End-to-End User Journeys QA Test Suite
Tests realistic, complex end-to-end developer workflows:
1. Journey 1: Building a Complete Multi-Tab Application
   - Instantiates ProjectState
   - Adds TNotebook with 3 tabs ("Overview", "Data Table", "Settings")
   - On "Overview": LabelFrame, 2 Labels, 2 Entries, Button with callback
   - On "Data Table": Scrolledtreeview with 4 columns (ID, Name, Role, Status) and Scrolledtext log
   - On "Settings": Checkbuttons, Radiobuttons, Combobox, and Scale
   - Menubar: File (New, Open, Save, Exit), Edit (Preferences), Help (About)
2. Journey 2: Persistence & Round-Trip Fidelity
   - Serializes project to .pgproj on disk
   - Loads back into fresh ProjectState
   - Asserts 100% property-by-property, hierarchy-by-hierarchy, and menu-by-menu identity
3. Journey 3: Production Code Export & Subprocess Execution
   - Exports project to temp directory (app.py and app_support.py)
   - Compiles both files with py_compile
   - Spawns python app.py in a headless subprocess
   - Asserts exit code is 0 and no exceptions during initialization
4. Journey 4: Support File Re-Export & Logic Preservation
   - Injects custom user logic into app_support.py (custom functions, modified callbacks, custom global state)
   - Adds a new widget with a new callback to the GUI
   - Re-exports the GUI
   - Asserts custom user code remains intact and new callback stub is cleanly appended
"""

import unittest
import os
import sys
import tempfile
import py_compile
import subprocess

from pagestudio.core.state import ProjectState
from pagestudio.core.models import WidgetInstance, MenuItemSpec, MenuBarSpec
from pagestudio.core.serializer import ProjectSerializer
from pagestudio.core.generator import CodeGenerator


class TestQAE2EWorkflows(unittest.TestCase):
    """E2E User Journeys QA Test Case for PageStudio."""

    def _build_multi_tab_project(self) -> ProjectState:
        """Helper to build the complete multi-tab enterprise application (Journey 1)."""
        state = ProjectState(title="Enterprise Multi-Tab Manager", width=900, height=650)
        state.resizable_x = True
        state.resizable_y = True
        state.grid_size = 10
        state.snap_to_grid = True

        # -------------------------------------------------------------
        # 1. TNotebook with 3 tabs: "Overview", "Data Table", "Settings"
        # -------------------------------------------------------------
        nb = WidgetInstance.create("TNotebook", 10, 10, name_hint="main_notebook")
        nb.width = 880
        nb.height = 600
        nb.properties["tabs"] = [
            {"id": "tab_overview", "text": "Overview"},
            {"id": "tab_data_table", "text": "Data Table"},
            {"id": "tab_settings", "text": "Settings"}
        ]
        state.add_widget(nb)

        # -------------------------------------------------------------
        # Tab 0: Overview
        # LabelFrame, 2 Labels, 2 Entries, and 1 Button with callback
        # -------------------------------------------------------------
        lf = WidgetInstance.create("LabelFrame", 20, 20, name_hint="overview_group")
        lf.width = 460
        lf.height = 280
        lf.properties["text"] = "Account Overview"
        lf.parent_id = nb.id
        lf.container_tab_or_pane = "0"
        state.add_widget(lf)

        lbl_user = WidgetInstance.create("Label", 20, 30, name_hint="lbl_username")
        lbl_user.properties["text"] = "Username:"
        lbl_user.parent_id = lf.id
        lbl_user.container_tab_or_pane = "0"
        state.add_widget(lbl_user)

        entry_user = WidgetInstance.create("Entry", 150, 30, name_hint="entry_username")
        entry_user.properties["text"] = "admin_user"
        entry_user.properties["variable"] = "username_var"
        entry_user.parent_id = lf.id
        entry_user.container_tab_or_pane = "0"
        state.add_widget(entry_user)

        lbl_email = WidgetInstance.create("Label", 20, 80, name_hint="lbl_email")
        lbl_email.properties["text"] = "Email Address:"
        lbl_email.parent_id = lf.id
        lbl_email.container_tab_or_pane = "0"
        state.add_widget(lbl_email)

        entry_email = WidgetInstance.create("Entry", 150, 80, name_hint="entry_email")
        entry_email.properties["text"] = "admin@enterprise.com"
        entry_email.properties["variable"] = "email_var"
        entry_email.parent_id = lf.id
        entry_email.container_tab_or_pane = "0"
        state.add_widget(entry_email)

        btn_submit = WidgetInstance.create("Button", 150, 140, name_hint="btn_save_profile")
        btn_submit.properties["text"] = "Save Profile"
        btn_submit.events["command"] = "on_save_profile_click"
        btn_submit.parent_id = lf.id
        btn_submit.container_tab_or_pane = "0"
        state.add_widget(btn_submit)

        # -------------------------------------------------------------
        # Tab 1: Data Table
        # Scrolledtreeview with 4 columns (ID, Name, Role, Status) and Scrolledtext log
        # -------------------------------------------------------------
        tree = WidgetInstance.create("Scrolledtreeview", 20, 20, name_hint="data_treeview")
        tree.width = 820
        tree.height = 250
        tree.properties["columns"] = [
            {"id": "id", "heading": "ID", "width": 80, "anchor": "center"},
            {"id": "name", "heading": "Name", "width": 220, "anchor": "w"},
            {"id": "role", "heading": "Role", "width": 180, "anchor": "w"},
            {"id": "status", "heading": "Status", "width": 120, "anchor": "center"}
        ]
        tree.parent_id = nb.id
        tree.container_tab_or_pane = "1"
        state.add_widget(tree)

        log = WidgetInstance.create("Scrolledtext", 20, 290, name_hint="activity_log")
        log.width = 820
        log.height = 240
        log.parent_id = nb.id
        log.container_tab_or_pane = "1"
        state.add_widget(log)

        # -------------------------------------------------------------
        # Tab 2: Settings
        # Checkbuttons, Radiobuttons, Combobox, Scale
        # -------------------------------------------------------------
        chk_alerts = WidgetInstance.create("Checkbutton", 20, 20, name_hint="chk_email_alerts")
        chk_alerts.properties["text"] = "Enable Email Alerts"
        chk_alerts.properties["variable"] = "email_alerts_var"
        chk_alerts.events["command"] = "on_toggle_alerts"
        chk_alerts.parent_id = nb.id
        chk_alerts.container_tab_or_pane = "2"
        state.add_widget(chk_alerts)

        chk_telem = WidgetInstance.create("Checkbutton", 20, 60, name_hint="chk_telemetry")
        chk_telem.properties["text"] = "Send Telemetry Data"
        chk_telem.properties["variable"] = "telemetry_var"
        chk_telem.events["command"] = "on_toggle_telemetry"
        chk_telem.parent_id = nb.id
        chk_telem.container_tab_or_pane = "2"
        state.add_widget(chk_telem)

        rad_prod = WidgetInstance.create("Radiobutton", 20, 110, name_hint="rad_env_prod")
        rad_prod.properties["text"] = "Production Server"
        rad_prod.properties["variable"] = "environment_var"
        rad_prod.properties["value"] = "production"
        rad_prod.events["command"] = "on_select_environment"
        rad_prod.parent_id = nb.id
        rad_prod.container_tab_or_pane = "2"
        state.add_widget(rad_prod)

        rad_stage = WidgetInstance.create("Radiobutton", 220, 110, name_hint="rad_env_stage")
        rad_stage.properties["text"] = "Staging Server"
        rad_stage.properties["variable"] = "environment_var"
        rad_stage.properties["value"] = "staging"
        rad_stage.events["command"] = "on_select_environment"
        rad_stage.parent_id = nb.id
        rad_stage.container_tab_or_pane = "2"
        state.add_widget(rad_stage)

        combo_theme = WidgetInstance.create("Combobox", 20, 160, name_hint="cmb_theme")
        combo_theme.properties["values"] = ["Default Light", "Nordic Dark", "Solarized", "High Contrast"]
        combo_theme.properties["variable"] = "theme_var"
        combo_theme.events["<<ComboboxSelected>>"] = "on_theme_changed"
        combo_theme.parent_id = nb.id
        combo_theme.container_tab_or_pane = "2"
        state.add_widget(combo_theme)

        scale_timeout = WidgetInstance.create("Scale", 20, 210, name_hint="scale_timeout")
        scale_timeout.properties["from_"] = 5
        scale_timeout.properties["to"] = 120
        scale_timeout.properties["orient"] = "horizontal"
        scale_timeout.properties["variable"] = "timeout_var"
        scale_timeout.events["command"] = "on_timeout_slide"
        scale_timeout.parent_id = nb.id
        scale_timeout.container_tab_or_pane = "2"
        state.add_widget(scale_timeout)

        # -------------------------------------------------------------
        # Full Menubar:
        # File -> New, Open, Save, Exit; Edit -> Preferences; Help -> About
        # -------------------------------------------------------------
        file_new = MenuItemSpec(id="m_file_new", item_type="command", label="New", command="on_file_new", accelerator="Ctrl+N")
        file_open = MenuItemSpec(id="m_file_open", item_type="command", label="Open", command="on_file_open", accelerator="Ctrl+O")
        file_save = MenuItemSpec(id="m_file_save", item_type="command", label="Save", command="on_file_save", accelerator="Ctrl+S")
        file_sep = MenuItemSpec(id="m_file_sep", item_type="separator")
        file_exit = MenuItemSpec(id="m_file_exit", item_type="command", label="Exit", command="on_file_exit", accelerator="Alt+F4")
        file_cascade = MenuItemSpec(id="m_cascade_file", item_type="cascade", label="File", children=[file_new, file_open, file_save, file_sep, file_exit])

        edit_pref = MenuItemSpec(id="m_edit_pref", item_type="command", label="Preferences", command="on_edit_preferences", accelerator="Ctrl+,")
        edit_cascade = MenuItemSpec(id="m_cascade_edit", item_type="cascade", label="Edit", children=[edit_pref])

        help_about = MenuItemSpec(id="m_help_about", item_type="command", label="About", command="on_help_about")
        help_cascade = MenuItemSpec(id="m_cascade_help", item_type="cascade", label="Help", children=[help_about])

        menubar = MenuBarSpec(id="main_menu", name="main_menu", items=[file_cascade, edit_cascade, help_cascade])
        state.menus["main_menu"] = menubar

        return state

    # =========================================================================
    # Journey 1: Building a Complete Multi-Tab Application
    # =========================================================================
    def test_journey_1_multi_tab_application_construction(self):
        """Journey 1: Build a complex multi-tab application and assert structural completeness."""
        state = self._build_multi_tab_project()

        # Assert Project Window properties
        self.assertEqual(state.title, "Enterprise Multi-Tab Manager")
        self.assertEqual(state.width, 900)
        self.assertEqual(state.height, 650)
        self.assertTrue(state.resizable_x)
        self.assertTrue(state.resizable_y)

        # Assert Notebook exists with 3 tabs
        nb_widgets = [w for w in state.widgets.values() if w.widget_type == "TNotebook"]
        self.assertEqual(len(nb_widgets), 1)
        nb = nb_widgets[0]
        tabs = nb.properties.get("tabs", [])
        self.assertEqual(len(tabs), 3)
        tab_texts = [t["text"] if isinstance(t, dict) else str(t) for t in tabs]
        self.assertEqual(tab_texts, ["Overview", "Data Table", "Settings"])

        # Assert Overview tab widgets: LabelFrame, 2 Labels, 2 Entries, Button
        overview_lf = [w for w in state.widgets.values() if w.widget_type == "LabelFrame" and w.container_tab_or_pane == "0"]
        self.assertEqual(len(overview_lf), 1)
        lf_id = overview_lf[0].id

        overview_labels = [w for w in state.widgets.values() if w.widget_type == "Label" and w.parent_id == lf_id]
        self.assertEqual(len(overview_labels), 2)

        overview_entries = [w for w in state.widgets.values() if w.widget_type == "Entry" and w.parent_id == lf_id]
        self.assertEqual(len(overview_entries), 2)

        overview_buttons = [w for w in state.widgets.values() if w.widget_type == "Button" and w.parent_id == lf_id]
        self.assertEqual(len(overview_buttons), 1)
        self.assertIn("command", overview_buttons[0].events)
        self.assertEqual(overview_buttons[0].events["command"], "on_save_profile_click")

        # Assert Data Table tab widgets: Scrolledtreeview with 4 columns, Scrolledtext log
        data_trees = [w for w in state.widgets.values() if w.widget_type == "Scrolledtreeview" and w.container_tab_or_pane == "1"]
        self.assertEqual(len(data_trees), 1)
        cols = data_trees[0].properties.get("columns", [])
        self.assertEqual(len(cols), 4)
        col_headings = [c["heading"] if isinstance(c, dict) else str(c) for c in cols]
        self.assertEqual(col_headings, ["ID", "Name", "Role", "Status"])

        data_logs = [w for w in state.widgets.values() if w.widget_type == "Scrolledtext" and w.container_tab_or_pane == "1"]
        self.assertEqual(len(data_logs), 1)

        # Assert Settings tab widgets: Checkbuttons, Radiobuttons, Combobox, Scale
        settings_checks = [w for w in state.widgets.values() if w.widget_type == "Checkbutton" and w.container_tab_or_pane == "2"]
        self.assertGreaterEqual(len(settings_checks), 2)

        settings_radios = [w for w in state.widgets.values() if w.widget_type == "Radiobutton" and w.container_tab_or_pane == "2"]
        self.assertGreaterEqual(len(settings_radios), 2)

        settings_combos = [w for w in state.widgets.values() if w.widget_type == "Combobox" and w.container_tab_or_pane == "2"]
        self.assertEqual(len(settings_combos), 1)

        settings_scales = [w for w in state.widgets.values() if w.widget_type == "Scale" and w.container_tab_or_pane == "2"]
        self.assertEqual(len(settings_scales), 1)

        # Assert Full Menubar
        self.assertIn("main_menu", state.menus)
        menu_items = state.menus["main_menu"].items
        cascade_labels = [item.label for item in menu_items if item.item_type == "cascade"]
        self.assertIn("File", cascade_labels)
        self.assertIn("Edit", cascade_labels)
        self.assertIn("Help", cascade_labels)

        file_cascade = next(item for item in menu_items if item.label == "File")
        file_commands = [c.label for c in file_cascade.children if c.item_type == "command"]
        self.assertIn("New", file_commands)
        self.assertIn("Open", file_commands)
        self.assertIn("Save", file_commands)
        self.assertIn("Exit", file_commands)

        edit_cascade = next(item for item in menu_items if item.label == "Edit")
        edit_commands = [c.label for c in edit_cascade.children if c.item_type == "command"]
        self.assertIn("Preferences", edit_commands)

        help_cascade = next(item for item in menu_items if item.label == "Help")
        help_commands = [c.label for c in help_cascade.children if c.item_type == "command"]
        self.assertIn("About", help_commands)

    # =========================================================================
    # Journey 2: Persistence & Round-Trip Fidelity
    # =========================================================================
    def test_journey_2_persistence_round_trip_fidelity(self):
        """Journey 2: Serializes to disk and asserts 100% identity property-by-property, hierarchy, and menus."""
        original_state = self._build_multi_tab_project()

        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = os.path.join(tmpdir, "enterprise_app.pgproj")
            ProjectSerializer.save_to_file(original_state, file_path)
            self.assertTrue(os.path.exists(file_path))
            self.assertGreater(os.path.getsize(file_path), 0)

            loaded_state = ProjectSerializer.load_from_file(file_path)

            # 1. Window & Canvas Properties Identity
            self.assertEqual(loaded_state.title, original_state.title)
            self.assertEqual(loaded_state.width, original_state.width)
            self.assertEqual(loaded_state.height, original_state.height)
            self.assertEqual(loaded_state.resizable_x, original_state.resizable_x)
            self.assertEqual(loaded_state.resizable_y, original_state.resizable_y)
            self.assertEqual(loaded_state.grid_size, original_state.grid_size)
            self.assertEqual(loaded_state.snap_to_grid, original_state.snap_to_grid)
            self.assertEqual(loaded_state.is_relative_mode, original_state.is_relative_mode)

            # 2. Hierarchy & Order Identity
            self.assertEqual(len(loaded_state.widgets), len(original_state.widgets))
            self.assertEqual(loaded_state.widget_order, original_state.widget_order)

            # 3. Property-by-Property Widget Identity
            for wid, orig_w in original_state.widgets.items():
                self.assertIn(wid, loaded_state.widgets)
                load_w = loaded_state.widgets[wid]

                self.assertEqual(load_w.id, orig_w.id)
                self.assertEqual(load_w.widget_type, orig_w.widget_type)
                self.assertEqual(load_w.name, orig_w.name)
                self.assertEqual(load_w.x, orig_w.x)
                self.assertEqual(load_w.y, orig_w.y)
                self.assertEqual(load_w.width, orig_w.width)
                self.assertEqual(load_w.height, orig_w.height)
                self.assertEqual(load_w.parent_id, orig_w.parent_id)
                self.assertEqual(load_w.container_tab_or_pane, orig_w.container_tab_or_pane)
                self.assertEqual(load_w.properties, orig_w.properties)
                self.assertEqual(load_w.events, orig_w.events)
                self.assertEqual(load_w.locked, orig_w.locked)
                self.assertEqual(load_w.z_order, orig_w.z_order)
                self.assertEqual(load_w.is_relative, orig_w.is_relative)
                self.assertEqual(load_w.rel_x, orig_w.rel_x)
                self.assertEqual(load_w.rel_y, orig_w.rel_y)
                self.assertEqual(load_w.rel_width, orig_w.rel_width)
                self.assertEqual(load_w.rel_height, orig_w.rel_height)

                # Check children hierarchy preserved identically
                orig_children = [c.id for c in original_state.get_children(wid)]
                load_children = [c.id for c in loaded_state.get_children(wid)]
                self.assertEqual(load_children, orig_children)

            # 4. Menu-by-Menu Identity
            self.assertEqual(set(loaded_state.menus.keys()), set(original_state.menus.keys()))
            for mkey, orig_m in original_state.menus.items():
                load_m = loaded_state.menus[mkey]
                self.assertEqual(load_m.id, orig_m.id)
                self.assertEqual(load_m.name, orig_m.name)
                self.assertEqual(load_m.to_dict(), orig_m.to_dict())

            # 5. Full Dictionary Deep Serialization Identity
            d_orig = ProjectSerializer.to_dict(original_state)
            d_load = ProjectSerializer.to_dict(loaded_state)
            self.assertEqual(d_load, d_orig)

    # =========================================================================
    # Journey 3: Production Code Export & Subprocess Execution
    # =========================================================================
    def test_journey_3_production_export_and_subprocess_execution(self):
        """Journey 3: Export production code, compile with py_compile, spawn headless subprocess, assert exit 0."""
        state = self._build_multi_tab_project()

        with tempfile.TemporaryDirectory() as tmpdir:
            gui_path, sup_path = CodeGenerator.generate_all(state, "app", tmpdir)

            self.assertTrue(os.path.exists(gui_path))
            self.assertTrue(os.path.exists(sup_path))

            # Compile both generated files with py_compile
            try:
                py_compile.compile(gui_path, doraise=True)
                py_compile.compile(sup_path, doraise=True)
            except py_compile.PyCompileError as exc:
                self.fail(f"Production code failed py_compile: {exc}")

            # Verify contents of generated GUI code
            with open(gui_path, "r", encoding="utf-8") as f:
                gui_code = f.read()

            self.assertIn("class MainApp:", gui_code)
            self.assertIn("self.main_notebook = ttk.Notebook(self.root)", gui_code)
            self.assertIn('self.main_notebook.add(self.main_notebook_t0, text="Overview")', gui_code)
            self.assertIn('self.main_notebook.add(self.main_notebook_t1, text="Data Table")', gui_code)
            self.assertIn('self.main_notebook.add(self.main_notebook_t2, text="Settings")', gui_code)
            self.assertIn("self.overview_group = ttk.LabelFrame(self.main_notebook_t0", gui_code)
            self.assertIn("self.btn_save_profile = ttk.Button(self.overview_group", gui_code)
            self.assertIn("self.data_treeview = ttk.Treeview(self.data_treeview_frame", gui_code)
            self.assertIn("self.activity_log = tk.Text(self.activity_log_frame", gui_code)
            self.assertIn("self.chk_email_alerts = ttk.Checkbutton(self.main_notebook_t2", gui_code)
            self.assertIn("self.menubar = tk.Menu(self.root)", gui_code)

            # Spawn `python app.py` in a headless subprocess
            env = os.environ.copy()
            env["PAGESTUDIO_HEADLESS"] = "150"
            env["PYTHONPATH"] = tmpdir + os.pathsep + env.get("PYTHONPATH", "")

            proc = subprocess.run(
                [sys.executable, gui_path],
                cwd=tmpdir,
                env=env,
                capture_output=True,
                text=True,
                timeout=10
            )

            self.assertEqual(
                proc.returncode, 0,
                f"Generated application subprocess exited with non-zero code {proc.returncode}.\nSTDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}"
            )
            # Assert no runtime exceptions or tracebacks in stderr
            self.assertNotIn("Traceback (most recent call last):", proc.stderr)
            self.assertNotIn("Exception", proc.stderr)

    # =========================================================================
    # Journey 4: Support File Re-Export & Logic Preservation
    # =========================================================================
    def test_journey_4_support_file_reexport_logic_preservation(self):
        """Journey 4: Injects custom logic, adds new widget + callback, re-exports, asserts preservation & clean append."""
        state = self._build_multi_tab_project()

        with tempfile.TemporaryDirectory() as tmpdir:
            gui_path, sup_path = CodeGenerator.generate_all(state, "app", tmpdir)

            # Read initial generated support code
            with open(sup_path, "r", encoding="utf-8") as f:
                initial_sup_code = f.read()

            # Inject custom user logic:
            # 1. Custom global state
            # 2. Custom helper function
            # 3. Modified callback implementation
            custom_code_additions = (
                "\n"
                "# ==========================================================================\n"
                "# USER CUSTOM BUSINESS LOGIC & STATE (DO NOT OVERWRITE)\n"
                "# ==========================================================================\n"
                "USER_GLOBAL_AUDIT_STATE = {\n"
                '    "session_id": "SES-987654",\n'
                '    "audit_records": 105,\n'
                '    "active": True,\n'
                '    "custom_counter": 42\n'
                "}\n\n"
                "def calculate_telemetry_digest(record_count, factor=1.5):\n"
                '    """Custom helper function calculating telemetry metrics."""\n'
                "    return int(record_count * factor) + 7\n\n"
            )

            # Modify on_save_profile_click implementation to use the custom state
            modified_sup_code = initial_sup_code + custom_code_additions
            modified_sup_code = modified_sup_code.replace(
                "def on_save_profile_click():\n    \"\"\"Callback handler for on_save_profile_click\"\"\"\n    print(\"[Callback] on_save_profile_click triggered\")\n    # TODO: Implement your application logic here\n    pass",
                "def on_save_profile_click():\n    \"\"\"Modified custom profile save handler.\"\"\"\n    global USER_GLOBAL_AUDIT_STATE\n    USER_GLOBAL_AUDIT_STATE[\"custom_counter\"] += 1\n    print(f\"[Custom Logic] Profile saved, counter={USER_GLOBAL_AUDIT_STATE['custom_counter']}\")"
            )

            with open(sup_path, "w", encoding="utf-8") as f:
                f.write(modified_sup_code)

            # Add a new widget with a brand new callback to the GUI
            btn_audit = WidgetInstance.create("Button", 300, 140, name_hint="btn_run_audit")
            btn_audit.properties["text"] = "Run Security Audit"
            btn_audit.events["command"] = "on_run_security_audit_click"
            nb_id = next(wid for wid, w in state.widgets.items() if w.widget_type == "TNotebook")
            btn_audit.parent_id = nb_id
            btn_audit.container_tab_or_pane = "0"
            state.add_widget(btn_audit)

            # Re-export project
            re_gui_path, re_sup_path = CodeGenerator.generate_all(state, "app", tmpdir)

            # Read re-exported support code
            with open(re_sup_path, "r", encoding="utf-8") as f:
                final_sup_code = f.read()

            # Compile both re-exported files
            py_compile.compile(re_gui_path, doraise=True)
            py_compile.compile(re_sup_path, doraise=True)

            # Assert custom global state remains intact
            self.assertIn("USER_GLOBAL_AUDIT_STATE = {", final_sup_code)
            self.assertIn('"session_id": "SES-987654"', final_sup_code)
            self.assertIn('"custom_counter": 42', final_sup_code)

            # Assert custom helper function remains intact
            self.assertIn("def calculate_telemetry_digest(record_count, factor=1.5):", final_sup_code)
            self.assertIn("return int(record_count * factor) + 7", final_sup_code)

            # Assert modified callback implementation remains intact
            self.assertIn("def on_save_profile_click():", final_sup_code)
            self.assertIn('USER_GLOBAL_AUDIT_STATE["custom_counter"] += 1', final_sup_code)

            # Assert newly added callback stub is cleanly appended
            self.assertIn("def on_run_security_audit_click():", final_sup_code)
            self.assertIn('"""Callback handler for on_run_security_audit_click"""', final_sup_code)

            # Subprocess execution test of re-exported app
            env = os.environ.copy()
            env["PAGESTUDIO_HEADLESS"] = "150"
            env["PYTHONPATH"] = tmpdir + os.pathsep + env.get("PYTHONPATH", "")

            proc = subprocess.run(
                [sys.executable, re_gui_path],
                cwd=tmpdir,
                env=env,
                capture_output=True,
                text=True,
                timeout=10
            )
            self.assertEqual(proc.returncode, 0, f"Re-exported app execution failed: {proc.stderr}")
            self.assertNotIn("Traceback (most recent call last):", proc.stderr)

    # =========================================================================
    # Integrated Master E2E Workflow Test
    # =========================================================================
    def test_complete_integrated_e2e_journey(self):
        """Executes all 4 journeys sequentially in a single end-to-end user workflow."""
        # 1. Journey 1: Construction
        state = self._build_multi_tab_project()
        self.assertEqual(len(state.widgets), 15)
        self.assertIn("main_menu", state.menus)

        with tempfile.TemporaryDirectory() as tmpdir:
            # 2. Journey 2: Persistence & Round-Trip
            proj_file = os.path.join(tmpdir, "master_journey.pgproj")
            ProjectSerializer.save_to_file(state, proj_file)
            reloaded_state = ProjectSerializer.load_from_file(proj_file)
            self.assertEqual(
                ProjectSerializer.to_dict(reloaded_state),
                ProjectSerializer.to_dict(state)
            )

            # 3. Journey 3: Production Export & Subprocess Execution
            gui_file, sup_file = CodeGenerator.generate_all(reloaded_state, "app", tmpdir)
            py_compile.compile(gui_file, doraise=True)
            py_compile.compile(sup_file, doraise=True)

            env = os.environ.copy()
            env["PAGESTUDIO_HEADLESS"] = "150"
            env["PYTHONPATH"] = tmpdir + os.pathsep + env.get("PYTHONPATH", "")
            res1 = subprocess.run([sys.executable, gui_file], cwd=tmpdir, env=env, capture_output=True, text=True, timeout=10)
            self.assertEqual(res1.returncode, 0)

            # 4. Journey 4: Custom Logic Injection & Re-Export
            with open(sup_file, "a", encoding="utf-8") as f:
                f.write("\nCUSTOM_FLAG = True\ndef custom_helper():\n    return 100\n")

            new_btn = WidgetInstance.create("Button", 10, 10, name_hint="new_btn")
            new_btn.events["command"] = "on_new_btn_click"
            reloaded_state.add_widget(new_btn)

            re_gui, re_sup = CodeGenerator.generate_all(reloaded_state, "app", tmpdir)
            with open(re_sup, "r", encoding="utf-8") as f:
                content = f.read()

            self.assertIn("CUSTOM_FLAG = True", content)
            self.assertIn("def custom_helper():", content)
            self.assertIn("def on_new_btn_click():", content)

            py_compile.compile(re_gui, doraise=True)
            py_compile.compile(re_sup, doraise=True)
            res2 = subprocess.run([sys.executable, re_gui], cwd=tmpdir, env=env, capture_output=True, text=True, timeout=10)
            self.assertEqual(res2.returncode, 0)


if __name__ == "__main__":
    unittest.main()

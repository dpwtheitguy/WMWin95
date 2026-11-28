PYTHON ?= python3
.PHONY: check-themes check-printer-wizard check-printer-installation-backend check-namespace-modal-ghost check-shortcut-visuals check-namespace-drop-prompt check-printers-shell check-namespace-rearrange check-dnd-feel check-popup-dismissal check-gtk-scrollbars check-accessibility check-scrollbar-tracks check-control-panel-layout check-command-buttons check test check-ui check-menu-seams check-sprint-controls check-computer-view check-mouse check-pointer-catalog check-selection-details check-control-panel check-sounds check-multimedia check-volume-popup check-fonts stage reference-plan native
native:
	$(PYTHON) dev/build_native.py
check:
	$(PYTHON) dev/check.py
test:
	$(PYTHON) -m unittest discover -s tests -v
	$(PYTHON) -m compileall -q tools dev src
check-menu-seams:
	GDK_BACKEND=x11 xvfb-run -a $(PYTHON) dev/check_menu_seams.py
check-sprint-controls:
	$(PYTHON) dev/run_sprint_checks.py --python "$(PYTHON)"
check-computer-view:
	GDK_BACKEND=x11 xvfb-run -a -s '-screen 0 800x600x24' $(PYTHON) dev/check_computer_view.py
	GDK_BACKEND=x11 xvfb-run -a -s '-screen 0 1280x720x24' $(PYTHON) dev/check_computer_view.py
check-selection-details:
	GDK_BACKEND=x11 xvfb-run -a -s '-screen 0 800x600x24' $(PYTHON) dev/check_selection_details.py
	GDK_BACKEND=x11 xvfb-run -a -s '-screen 0 1280x720x24' $(PYTHON) dev/check_selection_details.py
check-mouse:
	GDK_BACKEND=x11 xvfb-run -a -s '-screen 0 800x600x24' $(PYTHON) dev/check_mouse.py --output private/screenshots/mouse-$$(date +%s%N)-800
	GDK_BACKEND=x11 xvfb-run -a -s '-screen 0 1280x720x24' $(PYTHON) dev/check_mouse.py --output private/screenshots/mouse-$$(date +%s%N)-1280
check-pointer-catalog:
	GDK_BACKEND=x11 xvfb-run -a -s '-screen 0 800x600x24' $(PYTHON) dev/check_pointer_catalog.py --output private/screenshots/pointers-$$(date +%s%N)-800
	GDK_BACKEND=x11 xvfb-run -a -s '-screen 0 1280x720x24' $(PYTHON) dev/check_pointer_catalog.py --output private/screenshots/pointers-$$(date +%s%N)-1280
check-control-panel:
	GDK_BACKEND=x11 xvfb-run -a -s '-screen 0 800x600x24' $(PYTHON) dev/check_control_panel.py --output private/screenshots/control-panel-$$(date +%s%N)-800
	GDK_BACKEND=x11 xvfb-run -a -s '-screen 0 1280x720x24' $(PYTHON) dev/check_control_panel.py --output private/screenshots/control-panel-$$(date +%s%N)-1280
check-ui: check-themes check-printer-wizard check-namespace-modal-ghost check-shortcut-visuals check-namespace-drop-prompt check-namespace-rearrange check-printers-shell check-dnd-feel check-popup-dismissal check-gtk-scrollbars check-accessibility check-scrollbar-tracks check-control-panel-layout check-command-buttons check-fonts check-multimedia check-volume-popup check-sounds check-control-panel check-pointer-catalog check-mouse check-menu-seams check-sprint-controls check-computer-view check-selection-details
	GDK_BACKEND=x11 xvfb-run -a -s '-screen 0 800x600x24' $(PYTHON) dev/check_folder_windows.py
	GDK_BACKEND=x11 xvfb-run -a -s '-screen 0 1280x720x24' $(PYTHON) dev/check_folder_windows.py
	GDK_BACKEND=x11 xvfb-run -a -s '-screen 0 800x600x24' $(PYTHON) dev/check_file_dialogs.py
	GDK_BACKEND=x11 xvfb-run -a -s '-screen 0 1280x720x24' $(PYTHON) dev/check_file_dialogs.py
	GDK_BACKEND=x11 xvfb-run -a -s '-screen 0 800x600x24' $(PYTHON) dev/check_reference_ui.py
	GDK_BACKEND=x11 xvfb-run -a -s '-screen 0 1280x720x24' $(PYTHON) dev/check_reference_ui.py --size 1280x720
stage:
	$(PYTHON) dev/stage_xfce.py
reference-plan:
	$(PYTHON) tools/reference_vm.py --iso "$(HOME)/Downloads/Windows 95C.iso"

check-sounds:
	GDK_BACKEND=x11 xvfb-run -a -s '-screen 0 800x600x24' $(PYTHON) dev/check_sounds.py --output private/screenshots/sounds-$$(date +%s%N)-800
	GDK_BACKEND=x11 xvfb-run -a -s '-screen 0 1280x720x24' $(PYTHON) dev/check_sounds.py --output private/screenshots/sounds-$$(date +%s%N)-1280

check-multimedia:
	GDK_BACKEND=x11 xvfb-run -a -s '-screen 0 800x600x24' $(PYTHON) dev/check_multimedia.py --output private/screenshots/multimedia-$$(date +%s%N)-800
	GDK_BACKEND=x11 xvfb-run -a -s '-screen 0 1280x720x24' $(PYTHON) dev/check_multimedia.py --output private/screenshots/multimedia-$$(date +%s%N)-1280

check-volume-popup:
	GDK_BACKEND=x11 xvfb-run -a -s '-screen 0 800x600x24' $(PYTHON) dev/check_volume_popup.py --output private/screenshots/volume-$$(date +%s%N)-800
	GDK_BACKEND=x11 xvfb-run -a -s '-screen 0 1280x720x24' $(PYTHON) dev/check_volume_popup.py --output private/screenshots/volume-$$(date +%s%N)-1280

check-fonts:
	GDK_BACKEND=x11 xvfb-run -a -s '-screen 0 800x600x24' $(PYTHON) dev/check_fonts.py --output private/screenshots/fonts-$$(date +%s%N)-800
	GDK_BACKEND=x11 xvfb-run -a -s '-screen 0 1280x720x24' $(PYTHON) dev/check_fonts.py --output private/screenshots/fonts-$$(date +%s%N)-1280

check-command-buttons:
	$(PYTHON) dev/check_command_buttons.py --output private/screenshots/command-buttons-$$(date +%s%N)-800 --size 800x600
	$(PYTHON) dev/check_command_buttons.py --output private/screenshots/command-buttons-$$(date +%s%N)-1280 --size 1280x720

check-control-panel-layout:
	GDK_BACKEND=x11 xvfb-run -a -s '-screen 0 800x600x24' $(PYTHON) dev/research/check_control_panel_layout.py --output private/screenshots/control-layout-$$(date +%s%N)-800
	GDK_BACKEND=x11 xvfb-run -a -s '-screen 0 1280x720x24' $(PYTHON) dev/research/check_control_panel_layout.py --output private/screenshots/control-layout-$$(date +%s%N)-1280

check-scrollbar-tracks:
	GDK_BACKEND=x11 xvfb-run -a -s '-screen 0 800x600x24' $(PYTHON) dev/check_scrollbar_tracks.py --output private/screenshots/scrollbar-tracks-$$(date +%s%N)-800
	GDK_BACKEND=x11 xvfb-run -a -s '-screen 0 1280x720x24' $(PYTHON) dev/check_scrollbar_tracks.py --output private/screenshots/scrollbar-tracks-$$(date +%s%N)-1280

check-accessibility:
	GDK_BACKEND=x11 $(PYTHON) dev/check_accessibility.py --resolution 800x600 --output private/screenshots/accessibility-$$(date +%s%N)-800
	GDK_BACKEND=x11 $(PYTHON) dev/check_accessibility.py --resolution 1280x800 --output private/screenshots/accessibility-$$(date +%s%N)-1280

check-popup-dismissal:
	GDK_BACKEND=x11 xvfb-run -a -s '-screen 0 800x600x24' $(PYTHON) dev/check_popup_dismissal.py --output private/screenshots/popup-dismissal-$$(date +%s%N)-800
	GDK_BACKEND=x11 xvfb-run -a -s '-screen 0 1280x720x24' $(PYTHON) dev/check_popup_dismissal.py --output private/screenshots/popup-dismissal-$$(date +%s%N)-1280

check-gtk-scrollbars:
	GDK_BACKEND=x11 GDK_SCALE=1 xvfb-run -a -s '-screen 0 800x600x24' $(PYTHON) dev/check_gtk_scrollbars.py --output private/screenshots/gtk-scrollbars-$$(date +%s%N)-800-1x
	GDK_BACKEND=x11 GDK_SCALE=1 xvfb-run -a -s '-screen 0 1280x720x24' $(PYTHON) dev/check_gtk_scrollbars.py --output private/screenshots/gtk-scrollbars-$$(date +%s%N)-1280-1x
	GDK_BACKEND=x11 GDK_SCALE=2 xvfb-run -a -s '-screen 0 800x600x24' $(PYTHON) dev/check_gtk_scrollbars.py --output private/screenshots/gtk-scrollbars-$$(date +%s%N)-800-2x
	GDK_BACKEND=x11 GDK_SCALE=2 xvfb-run -a -s '-screen 0 1280x720x24' $(PYTHON) dev/check_gtk_scrollbars.py --output private/screenshots/gtk-scrollbars-$$(date +%s%N)-1280-2x

check-dnd-feel:
	GDK_BACKEND=x11 $(PYTHON) dev/check_dnd_feel.py --resolution 800x600 --output private/screenshots/dnd-feel-$$(date +%s%N)-800
	GDK_BACKEND=x11 $(PYTHON) dev/check_dnd_feel.py --resolution 1280x800 --output private/screenshots/dnd-feel-$$(date +%s%N)-1280

check-printers-shell:
	GDK_BACKEND=x11 xvfb-run -a -s '-screen 0 800x600x24' $(PYTHON) dev/check_printers_shell.py --output private/screenshots/printers-shell-$$(date +%s%N)-800
	GDK_BACKEND=x11 xvfb-run -a -s '-screen 0 1280x720x24' $(PYTHON) dev/check_printers_shell.py --output private/screenshots/printers-shell-$$(date +%s%N)-1280

check-namespace-rearrange:
	env -u WAYLAND_DISPLAY GDK_BACKEND=x11 xvfb-run -a -s '-screen 0 800x600x24' $(PYTHON) dev/check_namespace_rearrange.py --output private/screenshots/namespace-rearrange-$$(date +%s%N)-800
	env -u WAYLAND_DISPLAY GDK_BACKEND=x11 xvfb-run -a -s '-screen 0 1280x720x24' $(PYTHON) dev/check_namespace_rearrange.py --output private/screenshots/namespace-rearrange-$$(date +%s%N)-1280

check-shortcut-visuals:
	$(PYTHON) dev/check_shortcut_visuals.py --profile classic --output private/screenshots/shortcut-visuals-$$(date +%s%N)-classic
	env -u WAYLAND_DISPLAY GDK_BACKEND=x11 xvfb-run -a -s '-screen 0 800x600x24' $(PYTHON) dev/check_shortcut_visuals.py --profile ie4 --shell --output private/screenshots/shortcut-visuals-$$(date +%s%N)-800
	env -u WAYLAND_DISPLAY GDK_BACKEND=x11 xvfb-run -a -s '-screen 0 1280x720x24' $(PYTHON) dev/check_shortcut_visuals.py --profile ie4 --shell --output private/screenshots/shortcut-visuals-$$(date +%s%N)-1280

check-namespace-drop-prompt:
	env -u WAYLAND_DISPLAY GDK_BACKEND=x11 xvfb-run -a -s '-screen 0 800x600x24' $(PYTHON) dev/check_namespace_drop_prompt.py --output private/screenshots/namespace-drop-prompt-$$(date +%s%N)-800
	env -u WAYLAND_DISPLAY GDK_BACKEND=x11 xvfb-run -a -s '-screen 0 1280x720x24' $(PYTHON) dev/check_namespace_drop_prompt.py --output private/screenshots/namespace-drop-prompt-$$(date +%s%N)-1280

check-namespace-modal-ghost:
	env -u WAYLAND_DISPLAY GDK_BACKEND=x11 xvfb-run -a -s '-screen 0 800x600x24' $(PYTHON) dev/check_namespace_modal_ghost.py --output private/screenshots/modal-ghost-$$(date +%s%N)-800
	env -u WAYLAND_DISPLAY GDK_BACKEND=x11 xvfb-run -a -s '-screen 0 1280x720x24' $(PYTHON) dev/check_namespace_modal_ghost.py --output private/screenshots/modal-ghost-$$(date +%s%N)-1280

check-themes:
	$(PYTHON) dev/check_themes.py --palette truecolor --size 800x600 --output private/screenshots/themes-truecolor-$$(date +%s%N)-800
	$(PYTHON) dev/check_themes.py --palette truecolor --size 1280x720 --output private/screenshots/themes-truecolor-$$(date +%s%N)-1280
	$(PYTHON) dev/check_themes.py --palette 256 --size 800x600 --output private/screenshots/themes-256-$$(date +%s%N)-800
	$(PYTHON) dev/check_themes.py --palette 256 --size 1280x720 --output private/screenshots/themes-256-$$(date +%s%N)-1280

check-printer-wizard:
	GDK_BACKEND=x11 xvfb-run -a -s '-screen 0 800x600x24' $(PYTHON) dev/check_printer_wizard.py --output private/screenshots/printer-wizard-$$(date +%s%N)-800
	GDK_BACKEND=x11 xvfb-run -a -s '-screen 0 1280x720x24' $(PYTHON) dev/check_printer_wizard.py --output private/screenshots/printer-wizard-$$(date +%s%N)-1280

check-printer-installation-backend:
	$(PYTHON) dev/check_printer_installation_backend.py --owned-guest-service --output private/screenshots/printer-installation-$$(date +%s%N)

.PHONY: check-theme-customization check-theme-appearance check-screen-saver check-theme-import
check-ui: check-theme-customization check-theme-appearance check-screen-saver check-theme-import
check-theme-customization:
	$(PYTHON) dev/check_theme_customization.py --size 800x600 --output private/screenshots/theme-customization-$$(date +%s%N)-800
	$(PYTHON) dev/check_theme_customization.py --size 1280x720 --output private/screenshots/theme-customization-$$(date +%s%N)-1280
check-theme-appearance:
	$(PYTHON) dev/check_theme_appearance.py --size 800x600 --output private/screenshots/theme-appearance-$$(date +%s%N)-800
	$(PYTHON) dev/check_theme_appearance.py --size 1280x720 --output private/screenshots/theme-appearance-$$(date +%s%N)-1280
check-screen-saver:
	$(PYTHON) dev/check_screen_saver.py --size 800x600 --output private/screenshots/saver-ui-$$(date +%s%N)-800
	$(PYTHON) dev/check_screen_saver.py --size 1280x720 --output private/screenshots/saver-ui-$$(date +%s%N)-1280
check-theme-import:
	$(PYTHON) dev/run_theme_import_checks.py

.PHONY: prepare-assets check-asset-cache
prepare-assets:
	$(PYTHON) tools/prepare_assets.py --report private/asset-stage-cache/reports/build-$$(date +%s%N).json
check-asset-cache:
	$(PYTHON) -m unittest discover -s tests -p 'test_asset*.py' -q

PYTHON ?= python3
.PHONY: check test check-ui check-menu-seams check-sprint-controls check-computer-view stage reference-plan
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
check-ui: check-menu-seams check-sprint-controls check-computer-view
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

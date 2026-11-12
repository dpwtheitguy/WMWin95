PYTHON ?= python3
.PHONY: check test stage reference-plan
check:
	$(PYTHON) dev/check.py
test:
	$(PYTHON) -m unittest discover -s tests -v
	$(PYTHON) -m compileall -q tools dev src
stage:
	$(PYTHON) dev/stage_xfce.py
reference-plan:
	$(PYTHON) tools/reference_vm.py --iso "$(HOME)/Downloads/Windows 95C.iso"

.PHONY: test compile zip

test:
	pytest

compile:
	python -m compileall brain apps tests

zip:
	cd .. && zip -r brain-codebase.zip brain-codebase -x '*.pyc' -x '__pycache__/*'

.PHONY: test lint clean run

test:
	PYTHONPATH=. python3 -m unittest discover -s tests -v

lint:
	python3 -m py_compile parity_guard/*.py tests/*.py

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

run:
	python3 -m parity_guard --help

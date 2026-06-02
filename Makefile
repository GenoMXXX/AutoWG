.PHONY: build clean

build:
	python build_ipk.py

clean:
	python -c "from pathlib import Path; import shutil; [p.unlink() for p in Path('.').glob('wg-watchdog_*.ipk') if p.is_file()]; [shutil.rmtree(p, ignore_errors=True) for p in Path('.').rglob('__pycache__')]"

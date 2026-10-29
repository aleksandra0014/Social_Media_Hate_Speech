"""Execute notebooks in place (e.g. all hate analyses for the best model) – notebooks/5_analizy_herbert_hate/README.
    python scripts/run_notebooks.py notebooks/5_analizy_herbert_hate            # all, every platform
    python scripts/run_notebooks.py notebooks/5_analizy_herbert_hate/wykop      # one platform
Each notebook runs in its own folder (like opening it in Jupyter); errors are listed at the end, the rest keeps going.
Needs: pip install nbclient ipykernel
"""
import sys
import time
from pathlib import Path

import nbformat
from nbclient import NotebookClient
from nbclient.exceptions import CellExecutionError


def main():
    targets = [Path(a) for a in sys.argv[1:]] or [Path('notebooks/5_analizy_herbert_hate')]
    notebooks = sorted(p for t in targets for p in ([t] if t.suffix == '.ipynb' else t.rglob('*.ipynb'))
                       if '.ipynb_checkpoints' not in p.parts)
    # per-event notebooks first, platform summaries last
    notebooks.sort(key=lambda p: (p.name.startswith('all_events'), str(p)))
    failed = []
    for i, p in enumerate(notebooks, 1):
        t0 = time.time()
        nb = nbformat.read(p, as_version=4)
        client = NotebookClient(nb, timeout=3600, kernel_name='python3', resources={'metadata': {'path': str(p.parent)}})
        try:
            client.execute()
            status = 'ok'
        except CellExecutionError as e:
            failed.append((p, str(e).strip().splitlines()[-1][:200]))
            status = 'BŁĄD'
        nbformat.write(nb, p)
        print(f'[{i}/{len(notebooks)}] {status:4s} {time.time() - t0:6.0f}s  {p}', flush=True)
    if failed:
        print('\nNotebooki z błędem:')
        for p, msg in failed:
            print(f'  {p}: {msg}')
        sys.exit(1)


if __name__ == '__main__':
    main()

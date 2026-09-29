"""Atalho de compatibilidade: `streamlit run main.py` abre o front-end.

O aplicativo mora em `frontend/app.py` e consome a API REST de `backend/`.
"""

import runpy
from pathlib import Path

runpy.run_path(str(Path(__file__).parent / "frontend" / "app.py"), run_name="__main__")

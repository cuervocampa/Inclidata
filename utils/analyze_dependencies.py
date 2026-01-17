
import os
import ast
import sys
import pkgutil
from pathlib import Path
import json

# Directorio raíz del proyecto
ROOT_DIR = Path(os.getcwd())

# Lista de librerías estándar de Python (aproximada para filtrar)
STD_LIB = {
    'abc', 'argparse', 'ast', 'asyncio', 'base64', 'calendar', 'collections', 'concurrent',
    'contextlib', 'copy', 'csv', 'datetime', 'decimal', 'difflib', 'email', 'enum',
    'functools', 'glob', 'hashlib', 'html', 'http', 'importlib', 'inspect', 'io', 'itertools',
    'json', 'logging', 'math', 'multiprocessing', 'os', 'pathlib', 'pickle', 'platform',
    'pprint', 'random', 're', 'shutil', 'signal', 'socket', 'sqlite3', 'statistics',
    'string', 'subprocess', 'sys', 'tempfile', 'threading', 'time', 'timeit', 'traceback',
    'types', 'typing', 'unittest', 'urllib', 'uuid', 'warnings', 'weakref', 'xml', 'zipfile',
    'zoneinfo'
}

# Mapeo de nombres de importación a nombres de paquetes en PyPI (cuando difieren)
IMPORT_TO_PIP = {
    'sklearn': 'scikit-learn',
    'PIL': 'Pillow',
    'yaml': 'PyYAML',
    'cv2': 'opencv-python',
    'dash_mantine_components': 'dash-mantine-components',
    'dash_bootstrap_components': 'dash-bootstrap-components',
    'dash_ag_grid': 'dash-ag-grid',
    'dash_iconify': 'dash-iconify',
    'xlsxwriter': 'XlsxWriter',
    'dateutil': 'python-dateutil',
    'win32com': 'pywin32',
    'win32api': 'pywin32',
    'pythoncom': 'pywin32',
    'fitz': 'pymupdf',
}

def get_imports_from_file(file_path):
    """Extrae las librerías importadas de un archivo Python."""
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        try:
            tree = ast.parse(f.read())
        except SyntaxError:
            return set()

    imports = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.add(alias.name.split('.')[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.add(node.module.split('.')[0])
    return imports

def analyze_project():
    file_dependencies = {}
    all_third_party = set()
    
    # Identificar módulos locales (directorios con __init__.py o en la raíz)
    local_modules = {p.name for p in ROOT_DIR.iterdir() if p.is_dir()}
    local_modules.add('utils')
    local_modules.add('pages')
    local_modules.add('biblioteca_graficos')
    local_modules.add('data')
    local_modules.add('assets')
    
    print("Analizando archivos...")
    
    for py_file in ROOT_DIR.rglob('*.py'):
        if 'venv' in py_file.parts or 'site-packages' in py_file.parts or '__pycache__' in py_file.parts:
            continue
            
        rel_path = py_file.relative_to(ROOT_DIR)
        imports = get_imports_from_file(py_file)
        
        # Filtrar
        third_party = set()
        for imp in imports:
            if imp in STD_LIB:
                continue
            if imp in local_modules:
                continue
            if imp.startswith('.'):
                continue
            
            # Normalizar nombre PIP
            pip_name = IMPORT_TO_PIP.get(imp, imp)
            third_party.add(pip_name)
            all_third_party.add(pip_name)
            
        file_dependencies[str(rel_path)] = sorted(list(third_party))

    # Generar MD
    md_content = "# Documentación de Librerías por Archivo\n\n"
    md_content += "Este documento detalla las librerías de terceros utilizadas en cada archivo del proyecto.\n\n"
    
    for file, deps in sorted(file_dependencies.items()):
        if deps:
            md_content += f"## `{file}`\n"
            for dep in deps:
                md_content += f"- {dep}\n"
            md_content += "\n"
            
    with open('LIBRERIAS_POR_ARCHIVO.md', 'w', encoding='utf-8') as f:
        f.write(md_content)
        
    print(f"Archivo LIBRERIAS_POR_ARCHIVO.md generado.")
    print(f"Librerías externas detectadas: {sorted(list(all_third_party))}")
    
    # Leer requirements actual
    try:
        with open('requirements.txt', 'r') as f:
            current_reqs = f.read().splitlines()
    except FileNotFoundError:
        current_reqs = []
        
    return sorted(list(all_third_party))

if __name__ == "__main__":
    analyze_project()

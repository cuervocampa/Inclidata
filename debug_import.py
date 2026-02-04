import sys
import os

# Add local path to ensure we find it if pip failed
sys.path.append(os.getcwd())

try:
    import dash_component_editor as dce
    print("Imported successfully:", dce)
    print("File:", dce.__file__)
    print("Dir:", dir(dce))
    if hasattr(dce, 'Editor'):
        print("Editor found")
    else:
        print("Editor NOT found")
except ImportError as e:
    print("Import failed:", e)
except Exception as e:
    print("Error:", e)

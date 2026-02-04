
import os
import sys
# Make sure we can find the modules
sys.path.append(os.getcwd())

from utils.funciones_importar import import_RST

# Mock file reading as done in the app (reading lines)
def read_file_lines(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        # Simulate base64 decode by just reading and splitting lines
        # In the app: content_string -> base64 decode -> decode utf-8 -> splitlines
        # Here: just reading the file replicates the textual content
        return f.read().splitlines()

def test_import():
    file_path = r"c:\_\03_PYTHON\GitHub\IncliData\data\RST\Rozmarin_IN_01\rozmarinJerusalem-11-20240718_131703.csv"
    
    if not os.path.exists(file_path):
        print(f"File not found: {file_path}")
        return

    print(f"Testing import for: {file_path}")
    
    try:
        lines = read_file_lines(file_path)
        # The structure expected by import_RST is a list of dictionaries
        input_files = [{'filename': os.path.basename(file_path), 'lines': lines}]
        
        # Mock index_0 and cota
        index_0 = 1000 
        cota = 0 
        
        data = import_RST(input_files, index_0, cota)
        
        if not data:
             print("Result is empty!")
             return

        print("Import Result Keys:", list(data.keys()))
        
        for key, value in data.items():
             if key != 'info':
                 print(f"Campaign: {key}")
                 # Print a sample of data to verify
                 if 'calc' in value:
                     print(f"  First data point: {value['calc'][0]}")
                 else:
                     print(f"  structure: {value.keys()}")

    except Exception as e:
        print(f"Error during import: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_import()

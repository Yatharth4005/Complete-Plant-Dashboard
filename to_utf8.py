import os

input_file = "excel_structure.txt"
output_file = "excel_structure_utf8.txt"

if os.path.exists(input_file):
    try:
        # Read as UTF-16 LE (default for PowerShell redirection >)
        with open(input_file, "r", encoding="utf-16") as f:
            content = f.read()
        
        # Write as UTF-8
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"Successfully converted '{input_file}' to UTF-8 as '{output_file}'!")
    except Exception as e:
        print(f"Error during conversion: {e}")
else:
    print(f"Error: '{input_file}' not found.")

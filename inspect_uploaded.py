import openpyxl

path = r"e:\Jindal Steel Projects\DEPARTMENTS DASHBOARD\EFMEA\fmea\Rail Mill Raigarh - EFMEA and Action Plan.xlsx"
wb = openpyxl.load_workbook(path, data_only=True)
sheet = wb['Vertical Roll Balancing Cylinde']

print("Vertical Roll Balancing Cylinde Row Details:")
for r in range(10, sheet.max_row + 1):
    row_vals = [cell.value for cell in sheet[r]]
    if any(cell is not None for cell in row_vals):
        print(f"Row {r:2d}: {row_vals}")

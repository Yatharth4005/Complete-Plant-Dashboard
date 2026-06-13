import openpyxl

path = r"e:\Jindal Steel Projects\DEPARTMENTS DASHBOARD\EFMEA\fmea\FMEA Format.xlsx"
wb = openpyxl.load_workbook(path, data_only=False)
sheet = wb['FMEA']

print("Merged cells in sheet:")
for range_ in sheet.merged_cells.ranges:
    print(f" - {range_}")

print("\nDetail of top rows:")
for r in range(1, 5):
    for c in range(1, 24):
        cell = sheet.cell(row=r, column=c)
        if cell.value is not None:
            print(f"Cell {cell.coordinate} (value): {repr(cell.value)}")

import openpyxl
import os

path = r"e:\Jindal Steel Projects\DEPARTMENTS DASHBOARD\EFMEA\fmea\FMEA Format.xlsx"
wb = openpyxl.load_workbook(path, data_only=False)
sheet = wb['FMEA']

print("================ FMEA Format.xlsx Top 5 Rows ================")
for r in range(1, 6):
    row_data = []
    for c in range(1, 24): # columns A to W
        cell = sheet.cell(row=r, column=c)
        val = cell.value
        coord = cell.coordinate
        if val is not None:
            row_data.append(f"{coord}: {repr(val)}")
    if row_data:
        print(f"Row {r}: {', '.join(row_data)}")

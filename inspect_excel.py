import openpyxl

wb = openpyxl.load_workbook(r"e:\Jindal Steel Projects\DEPARTMENTS DASHBOARD\media\uploads\delays\SPM_Delay_08-06-2026_kBwdxhk.xlsx", data_only=True)
for name in wb.sheetnames:
    print(f"--- Sheet: {name} ---")
    sheet = wb[name]
    for r in range(1, 35):
        row_vals = [cell.value for cell in sheet[r]]
        if any(row_vals):
            print(f"Row {r}: {row_vals[:15]}")

import xlrd
import os

def main():
    xls_path = "KAIZEN - Blank Format.xls"
    if not os.path.exists(xls_path):
        print(f"File not found: {xls_path}")
        return
        
    try:
        book = xlrd.open_workbook(xls_path, formatting_info=True)
        print(f"Workbook opened successfully. Sheets: {book.nsheets}")
        sheet = book.sheet_by_index(0)
        print(f"Sheet name: {sheet.name}, Rows: {sheet.nrows}, Cols: {sheet.ncols}")
        
        print("\n--- Detailed Cell Grid ---")
        for r in range(sheet.nrows):
            row_cells = []
            for c in range(sheet.ncols):
                cell = sheet.cell(r, c)
                val = cell.value
                # If cell is merged or has a value, show it
                if val != "":
                    row_cells.append(f"C{c}({cell.ctype}): {repr(val)}")
            if row_cells:
                print(f"Row {r:02d}: " + " | ".join(row_cells))
                
        # Also print merged cells to understand spans
        print("\n--- Merged Cells ---")
        for crange in sheet.merged_cells:
            rlo, rhi, clo, chi = crange
            print(f"Merged region: Rows {rlo} to {rhi-1}, Cols {clo} to {chi-1} (Top-Left cell: Row {rlo}, Col {clo}, value: {repr(sheet.cell(rlo, clo).value)})")

    except Exception as e:
        print(f"Error reading XLS: {e}")

if __name__ == '__main__':
    main()

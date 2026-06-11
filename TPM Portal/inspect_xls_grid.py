import xlrd
import os

def main():
    xls_path = "KAIZEN - Blank Format.xls"
    if not os.path.exists(xls_path):
        print(f"File not found: {xls_path}")
        return
        
    try:
        book = xlrd.open_workbook(xls_path, formatting_info=True)
        sheet = book.sheet_by_index(0)
        
        print(f"Sheet: {sheet.name}, Rows: {sheet.nrows}, Cols: {sheet.ncols}")
        
        # We will print the grid with cell values or None
        for r in range(sheet.nrows):
            row_str = []
            for c in range(sheet.ncols):
                val = sheet.cell_value(r, c)
                if val == "":
                    # Check if it is a merged cell
                    is_merged_non_top_left = False
                    for crange in sheet.merged_cells:
                        rlo, rhi, clo, chi = crange
                        if rlo <= r < rhi and clo <= c < chi:
                            if not (r == rlo and c == clo):
                                is_merged_non_top_left = True
                                break
                    if is_merged_non_top_left:
                        row_str.append("[Merged]")
                    else:
                        row_str.append("")
                else:
                    row_str.append(str(val))
            print(f"Row {r:02d}: " + " | ".join(f"C{c}:{v}" for c, v in enumerate(row_str) if v != ""))
    except Exception as e:
        print(f"Error: {e}")

if __name__ == '__main__':
    main()

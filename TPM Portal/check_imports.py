try:
    import xlrd
    import xlwt
    import xlutils
    from xlutils.copy import copy
    print("ALL_IMPORTS_SUCCESSFUL")
except ImportError as e:
    print(f"IMPORT_ERROR: {e}")

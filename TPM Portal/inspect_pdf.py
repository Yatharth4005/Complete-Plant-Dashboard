import os

def check_pdf():
    pdf_path = "CAPA Formate.pdf"
    if not os.path.exists(pdf_path):
        print(f"File not found: {pdf_path}")
        return
        
    print(f"File size: {os.path.getsize(pdf_path)} bytes")
    
    # Try importing common PDF libraries
    libs = ['pypdf', 'PyPDF2', 'pdfplumber', 'fitz', 'pdfminer']
    for lib in libs:
        try:
            __import__(lib)
            print(f"Library '{lib}' is AVAILABLE")
        except ImportError:
            print(f"Library '{lib}' is NOT available")

if __name__ == '__main__':
    check_pdf()

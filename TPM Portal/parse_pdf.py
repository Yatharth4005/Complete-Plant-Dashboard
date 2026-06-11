import pypdf
import os

def main():
    pdf_path = "CAPA Formate.pdf"
    if not os.path.exists(pdf_path):
        pdf_path = r"e:\Jindal Steel Projects\DEPARTMENTS DASHBOARD\TPM Portal\CAPA Formate.pdf"
        
    if not os.path.exists(pdf_path):
        print(f"File not found: {pdf_path}")
        return
        
    try:
        reader = pypdf.PdfReader(pdf_path)
        print(f"Successfully opened PDF. Pages: {len(reader.pages)}")
        for i, page in enumerate(reader.pages):
            print(f"\n=================== Page {i+1} ===================")
            text = page.extract_text()
            print(text)
    except Exception as e:
        print(f"Error parsing PDF: {e}")

if __name__ == '__main__':
    main()

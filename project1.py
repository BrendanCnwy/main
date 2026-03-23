# Read: Read the output file name from the command line. I.e. if the invocation is “python pdfmerger.py my_files”
# then the merged file will be my_files.pdf.
# If a name is not specified, terminate the script with a message: Error: Merge file name not specified. Usage:
# python pdfmerger.py filename
# Initialize: Create a “merger” object that will hold all of our pages.
# Retrieve: Collect the names of files in the current directory.
# Filter: Pick only the files with a .pdf extension.
# Sort: Put the files in alphabetical order.
# Report: List files found and count to the user.
# PDF files found: 2
# List:
# File1.pdf
# File2.pdf
# Prompt: Ask the user whether to continue operation: Continue (y/n):
# Append: Add each PDF into the “merger” object. Be sure not to merge any file with the same name as the
# output file name.
# Export: Save the final combined pdf file to your hard drive.1``

import sys
import os
from PyPDF2 import PdfMerger

def merge_pdfs(output_path):
    merger = PdfMerger()
    for fname in sorted(os.listdir(os.getcwd())): # iterate through sorted list pdf's in current directory
        if fname.lower().endswith(".pdf"):   #check if file is a pdf
            merger.append(os.path.join(os.getcwd(), fname)) #if the chosen files are pdf's then append them into the merger file
    with open(output_path, "wb") as f:
        merger.write(f)
    merger.close()

def main():
    if len(sys.argv) < 2:
        print("Error: Merge\nfile name not specified. Usage: python pdfmerger.py\nfilename") #terminates the script if name is not specified or if there is less than 2 files
        sys.exit(1)

    base = sys.argv[1]
    output = base if base.lower().endswith(".pdf") else base + ".pdf" #identify the files for merging

    # list available PDF files
    pdfs = sorted(f for f in os.listdir(os.getcwd()) if f.lower().endswith(".pdf")) #this searches for files with .pdf and lists them to the user
    print(f"PDF files found: {len(pdfs)}")
    for p in pdfs:
        print(p)

    # prompt user to continue
    choice = input("Continue (y/n): ").strip().lower()
    if choice not in ("y", "yes"):
        print("Operation cancelled by user.")
        sys.exit(0)

    merge_pdfs(output)
    print(f"Merged PDFs into {output}") #makes the output file by merging the pdf's into one file

if __name__ == "__main__":
    main()

choice = input("Continue (y/n): ").strip().lower()
if choice not in ("y", "yes"):
    print("Operation cancelled by user.") #this will ask if the user wants to continue and if the choice is not yes it prints the termination message
    sys.exit(0)

    
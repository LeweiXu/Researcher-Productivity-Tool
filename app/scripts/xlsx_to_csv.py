import pandas as pd
import csv

def convert_xlsx_to_multiple_csv(xlsx_file_path):
    """
    Converts each sheet in an XLSX file to a separate CSV file.

    Args:
        xlsx_file_path (str): The path to the input XLSX file.
    """
    xls = pd.ExcelFile(xlsx_file_path)
    for sheet_name in xls.sheet_names:
        df = pd.read_excel(xlsx_file_path, sheet_name=sheet_name)
        csv_file_name = f"{sheet_name}.csv"
        df.to_csv(csv_file_name, index=False)
        print(f"Sheet '{sheet_name}' saved as '{csv_file_name}'")

def clean_csv_whitespace(input_csv, output_csv):
    with open(input_csv, mode='r', encoding='utf-8', newline='') as infile, \
         open(output_csv, mode='w', encoding='utf-8', newline='') as outfile:
        reader = csv.reader(infile)
        writer = csv.writer(outfile)
        for row in reader:
            cleaned_row = [cell.strip() for cell in row]
            writer.writerow(cleaned_row)

def main():
    # convert_xlsx_to_multiple_csv("./app/files/ABDC_All_Rankings.xlsx")
    clean_csv_whitespace("./app/files/2016 JQL.csv", "./app/files/2016 JQL_c.csv")

if __name__ == "__main__":
    main()
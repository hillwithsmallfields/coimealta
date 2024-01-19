#!/usr/bin/python3

# import argparse
import csv
import os
import datetime

PERISHABLES_FILE = os.path.expandvars("$SYNCED/org/perishables.csv")

def convert_row(row):
    row['Best before'] = datetime.date.fromisoformat(row['Best before'])
    quantity_cell = row.get'Quantity', "")
    row['Quantity'] = 1 if quantity_cell in (None, "") else float(quantity_cell)
    return row

def get_perishables():
    with open(PERISHABLES_FILE) as instream:
        return sorted([convert_row(raw) for raw in csv.DictReader(instream)],
                      key=lambda row: row['Best before'])

def perishables_main():
    for row in get_perishables():
        print(row['Best before'], row['Product'], "x", row['Quantity'])

def main():
    # parser = argparse.ArgumentParser()
    # args = parser.parse_args()
    perishables_main()

if __name__ == '__main__':
    main()

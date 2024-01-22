#!/usr/bin/env python3

import csv
import os

def get_storage_types(filename):
    with open(filename) as instream:
        return sorted(set(row.get('Type')
                          for row in csv.DictReader(instream)))

print(get_storage_types(os.path.expandvars("$ORG/storage.csv")))

#!/usr/bin/env python
import argparse
from backports import csv
import io
import re

def read_locations(locations_file):
    locations = {}
    with io.open(locations_file, 'r', encoding='utf-8') as input:
        storage_reader = csv.DictReader(input)
        for row in storage_reader:
            contained_within = row['ContainedWithin']
            row['ContainedWithin'] = int(contained_within) if contained_within != "" else None
            number = row['Number']
            if number != "":
                locations[int(number)] = row
    return locations

def nested_location(locations, location):
    result = []
    while location:
        where = locations[int(location)]
        result.append(where['Description'])
        location = where['ContainedWithin']
    return result

def describe_location(locations, location):
    return " which is in ".join(nested_location(locations, location))
    
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", "-f", default="/home/jcgs/common/org/storage.csv")
    parser.add_argument("location", nargs='+')
    args = parser.parse_args()
    locations = read_locations(args.file)
    for location in args.location:
        print describe_location(locations, location)

if __name__ == "__main__":
    main()

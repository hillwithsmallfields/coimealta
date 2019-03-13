#!/usr/bin/env python
import argparse
from backports import csv
import io
import os
import re

# todo: make searches case-insensitive
# todo: try each name as a storage location name, and if found, list everything in that location
# todo: option to print table of where all books are
# todo: option to print table of where all inventory items are
# todo: option to print table of all storage locations, with everything that is in them

def read_books(books_file):
    books = {}
    with io.open(books_file, 'r', encoding='utf-8') as input:
        books_reader = csv.DictReader(input)
        for row in books_reader:
            ex_libris = row['Number']
            if ex_libris != "":
                books[int(ex_libris)] = row
    return books

def book_matches(book, pattern):
    return (re.search(pattern, book['Title'])
            or re.search(pattern, book['Authors'])
            or re.search(pattern, book['Publisher'])
            or re.search(pattern, book['ISBN'])
            or re.search(pattern, book['Area']))

def books_matching(book_index, pattern):
    return [ book
             for book in book_index.values()
             if book_matches(book, pattern) ]

def read_inventory(inventory_file):
    inventory = {}
    unlabelled = -1
    with io.open(inventory_file, 'r', encoding='utf-8') as input:
        inventory_reader = csv.DictReader(input)
        for row in inventory_reader:
            label_number = row['Label number']
            if label_number != "":
                inventory[int(label_number)] = row
            else:
                inventory[unlabelled] = row
                unlabelled -= 1
    return inventory

def item_matches(item, pattern):
    return (re.search(pattern, item['Item'])
            or re.search(pattern, item['Type'])
            or re.search(pattern, item['Subtype']))

def items_matching(inventory_index, pattern):
    return [ item
             for item in inventory_index.values()
             if item_matches(item, pattern) ]

def read_locations(locations_file):
    locations = {}
    with io.open(locations_file, 'r', encoding='utf-8') as input:
        storage_reader = csv.DictReader(input)
        for row in storage_reader:
            contained_within = row['ContainedWithin']
            row['ContainedWithin'] = (int(contained_within)
                                      if contained_within != ""
                                      else None)
            number = row['Number']
            if number != "":
                locations[int(number)] = row
    return locations

def nested_location(locations, location):
    result = []
    location = int(location)
    while location:
        if location not in locations:
            break
        where = locations[location]
        description = where['Description']
        level = where['Level']
        if level != "":
            description += " "
            if re.match("[0-9]+", level):
                description += "level " + level
            else:
                description += level
            result.append(description)
        location = where['ContainedWithin']
    return result

def describe_location(locations, location):
    return " which is in ".join(nested_location(locations, location))

def main():
    parser = argparse.ArgumentParser()
    org_files = os.environ.get("ORG", "~/org")
    parser.add_argument("--locations", "-f",
                        default=os.path.join(org_files, "storage.csv"),
                        help="""The CSV file containing the storage locations.""")
    parser.add_argument("--books", "-b",
                        default=os.path.join(org_files, "books.csv"),
                        help="""The CSV file containing the book catalogue.""")
    parser.add_argument("--inventory", "-i",
                        default=os.path.join(org_files, "inventory.csv"),
                        help="""The CSV file containing the inventory.""")
    parser.add_argument("things",
                        nargs='+',
                        help="""The things to look for.""")
    args = parser.parse_args()
    locations = read_locations(args.locations)
    inventory = read_inventory(args.inventory)
    books = read_books(args.books)
    for thing in args.things:
        if re.match("[0-9]+", thing):
            as_location = describe_location(locations, thing)
            if as_location != []:
                print "as location:", as_location
            # todo: also look up books and items by number
        for book in books_matching(books, thing):
            shelf = book['Location']
            where = describe_location(locations, shelf) if shelf != "" else "unknown"
            print "book:", book['Title'], "is on", where
        for item in items_matching(inventory, thing):
            shelf = item['Normal_location']
            where = describe_location(locations, shelf) if shelf != "" else "unknown"
            print "item:", item['Item'], "is in", where

if __name__ == "__main__":
    main()

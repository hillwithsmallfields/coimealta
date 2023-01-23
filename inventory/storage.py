#!/usr/bin/env python3
import argparse
import cmd
import csv
import decouple
import functools
import io
import json
import math
import operator
import os
import re
import shlex
import sys
# import yaml

source_dir = os.path.dirname(os.path.realpath(__file__))
# This corresponds to https://github.com/hillwithsmallfields
my_projects = os.path.dirname(os.path.dirname(source_dir))
sys.path.append(os.path.join(my_projects, "Simple_client_server"))

import client_server # the shell script ../storage makes this available

class StorageShell(cmd.Cmd):

    prompt = "Storage> "

    def __init__(self, outstream, locations, items, books):
        super().__init__()
        self.outstream = outstream
        self.locations = locations
        self.items = items
        self.books = books

    def postcmd(self, stop, _line):
        return stop

    def do_list_books(self, *_args):
        """Show a table of where all the books are."""
        by_location = {}
        for idx, book in self.books.items():
            if 'Location' in book:
                loc = book['Location']
                if loc in by_location:
                    by_location[loc].append(idx)
                else:
                    by_location[loc] = [idx]
        for loc, contents in by_location.items():
            self.outstream.write(describe_nested_location(self.locations, loc) + ":\n")
            for title in sorted([self.books[idx]['Title'] for idx in contents ]):
                self.outstream.write("    " + title + "\n")
        return False

    def do_capacities(self, *_args):
        """Analyze the storage capacities.
    Shows how much of each type of storage there is, and also a summary
    combining the types."""
        capacity_by_type, volume, bookshelf_length, other_length, area = calculate_capacities(self.locations)
        for loctype in sorted(capacity_by_type.keys()):
            label_width = max(*map(len, capacity_by_type.keys()))
        self.outstream.write(loctype.rjust(label_width) + " " + str(math.ceil(capacity_by_type[loctype])) + "\n")
        self.outstream.write("Total container volume: " + str(volume) + " litres\n")
        self.outstream.write("Total container and book (estimate) volume: "
                             + str(volume + bookshelf_length * bookshelf_area)
                             + " litres\n")
        self.outstream.write("Total shelving length: "
                             + str(bookshelf_length + other_length)
                             + " metres\n")
        self.outstream.write("Total panel area: "
                             + str(area)
                             + " square metres\n")
        return False

    def do_counts(self, *_args):
        """Count how many of each type of thing I have."""
        # todo: maybe do the books here as well?
        types = {}
        for item in self.items.values():
            item_type = item['Type']
            if item_type not in types:
                types[item_type] = {}
            subtypes = types[item_type]
            item_subtype = item['Subtype']
            if item_subtype in subtypes:
                subtypes[item_subtype] += 1
            else:
                subtypes[item_subtype] = 1
        for item_type in sorted(types.keys()):
            subtypes = types[item_type]
            self.outstream.write((item_type if item_type != "" else "unspecified")
                            + ": "
                            + str(functools.reduce(operator.add, subtypes.values()))
                            + "\n")
            for subtype in sorted([k for k in subtypes.keys() if k is not None ]):
                self.outstream.write("    "
                                     + (subtype
                                        if subtype != "" and subtype is not None
                                        else "unspecified")
                                     + ": "
                                     + str(subtypes[subtype])
                                     + "\n")
        return False

    def do_list_items(self, *args):
        """Show a table of where all the items are."""
        # todo: option to print table of where all inventory items are
        by_location = {}
        for idx, item in self.items.items():
            if 'Normal location' in item:
                loc = item['Normal location']
                if loc in by_location:
                    by_location[loc].append(idx)
                else:
                    by_location[loc] = [idx]
        for loc, contents in by_location.items():
            self.outstream.write(describe_nested_location(self.locations, loc) + ":\n")
            for title in sorted([self.items[idx]['Item'] for idx in contents ]):
                self.outstream.write("    " + title + "\n")
        return False

    def do_name_completions(self, *things):
        """Return the names matching a fragment."""
        if len(things) == 0:
            return ""
        fragment = things[0]
        self.outstream.write(json.dumps(sorted(
            [book['Title']
              for book in self.books.values()
              if fragment in book['Title']]
            + [item['Item']
               for item in self.items.values()
               if fragment in item['Item']]))
                             + "\n")

    def do_location_completions(self, *things):
        """Return the location names matching a fragment."""
        if len(things) == 0:
            return ""
        fragment = things[0]
        self.outstream.write(json.dumps(sorted(
            [location['Description']
             for location in self.locations.values()
             if fragment in location['Description']]))
            + "\n")
        return False

    def do_quit(self, _args):
        """Stop the CLI."""
        return True

    def do_list_locations(self, *things):
        """List everything that is in the matching locations."""
        for where in locations_matching_patterns(self.locations, things):
            list_location(self.outstream, where, "", self.locations, self.items, self.books)
        return False

    def do_find_things(self, *args):
        """Show the locations of things.
        This finds books, other items, and locations."""
        print("Looking for", *args)
        findings = {}
        for thing in args:
            if re.match("[0-9]+", thing):
                as_location = describe_nested_location(self.locations, thing)
                if as_location != []:
                    findings[thing] = as_location
            for book in books_matching(self.books, thing):
                findings[book['Title']] = describe_nested_location(self.locations, book['Location'])
            for item in items_matching(self.items, thing):
                findings[item['Item']] = describe_nested_location(self.locations, item['Normal location'])
        for finding in sorted(findings.keys()):
            self.outstream.write(finding + " is " + findings[finding] + "\n")
        return False

def normalize_book_entry(row):
    ex_libris = row['Number']
    if isinstance(ex_libris, str) and ex_libris != "":
        ex_libris = int(ex_libris)
        row['Number'] = ex_libris
    location = row['Location']
    if isinstance(location, str) and location != "":
        location = int(location)
        row['Location'] = location
    return row

def read_books(books_file, _key=None):
    with io.open(books_file, 'r', encoding='utf-8') as instream:
        return { book['Number']: book
                 for book in [normalize_book_entry(row)
                              for row in csv.DictReader(instream)]
                 if book['Number'] != "" }

# Description for reading these files using client_server.py:
# ('Number', normalize_book_entry)

def book_matches(book, pattern):
    pattern = re.compile(pattern , re.IGNORECASE)
    return (book['Title'] and pattern.search(book['Title'])
            or book['Authors'] and pattern.search(book['Authors'])
            or book['Publisher'] and pattern.search(book['Publisher'])
            or book['ISBN'] and pattern.search(book['ISBN'])
            or book['Area'] and pattern.search(book['Area']))

def books_matching(book_index, pattern):
    return [book
            for book in book_index.values()
            if book_matches(book, pattern) ]

unlabelled = -1

def normalize_item_entry(row):
    global unlabelled
    label_number = row.get('Label number', "")
    if isinstance(label_number, str) and label_number != "":
        label_number = int(label_number)
        row['Label number'] = label_number
    else:
        row['Label number'] = unlabelled
        unlabelled -= 1
    normal_location = row['Normal location']
    if isinstance(normal_location, str) and re.match("[0-9]+", normal_location):
        normal_location = int(normal_location)
        row['Normal location'] = normal_location
    return row

def read_inventory(inventory_file, _key=None):
    if os.path.exists(inventory_file):
        with io.open(inventory_file, 'r', encoding='utf-8') as instream:
            return { item['Label number']: item
                     for item in map(normalize_item_entry,
                                     [row
                                       for row in csv.DictReader(instream) ])}
    else:
        return {}

# Description for reading these files using client_server.py:
# ('Label number', normalize_item_entry)

def item_matches(item, pattern):
    pattern = re.compile(pattern , re.IGNORECASE)
    return (pattern.search(item['Item'])
            or (item['Type'] and pattern.search(item['Type']))
            or (item['Subtype'] and pattern.search(item['Subtype'])))

def items_matching(inventory_index, pattern):
    return [item
             for item in inventory_index.values()
             if item_matches(item, pattern) ]

def normalize_location(row):
    contained_within = row['ContainedWithin']
    try:
        row['ContainedWithin'] = (int(contained_within)
                                  if (isinstance(contained_within, str)
                                      and contained_within != "")
                                  else None)
    except ValueError:
        row['ContainedWithin'] = None
    number = row['Number']
    row['Number'] = int(number) if (isinstance(number, str)
                                    and number != "") else None
    return row

def read_locations(locations_file, _key=None):
    with io.open(locations_file, 'r', encoding='utf-8') as instream:
        return { location['Number']: location
                 for location in [normalize_location(row)
                                   for row in csv.DictReader(instream)
                                   if row['Number'] is not None ] }

# Description for reading these files using client_server.py:
# ('Number', normalize_location)

def locations_matching(locations_index, pattern):
    """Return a list of location numbers for locations that match a regexp."""
    if pattern == "all":
        return [loc['Number']
                 for loc in locations_index.values() ]
    else:
        pattern = re.compile(pattern, re.IGNORECASE)
        return [loc['Number']
                 for loc in locations_index.values()
                 if pattern.search(loc['Description']) ]

def locations_matching_patterns(locations_index, patterns):
    """Return a set of location numbers for locations that match any of a list of regexps."""
    result = set()
    for pattern in patterns:
        for loc in locations_matching(locations_index, pattern):
            result.add(loc)
    return result

def describe_location(where):
    """Return a description of a location."""
    description = where['Description'].lower()
    level = where['Level']
    if level != "":
        description += " "
        if re.match("[0-9]+", level):
            description += "level " + level
        else:
            description += level
    storage_type = where['Type']
    if storage_type != "":
        if storage_type in ("room", "building"):
            description = "the " + description
        else:
            if (storage_type == "shelf"
                and not re.search("shelves", description)):
                description += " " + storage_type
    description = ("on " if storage_type == "shelf" else "in ") + description
    return description

def nested_location(locations, location):
    result = []
    try:
        location = int(location)
        while location:
            if location not in locations:
                break
            where = locations[location]
            description = describe_location(where)
            result.append(description)
            location = where['ContainedWithin']
        return result
    except:
        return ["Could not follow location %s" % location]

def describe_nested_location(locations, location):
    """Return a description of a location, along with any surrounding locations."""
    return (" which is ".join(nested_location(locations, location))
            if location != ""
            else "unknown")

def sum_capacities(all_data, types):
    return math.ceil(functools.reduce(operator.add,
                                      [all_data.get(loctype, 0)
                                       for loctype in types ]))

# factor to convert meter of bookshelf to litre of books
# the 10 is because a liter is a decimeter along each side
bookshelf_area = 10 * 2 * 1.5

def calculate_capacities(locations):
    capacity_by_type = {}
    for location in locations.values():
        loctype = (location['Type'] or "").lower() if 'Type' in location else ""
        locsize = (location['Size'] or "").lower() if 'Size' in location else ""
        if loctype != "" and locsize != "":
            capacity_by_type[loctype] = float(capacity_by_type.get(loctype, 0)) + float(locsize)
    volume = sum_capacities(capacity_by_type, ('box', 'crate',
                                               'drawer', 'cupboard'))
    bookshelf_length = sum_capacities(capacity_by_type, ('bookshelf', 'bookshelves'))
    other_length = sum_capacities(capacity_by_type, ('shelf', 'shelves',
                                                     'cupboard shelf', 'racklevel'))
    area = sum_capacities(capacity_by_type, ('louvre panel', 'pegboard'))
    return capacity_by_type, volume, bookshelf_length, other_length, area

def list_location(outstream, location, prefix, locations, items, books):
    """List everything that is in the given location."""
    if type(location) == dict:
        location = location['Number']
    directly_contained_items = [
        item for item in items.values()
        if item['Normal location'] == location ]
    directly_contained_books = [
        book for book in books.values()
        if book['Location'] == location ]
    sub_locations = [
        subloc for subloc in locations.values()
        if subloc['ContainedWithin'] == location ]
    description = describe_location(locations[location])
    next_prefix = prefix + "    "
    if len(directly_contained_items) > 0:
        outstream.write(prefix + "Items directly " + description + ":\n")
        for item in directly_contained_items:
            outstream.write(next_prefix + item['Item'] + "\n")
    if len(directly_contained_books) > 0:
        outstream.write(prefix + "Books directly " + description + ":\n")
        for book in directly_contained_books:
            outstream.write(next_prefix + book['Title'] + "\n")
    if len(sub_locations) > 0:
        outstream.write(prefix + "Locations " + description + ":\n")
        for subloc in sub_locations:
            outstream.write(next_prefix + subloc['Description'] + "\n")
            list_location(outstream, subloc, next_prefix, locations, items, books)

def cmd_bad(outstream, _args, _locations, _items, _books):
    """Report an invalid command."""
    outstream.write("""Bad command; enter "help" to get a list of commands\n""")
    return True

def run_command(outstream,
                command,
                things,
                locations,
                items, books):
    # todo: change the arguments to these functions, to take a dictionary mapping standard names to the used names, and one mapping the used names to the data
    return commands.get(command, cmd_bad)(outstream,
                                          things,
                                          locations,
                                          items,
                                          books)

filenames = {}

remembered_items_data = {'combined': None,
                         'inventory': None,
                         'stock': None,
                         'project_parts': None,
                         'books': None,
                         'locations': None}

def storage_server_function(in_string, files_data):
    command_parts = shlex.split(in_string)
    if len(command_parts) > 0:
        inventory = files_data[filenames['inventory']]
        stock = files_data[filenames['stock']]
        project_parts = files_data[filenames['project_parts']]
        if (inventory is not remembered_items_data['inventory']
            or stock is not remembered_items_data['stock']
            or project_parts is not remembered_items_data['project_parts']):
            items_data = inventory
            items_data.update(stock)
            items_data.update(project_parts)
            remembered_items_data['combined'] = items_data
            remembered_items_data['inventory'] = inventory
            remembered_items_data['stock'] = stock
            remembered_items_data['project_parts'] = project_parts
        else:
            items_data = remembered_items_data['combined']
        output_catcher = io.StringIO()
        StorageShell(output_catcher,
                     files_data[filenames['locations']],
                     items_data,
                     files_data[filenames['books']]).onecmd(in_string)
        run_command(output_catcher,
                    command_parts[0],
                    command_parts[1:],
                    files_data[filenames['locations']],
                    items_data,
                    files_data[filenames['books']])
        return output_catcher.getvalue()
    else:
        return "Command was empty"

def get_args():
    parser = argparse.ArgumentParser()
    # parser.add_argument("--config", "-c",
    #                     default="/usr/local/share/storage.yaml",
    #                     help="""The config file for the storage system.""")
    parser.add_argument("--locations", "-f",
                        default="$ORG/storage.csv",
                        help="""The CSV file containing the storage locations.""")
    parser.add_argument("--books", "-b",
                        default="$ORG/books.csv",
                        help="""The CSV file containing the book catalogue.""")
    parser.add_argument("--inventory", "-i",
                        default="$ORG/inventory.csv",
                        help="""The CSV file containing the general inventory.""")
    parser.add_argument("--stock", "-s",
                        default="$ORG/stock.csv",
                        help="""The CSV file containing the stock material inventory.""")
    parser.add_argument("--project-parts", "-p",
                        default="$ORG/project-parts.csv",
                        help="""The CSV file containing the project parts inventory.""")
    actions = parser.add_mutually_exclusive_group()
    actions.add_argument("--server", action='store_true',
                        help="""Run a little CLI on a network socket.""")
    actions.add_argument("--cli", action='store_true',
                         help="""Run a little CLI on stdin and stdout.""")
    client_server.client_server_add_arguments(parser, 9797)
    parser.add_argument("things",
                        nargs='*',
                        help="""The things to look for.""")
    return vars(parser.parse_args())

def storage(locations,
            books,
            inventory,
            stock,
            project_parts,
            server: bool,
            cli: bool,
            things):
    # with open(os.path.expanduser(os.path.expandvars(config))) as config_file:
    #     config = yaml.load(config_file)
    #     print("config is", config)
    for defkey, defval in __dict__.items():
        if isinstance(defval, str):
            __dict__[defkey] = os.path.expandvars(defval)
    if server:
        query_passphrase = decouple.config('query_passphrase')
        reply_passphrase = decouple.config('reply_passphrase')
        client_server.check_private_key_privacy(args)
        query_key, reply_key = client_server.read_keys_from_files(args,
                                                                  query_passphrase,
                                                                  reply_passphrase)
        global filenames
        filenames = {'inventory': os.path.basename(inventory),
                     'books': os.path.basename(books),
                     'stock': os.path.basename(stock),
                     'project_parts': os.path.basename(project_parts),
                     'locations': os.path.basename(locations)}
        client_server.run_servers(host, int(port),
                                  getter=storage_server_function,
                                  files={inventory: ('Label number',
                                                          normalize_item_entry),
                                         books: ('Number',
                                                      normalize_book_entry),
                                         stock: ('Label number',
                                                      normalize_item_entry),
                                         project_parts: ('Label number',
                                                              normalize_item_entry),
                                         locations: ('Number',
                                                          normalize_location)},
                                  query_key=query_key,
                                  reply_key=reply_key)
    else:
        locations = read_locations(locations)
        items = read_inventory(inventory)
        items.update(read_inventory(stock))
        items.update(read_inventory(project_parts))
        books = read_books(books)
        if cli:
            StorageShell(sys.stdout, locations, items, books).cmdloop()
        else:
            if things[0] in commands:
                run_command(sys.stdout, things[0], things[1:],
                            locations, items, books)
            else:
                run_command(sys.stdout, "where", things,
                            locations, items, books)

if __name__ == "__main__":
    storage(**get_args())

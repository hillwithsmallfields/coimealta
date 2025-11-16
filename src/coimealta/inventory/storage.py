#!/usr/bin/env python3
import argparse
import cmd
import collections
import dobishem.storage
import functools
import json
import math
import operator
import os
import re
import shlex
import sys

from typing import List, Optional

import decouple

STORAGE_BASE=500000

HAS_CLIENT_SERVER = True
try:
    import simple_client_server.client_server as client_server
except:
    HAS_CLIENT_SERVER = False

INVENTORY_COLUMNS = "Label number,Item,Type,Subtype,Subsubtype,Normal location,Origin,Acquired,Brand,Model,Serial number,Usefulness,Nostalgia,Fun,Approx value when bought,Condition,Status,Disposal,Notes".split(",")
BOOK_COLUMNS = "Number,MediaType,Title,Authors,Publisher,Year,ISBN,Area,Subject,Language,Source,Acquired,Location,Read,Lent,Comments,webchecked".split(",")
LOCATION_COLUMNS = "Number,Description,Level,Type,Variety,Size,ContainedWithin".split(",")

# What plausibly stacks within what:
HIERARCHY = {
    'bag': 1,
    'box': 1,
    'chest': 1,
    'crate': 1,
    'stacking crate': 1,
    'bookshelf': 2,
    'chair': 2,
    'cupboard shelf': 2,
    'drawer': 2,
    'louvre panel': 2,
    'racklevel': 2,
    'shelf': 2,
    'bay': 3,
    'cupboard': 3,
    'drawers': 3,
    'dresser': 3,
    'dressing table': 3,
    'furniture': 3,
    'pegboard': 3,
    'pigeonholes': 3,
    'rack': 3,
    'shelves': 3,
    'stand': 3,
    'room': 4,
    'building': 5,
    'vehicle': 5,
    }

# factor to convert metre of bookshelf to litre of books
# the 10 is because a litre is a decimetre along each side
BOOKSHELF_AREA = 10 * 2 * 1.5

class Storer:

    def __init__(self, locations, items, books, initial_type='book', verbose=False):
        self.locations = locations
        self.items = items
        self.books = books
        self.current_type = initial_type[0:4]
        self.current_location = None
        self.last_was_location = False
        self.last_enclosing_previous_location = None
        self.last_enclosed = None
        self.verbose=verbose

    def store(self, token):
        """Process a token in a token stream indicating where things are stored.

        The token is currently assumed to be number, typically from a barcode scanner.

        If it is in the range indicating a storage location, subsequent tokens will
        be recorded as stored in that location.

        Returns whether the item collection, the book collection, and
        the location collection were modified.
        """
        if token in ('book', 'books', 'item', 'items'):
            self.current_type = token[0:4]
            return False, False, False
        else:
            if not token:
                return False, False, False
            token = int(token)
            if token >= STORAGE_BASE:
                if self.last_was_location:
                    # consecutive entries being locations means we're
                    # indicating that subsequent locations are nested
                    # within the first of this run of locations
                    this_location = token - STORAGE_BASE
                    outer = self.locations.get(self.current_location)
                    if (inner := self.locations.get(this_location)):
                        if HIERARCHY.get(inner['Type'], 0) < HIERARCHY.get(outer['Type'], 0):
                            # boxes go on shelves, etc
                            if self.verbose:
                                print("nesting %s within %s" % (inner['Description'], outer['Description']))
                            self.last_enclosing_previous_location = inner['ContainedWithin']
                            self.last_enclosed = inner
                            inner['ContainedWithin'] = self.current_location
                            return False, False, True
                        else:
                            # typically, move on to the next shelf
                            self.current_location = this_location
                            if self.verbose:
                                print("moving on to recording within %s" % inner['Description'])
                else:
                    self.current_location = token - STORAGE_BASE
                    old_type = self.current_type
                    self.current_type = ('book'
                                         if self.locations[self.current_location].get('Type') == 'bookshelf'
                                         else 'item')
                    if self.verbose and self.current_type != old_type:
                        print("switched to storing %ss as the current location is a %s" % (
                            self.current_type, self.locations[self.current_location]['Type']))
                self.last_was_location = True
                return False, False, False
            else:
                self.last_was_location = False
                if self.last_enclosing_previous_location:
                    # We have just switched from putting boxes on
                    # shelves to putting things in boxes.  We don't
                    # want the box we're putting things in to be
                    # placed on the shelf, but it will have been, as
                    # it will have been the last box placed on the
                    # shelf.  So undo that.
                    if self.verbose:
                        print("Undoing nesting of", self.last_enclosed['Description'])
                    self.last_enclosed['ContainedWithin'] = self.last_enclosing_previous_location
                    self.last_enclosing_previous_location = None
                if self.current_type == 'book':
                    if token not in self.books:
                        print("Warning: No book with identity", token)
                        return False, False, False
                    if self.verbose:
                        print("storing book %s (%s) in location %s (%s)" % (
                            self.books[token]['Title'], token,
                            describe_location(self.locations.get(self.current_location)), self.current_location))
                    store_book(self.books, token, self.current_location)
                    return False, True, False
                else:
                    if token not in self.items:
                        print("Warning: No item with identity", token)
                        return False, False, False
                    if self.verbose:
                        print("storing item %s (%s) in location %s (%s)" % (
                            self.items[token]['Item'], token,
                            describe_location(self.locations.get(self.current_location)), self.current_location))
                    store_item(self.items, token, self.current_location)
                    return True, False, False

class StorageShell(cmd.Cmd):

    prompt = "Storage> "

    def __init__(self, outstream,
                 locations_file, locations,
                 items_file, items,
                 books_file, books,
                 verbose=False):
        super().__init__()
        self.outstream = outstream
        self.locations_file = locations_file
        self.locations = locations
        self.items_file = items_file
        self.items = items
        self.books_file = books_file
        self.books = books
        self.verbose = verbose

    def postcmd(self, stop, _line):
        return stop

    def do_list_books(self, *_args):
        """Show a table of where all the books are."""
        by_location = collections.defaultdict(list)
        for idx, book in self.books.items():
            if 'Location' in book:
                by_location[book['Location']].append(idx)
        for loc in sorted(by_location.keys()):
            contents = by_location[loc]
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
            label_width = max([len(label) for label in capacity_by_type.keys()])
            self.outstream.write(loctype.rjust(label_width) + " " + str(math.ceil(capacity_by_type[loctype])) + "\n")
        self.outstream.write("Total container volume: " + str(volume) + " litres\n")
        self.outstream.write("Total container and book (estimate) volume: "
                             + str(volume + bookshelf_length * BOOKSHELF_AREA)
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
        for item_type in sorted(types.keys(), key=lambda x: x or ""):
            subtypes = types[item_type]
            self.outstream.write((item_type or "unspecified")
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
        # TODO: option to print table of where all inventory items are
        by_location = collections.defaultdict(list)
        for idx, item in self.items.items():
            if 'Normal location' in item:
                by_location[item['Normal location']].append(idx)
        for loc in sorted(by_location.keys()):
            contents = by_location[loc]
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
        for where in sorted(locations_matching_patterns(self.locations, things)):
            list_location(self.outstream, where, "", self.locations, self.items, self.books)
        return False

    def do_find_things(self, *args):
        """Show the locations of things.
        This finds books, other items, and locations."""
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

    def do_store(self, *args):
        """Put things into locations.

        It may be given a sequence of numbers as args; if not given any as args,
        it will read the numbers from stdin.

        Numbers may either be locations or items/books.  A location
        sets where subsequent items or books will be stored.  Books
        and other items will be distinguished by whether the location
        is a bookshelf or not.  Consecutive locations represent the
        storing of containers within containers (e.g. boxes on a
        shelf).
        """
        items_stored = False
        books_stored = False
        locations_nested = False
        thing_type="books"
        storer = Storer(self.locations,
                        self.items, self.books,
                        initial_type=thing_type,
                        verbose=self.verbose)
        if args and any(args):  # ignore empty args
            for arg in args:
                for word in arg.split(' '):
                    item_stored, book_stored, location_nested = storer.store(word)
                    items_stored |= item_stored
                    books_stored |= book_stored
                    locations_nested = location_nested
        else:
            done = False
            for line in sys.stdin.readlines():
                for token in line.split():
                    if token == 'quit':
                        done = True
                        break
                    item_stored, book_stored, location_nested = storer.store(token)
                    items_stored |= item_stored
                    books_stored |= book_stored
                    locations_nested = location_nested
                if done:
                    break
        if items_stored:
            with dobishem.storage.FileProtection(self.items_file):
                dobishem.storage.write_csv(self.items_file,
                                           self.items,
                                           sort_columns=INVENTORY_COLUMNS)
        if books_stored:
            with dobishem.storage.FileProtection(self.books_file):
                dobishem.storage.write_csv(self.books_file,
                                           self.books,
                                           sort_columns=BOOK_COLUMNS)
        if locations_nested:
            with dobishem.storage.FileProtection(self.locations_file):
                dobishem.storage.write_csv(self.locations_file,
                                           self.locations,
                                           sort_columns=LOCATION_COLUMNS)

def normalize_book_entry(row):
    """Put the entry describing a book into our standard form."""
    ex_libris = row['Number']
    row['Number'] = (int(ex_libris)
                     if isinstance(ex_libris, str) and ex_libris != ""
                     else 0)
    location = row['Location']
    row['Location'] = (int(location)
                       if isinstance(location, str) and location != ""
                       else 0)
    return row

def read_books(books_file, _key=None):
    """Read the books file."""
    return dobishem.storage.read_csv(books_file,
                                     result_type=dict,
                                     row_type=dict,
                                     key_column='Number',
                                     empty_for_missing=True,
                                     transform_row=normalize_book_entry)

# Description for reading these files using client_server.py:
# ('Number', normalize_book_entry)

def book_matches(book, pattern):
    """Return whether a pattern matches any of the main characteristics of a book,"""
    pattern = re.compile(pattern , re.IGNORECASE)
    return (book['Title'] and pattern.search(book['Title'])
            or book['Authors'] and pattern.search(book['Authors'])
            or book['Publisher'] and pattern.search(book['Publisher'])
            or book['ISBN'] and pattern.search(book['ISBN'])
            or book['Area'] and pattern.search(book['Area']))

def books_matching(book_index, pattern):
    """Return a list of books matching a given pattern."""
    return [book
            for book in book_index.values()
            if book_matches(book, pattern) ]

unlabelled = 0

def normalize_item_entry(row):
    """Put an item entry into our standard form."""
    global unlabelled
    label_number = row.get('Label number', "")
    row['Label number'] = (int(label_number)
                           if isinstance(label_number, str) and label_number != ""
                           else (unlabelled := unlabelled-1))
    normal_location = row['Normal location']
    row['Normal location'] = (int(normal_location)
                              if isinstance(normal_location, str) and re.match("[0-9]+", normal_location)
                              else 0)
    return row

def read_inventory(inventory_file, key='Label number'):
    """Read an inventory file."""
    return dobishem.storage.read_csv(inventory_file,
                                     result_type=dict,
                                     row_type=dict,
                                     key_column=key,
                                     empty_for_missing=True,
                                     transform_row=normalize_item_entry)

# Description for reading these files using client_server.py:
# ('Label number', normalize_item_entry)

def item_matches(item, pattern):
    """Return whether an item matches a pattern."""
    pattern = re.compile(pattern , re.IGNORECASE)
    return (pattern.search(item['Item'])
            or (item['Type'] and pattern.search(item['Type']))
            or (item['Subtype'] and pattern.search(item['Subtype'])))

def items_matching(inventory_index, pattern):
    """Return a list of items matching a pattern."""
    return [item
             for item in inventory_index.values()
             if item_matches(item, pattern) ]

def store_item(inventory_index, item, location):
    """Record that an item is in a location."""
    inventory_index[item]['Normal location'] = location

def store_book(inventory_index, book, location):
    """Record that a book is in a location."""
    inventory_index[book]['Location'] = location

def normalize_location(row):
    """Put a location entry into our standard form."""
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
    """Read a storage locations file."""
    return dobishem.storage.read_csv(locations_file,
                                     result_type=dict,
                                     row_type=dict,
                                     key_column='Number',
                                     empty_for_missing=True,
                                     transform_row=normalize_location)

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
    description = ("on " if storage_type in ("shelf", "bookshelf") else "in ") + description
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
        StorageShell(
            outstream=output_catcher,
            locations_file=filenames['locations'],
            locations=files_data[filenames['locations']],
            items_file=inventory,
            items=items_data,
            books_file=filenames['books'],
            books=files_data[filenames['books']],
        ).onecmd(in_string)
        return output_catcher.getvalue()
    else:
        return "Command was empty"

def get_args():
    parser = argparse.ArgumentParser()
    # parser.add_argument("--config", "-c",
    #                     default="/usr/local/share/storage.yaml",
    #                     help="""The config file for the storage system.""")
    parser.add_argument("--locations", "-f",
                        default=os.path.expandvars("$ORG/storage.csv"),
                        help="""The CSV file containing the storage locations.""")
    parser.add_argument("--books", "-b",
                        default=os.path.expandvars("$ORG/books.csv"),
                        help="""The CSV file containing the book catalogue.""")
    parser.add_argument("--inventory", "-i",
                        default=os.path.expandvars("$ORG/inventory.csv"),
                        help="""The CSV file containing the general inventory.""")
    parser.add_argument("--stock", "-s",
                        default=os.path.expandvars("$ORG/stock.csv"),
                        help="""The CSV file containing the stock material inventory.""")
    parser.add_argument("--project-parts", "-p",
                        default=os.path.expandvars("$ORG/project-parts.csv"),
                        help="""The CSV file containing the project parts inventory.""")
    parser.add_argument("--verbose", "-v",
                        action='store_true',
                        help="""Output explanatory information.""")
    actions = parser.add_mutually_exclusive_group()
    actions.add_argument("--server", action='store_true',
                        help="""Run a little CLI on a network socket.""")
    actions.add_argument("--cli", action='store_true',
                         help="""Run a little CLI on stdin and stdout.""")
    if HAS_CLIENT_SERVER:
        client_server.client_server_add_arguments(parser, 9797, include_keys=False)
    parser.add_argument("things",
                        nargs='*',
                        help="""The things to look for.""")
    return vars(parser.parse_args())

def storage(locations,
            books,
            inventory,
            stock,
            project_parts,
            verbose: bool=False,
            server: bool=False,
            cli: bool=False,
            host: str=None,
            port: str=None,
            tcp: bool=True,
            things: Optional[List[str]]=None):
    if server:
        global filenames
        filenames = {'inventory': os.path.basename(inventory),
                     'books': os.path.basename(books),
                     'stock': os.path.basename(stock),
                     'project_parts': os.path.basename(project_parts),
                     'locations': os.path.basename(locations)}
        if HAS_CLIENT_SERVER:
            query_passphrase = decouple.config('query_passphrase')
            reply_passphrase = decouple.config('reply_passphrase')
            client_server.check_private_key_privacy(args)
            query_key, reply_key = client_server.read_keys_from_files(args,
                                                                      query_passphrase,
                                                                      reply_passphrase)
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
        # now we're writing data back, don't merge these in
        # TODO: work out what to do instead for these
        # items.update(read_inventory(stock))
        # items.update(read_inventory(project_parts))
        command_handler = StorageShell(outstream=sys.stdout,
                                       locations_file=locations,
                                       locations=read_locations(locations),
                                       items_file=inventory,
                                       items=read_inventory(inventory),
                                       books_file=books,
                                       books=read_books(books),
                                       verbose=verbose)
        if cli:
            command_handler.cmdloop()
        else:
            if (things[0]
                # the list of command keywords
                in command_handler.completenames("")):
                command_handler.onecmd(" ".join(things))
            else:
                command_handler.onecmd("find_things " + " ".join(things))

if __name__ == "__main__":
    storage(**get_args())

#!/usr/bin/env python
import argparse
from backports import csv
import io
import json
import operator
import os
import re
import sys

def normalize_book_entry(row):
    ex_libris = row['Number']
    if ex_libris != "":
        ex_libris = int(ex_libris)
        row['Number'] = ex_libris
    location = row['Location']
    if location != "":
        location = int(location)
        row['Location'] = location
    return row

def read_books(books_file):
    with io.open(books_file, 'r', encoding='utf-8') as input:
        return { book['Number']: book
                 for book in map(normalize_book_entry, [row
                                                        for row in csv.DictReader(input)])
                 if book['Number'] != "" }

def book_matches(book, pattern):
    pattern = re.compile(pattern , re.IGNORECASE)
    return (pattern.search(book['Title'])
            or pattern.search(book['Authors'])
            or pattern.search(book['Publisher'])
            or pattern.search(book['ISBN'])
            or pattern.search(book['Area']))

def books_matching(book_index, pattern):
    return [ book
             for book in book_index.values()
             if book_matches(book, pattern) ]

def list_books(outstream, args, locations, items, books):
    """Show a table of where all the books are."""
    # todo: print table of where all books are
    return True

unlabelled = -1

def normalize_item_entry(row):
    global unlabelled
    label_number = row.get('Label number', "")
    if label_number != "":
        label_number = int(label_number)
        row['Label number'] = label_number
    else:
        row['Label number'] = unlabelled
        unlabelled -= 1
    normal_location = row['Normal location']
    if normal_location and re.match("[0-9]+", normal_location):
        normal_location = int(normal_location)
        row['Normal location'] = normal_location
    return row

def read_inventory(inventory_file):
    if os.path.exists(inventory_file):
        with io.open(inventory_file, 'r', encoding='utf-8') as input:
            return { item['Label number']: item
                     for item in map(normalize_item_entry,
                                     [ row
                                       for row in csv.DictReader(input) ])}
    else:
        return {}

def item_matches(item, pattern):
    pattern = re.compile(pattern , re.IGNORECASE)
    return (pattern.search(item['Item'])
            or (item['Type'] and pattern.search(item['Type']))
            or (item['Subtype'] and pattern.search(item['Subtype'])))

def items_matching(inventory_index, pattern):
    return [ item
             for item in inventory_index.values()
             if item_matches(item, pattern) ]

def list_items(outstream, args, locations, items, books):
    """Show a table of where all the items are."""
    # todo: option to print table of where all inventory items are
    return True

def name_completions(outstream, things, locations, items, books):
    """Return the names matching a fragment."""
    if len(things) == 0:
        return ""
    fragment = things[0]
    outstream.write(json.dumps(sorted(
        [ book['Title']
          for book in books.values()
          if fragment in book['Title'] ]
        + [ item['Item']
            for item in items.values()
            if fragment in item['Item'] ]))
                    + "\n")

def normalize_location(row):
    contained_within = row['ContainedWithin']
    row['ContainedWithin'] = (int(contained_within)
                              if contained_within != ""
                              else None)
    number = row['Number']
    row['Number'] = int(number) if number != "" else None
    return row

def read_locations(locations_file):
    with io.open(locations_file, 'r', encoding='utf-8') as input:
        return { location['Number']: location
                 for location in map(normalize_location, [ row
                                                           for row in csv.DictReader(input) ])
                 if row['Number'] is not None}

def locations_matching(locations_index, pattern):
    """Return a list of location numbers for locations that match a regexp."""
    pattern = re.compile(pattern, re.IGNORECASE)
    return [ loc['Number']
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
    location = int(location)
    while location:
        if location not in locations:
            break
        where = locations[location]
        description = describe_location(where)
        result.append(description)
        location = where['ContainedWithin']
    return result

def describe_nested_location(locations, location):
    """Return a description of a location, along with any surrounding locations."""
    return (" which is ".join(nested_location(locations, location))
            if location != ""
            else "unknown")

def counts(outstream, args, locations, items, books):
    """Count how many of each type of thing I have."""
    types = {}
    for item in items.values():
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
        print item_type if item_type != "" else "unspecified", reduce(operator.add, subtypes.values())
        for subtype in sorted(subtypes.keys ()):
            print "    ", subtype if subtype != "" else "unspecified", subtypes[subtype]

def capacities(outstream, args, locations, items, books):
    """Analyze the storage capacities.
Shows how much of each type of storage there is, and also a summary
combining the types."""
    capacities = {}
    for location in locations.values():
        loctype = location['Type'].lower()
        locsize = location['Size'].lower()
        if loctype != "" and locsize != "":
            capacities[loctype] = float(capacities.get(loctype, 0)) + float(locsize)
    for loctype in sorted(capacities.keys()):
        label_width = max(*map(len, capacities.keys()))
        outstream.write(loctype.rjust(label_width) + " " + str(capacities[loctype]) + "\n")
    volume = reduce(operator.add,
                    map(lambda loctype: capacities.get(loctype, 0),
                        ('box', 'crate', 'drawer', 'cupboard')))
    length = reduce(operator.add,
                    map(lambda loctype: capacities.get(loctype, 0),
                        ('shelf', 'shelves', 'cupboard shelf', 'racklevel')))
    area = reduce(operator.add,
                  map(lambda loctype: capacities.get(loctype, 0),
                        ('louvre panel', 'pegboard')))
    outstream.write("Total container volume: " + str(volume) + " litres\n")
    outstream.write("Total shelving length: " + str(length) + " metres\n")
    outstream.write("Total panel area: " + str(area) + " square metres\n")
    return True

def construct_surrounders(locations):
    s = {}
    for loc_num, loc_descr in locations.iteritems():
        around = loc_descr['ContainedWithin']
        if around:
            if around in s:
                s[around].append(loc_num)
            else:
                s[around] = [loc_num]
    return s

def add_contained_storage(matching_locations, locations, surrounders, loc_number):
    if loc_number in surrounders:
        for inner_container in surrounders[loc_number]:
            matching_locations[inner_container] = locations[inner_container]
            add_contained_storage(matching_locations, locations, surrounders, inner_container)

surrounders = None

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

def list_locations(outstream, things, locations, items, books):
    """List everything that is in the matching locations."""
    for where in locations_matching_patterns(locations, things):
        list_location(outstream, where, "", locations, items, books)

def location_completions(outstream, things, locations, items, books):
    """Return the location names matching a fragment."""
    if len(things) == 0:
        return ""
    fragment = things[0]
    outstream.write(json.dumps(sorted(
        [ location['Description']
          for location in locations.values()
          if fragment in location['Description'] ]))
                    + "\n")

def find_things(outstream, args, locations, items, books):
    """Show the locations of things.
This finds books, other items, and locations."""
    findings = {}
    for thing in args:
        if re.match("[0-9]+", thing):
            as_location = describe_nested_location(locations, thing)
            if as_location != []:
                findings[thing] = as_location
        for book in books_matching(books, thing):
            findings[book['Title']] = describe_nested_location(locations, book['Location'])
        for item in items_matching(items, thing):
            findings[item['Item']] = describe_nested_location(locations, item['Normal location'])
    for finding in sorted(findings.keys()):
        outstream.write(finding + " is " + findings[finding] + "\n")
    return True

def cmd_help(outstream, args, locations, items, books):
    """Display some help."""
    if len(args) == 0:
        outstream.write("Commands are:\n")
        max_command_length = max(*map(len, commands.keys()))
        for command in sorted(commands.keys()):
            outstream.write("  " + command.rjust(max_command_length)
                            + ": " + commands[command].__doc__.split('\n')[0] + "\n")
    else:
        for topic in args:
            if topic in commands:
                outstream.write(topic + ":\n" + commands[topic].__doc__ + "\n")
            else:
                outstream.write(topic + ":\n" + topic
                                + """ is not a command.  Type "help" for a list of commands.\n""")
    return True

def cmd_quit(outstream, args, locations, items, books):
    """Stop the CLI."""
    return False

def cmd_bad(outstream, args, locations, items, books):
    """Report an invalid command."""
    outstream.write("""Bad command; enter "help" to get a list of commands\n""")
    return True

commands = {
    'books': list_books,
    'capacities': capacities,
    'counts': counts,
    'help': cmd_help,
    'items': list_items,
    'names': name_completions,
    'places': location_completions,
    'quit': cmd_quit,
    'what': list_locations,
    'where': find_things
}

def run_command(outstream,
                command,
                things,
                locations,
                items, books):
    return commands.get(command, cmd_bad)(outstream,
                                          things,
                                          locations,
                                          items,
                                          books)

def cli(instream, outstream, prompt, locations, items, books):
    """Run a command loop using stdin and stdout."""
    while True:
        if prompt:
            outstream.write(prompt)
        line_parts = instream.readline().strip().split()
        if len(line_parts) == 0:
            continue
        if not run_command(outstream,
                           line_parts[0],
                           line_parts[1:],
                           locations,
                           items, books):
            break

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
                        help="""The CSV file containing the general inventory.""")
    parser.add_argument("--stock", "-s",
                        default=os.path.join(org_files, "stock.csv"),
                        help="""The CSV file containing the stock material inventory.""")
    parser.add_argument("--project-parts", "-p",
                        default=os.path.join(org_files, "project-parts.csv"),
                        help="""The CSV file containing the project parts inventory.""")
    actions = parser.add_mutually_exclusive_group()
    actions.add_argument("--server", action='store_true',
                        help="""Run a little CLI on a network socket.""")
    actions.add_argument("--cli", action='store_true',
                         help="""Run a little CLI on stdin and stdout.""")
    parser.add_argument("things",
                        nargs='*',
                        help="""The things to look for.""")
    args = parser.parse_args()
    locations = read_locations(args.locations)
    items = read_inventory(args.inventory)
    items.update(read_inventory(args.stock))
    items.update(read_inventory(args.project_parts))
    books = read_books(args.books)
    if args.cli:
        cli(sys.stdin, sys.stdout, "storage> ", locations, items, books)
    elif args.server:
        pass # cli(inputsocket, outputsocket, None, locations, items, books)
    else:
        if args.things[0] in commands:
            run_command(sys.stdout, args.things[0], args.things[1:],
                        locations, items, books)
        else:
            run_command(sys.stdout, "where", args.things,
                        locations, items, books)

if __name__ == "__main__":
    main()

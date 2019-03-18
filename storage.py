#!/usr/bin/env python
import argparse
from backports import csv
import io
import operator
import os
import re
import sys

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
    pattern = re.compile(pattern , re.IGNORECASE)
    return (pattern.search(item['Item'])
            or pattern.search(item['Type'])
            or pattern.search(item['Subtype']))

def items_matching(inventory_index, pattern):
    return [ item
             for item in inventory_index.values()
             if item_matches(item, pattern) ]

def list_items(outstream, args, locations, items, books):
    """Show a table of where all the items are."""
    # todo: option to print table of where all inventory items are
    return True

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
                row['Number'] = number
                locations[int(number)] = row
    return locations

def nested_location(locations, location):
    result = []
    location = int(location)
    while location:
        if location not in locations:
            break
        where = locations[location]
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
        result.append(description)
        location = where['ContainedWithin']
    return result

def describe_location(locations, location):
    return (" which is ".join(nested_location(locations, location))
            if location != ""
            else "unknown")

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

def list_locations(outstream, things, locations, items, books):
    """List everything that is in the matching locations.
When complete, this should list them hierarchically."""
    global surrounders
    # todo: make this list things hierarchically (as it goes, in one loop, instead of saving all up for the end)
    if surrounders is None:
        surrounders = construct_surrounders(locations)
    matching_locations = {}
    for loc_name in things:
        loc_match = re.compile(loc_name, re.IGNORECASE)
        for loc in locations.values():
            if loc_match.search(loc['Description']):
                loc_number = int(loc['Number'])
                matching_locations[loc_number] = loc
                add_contained_storage(matching_locations, locations, surrounders, loc_number)
    for loc_number in sorted(matching_locations.keys()):
        things_here = []
        for thing in items.values():
            if thing['Normal_location'] == loc_number:
                things_here.append(thing)
        # todo: add books
        location = matching_locations[loc_number]
        description = location['Description']
        level = location['Level']
        if level != "":
            description += " level " + str(level)
        if len(things_here) == 0:
            outstream.write(description + " has no known direct contents\n")
        else:
            outstream.write(description + " contains\n")
            for what in things_here:
                outstream.write("    " + what['Item'] + "\n")
    return True

def find_things(outstream, args, locations, items, books):
    """Show the locations of things.
This finds books, other items, and locations."""
    findings = {}
    for thing in args:
        if re.match("[0-9]+", thing):
            as_location = describe_location(locations, thing)
            if as_location != []:
                findings[thing] = as_location
        for book in books_matching(books, thing):
            findings[book['Title']] = describe_location(locations, book['Location'])
        for item in items_matching(items, thing):
            findings[item['Item']] = describe_location(locations, item['Normal_location'])
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
    'where': find_things,
    'items': list_items,
    'books': list_books,
    'what': list_locations,
    'capacities': capacities,
    'help': cmd_help,
    'quit': cmd_quit
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
                        help="""The CSV file containing the inventory.""")
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

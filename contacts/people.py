#!/usr/bin/env python

import argparse
from backports import csv
import io
import sys
import os

# Fields to split into lists
multi_fields = ['Parents', 'Offspring', 'Siblings',
                'Partners', 'Ex-partners',
                'Knows',
                'Organizations']

def make_name(person):
    return ' '.join([person.get('Given name', "")]
                    + person.get('Middle names', "").split(" ")
                    + [person.get('Surname', "")])

def make_name_list(people):
    # todo: collect together all the people of the same surname and format that as "Fred, Freddie and Freda Smith and John and Jane Jones"
    return ", ".join([resi['_name_'] for resi in people])

def assemble_postal_address(who, spacer="; "):
    """Return a postal address."""
    address = []
    for key in ['Street', 'City', 'Region', 'Postal Code', 'Country']:
        value = who[key]
        if value != "":
            address += value.split("; ")
    return spacer.join(address)

def show_person(out, who):
    out.write(who['_name_'] + "\n")
    email = who['Primary email']
    if email != "":
        out.write("    Email: " + email + "\n")
    phone = who['Primary phone Value']
    if phone != "":
        phone_type = who['Primary phone Type']
        out.write("    " + (phone_type if phone_type != "" else "Phone") + ': ' + phone + "\n")
    if who['Street'] != "":
        out.write("    Address:\n        "
                  + assemble_postal_address(who, "\n        ")
                  + "\n")

def main():
    parser = argparse.ArgumentParser()
    org_files = os.environ.get("ORG", "~/org")
    parser.add_argument("--contacts", "-c",
                        default=os.path.join(org_files, "contacts.csv"),
                        help="""The CSV file containing the contact details.""")
    parser.add_argument("--flag", "-f",
                        action='store_true',
                        help="""Search by flag.""")
    parser.add_argument("names",
                        nargs='*',
                        help="""The names to look for.""")
    args = parser.parse_args()
    by_name = {}
    by_id = {}
    with io.open(args.contacts, 'r', encoding='utf-8') as input:
        contacts_reader = csv.DictReader(input)
        for row in contacts_reader:
            for multi in multi_fields:
                row[multi] = (row.get(multi, "") or "").split(";")
            n = make_name(row)
            row['_name_'] = n
            by_name[n] = row
            by_id[id] = row.get('ID', "")
    if args.flag != "":
        flag = args.names[0]
        by_address = {}
        for n in sorted(by_name.keys()):
            who = by_name[n]
            if flag in who['Flags']:
                addr = assemble_postal_address(who, "\n  ")
                if addr not in by_address:
                    by_address[addr] = []
                by_address[addr].append(who)
        for addr in sorted(by_address.keys()):
            sys.stdout.write(make_name_list(by_address[addr])
                             + "\n  " + addr + "\n\n")
    else:
        name = " ".join(args.names)
        if name in by_name:
            show_person(sys.stdout, by_name[name])
        else:
            for n in sorted(by_name.keys()):
                if name in n:
                    show_person(sys.stdout, by_name[n])

if __name__ == "__main__":
    main()

#!/usr/bin/env python3

import argparse
import re
import json
import sys

import coimealta.contacts.contacts_data as contacts_data

def safesearch(flags, text):
    print("Searching", text)
    return flags.search(text)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-f", "--flag", action='append')
    parser.add_argument("-g", "--group", action='append')
    parser.add_argument("-a", "--all", action='store_true')
    parser.add_argument("-s", "--surname", action='append')
    parser.add_argument("-G", "--given", action='append')
    parser.add_argument("-N", "--no-add-family",
                        help="""Without this option, if someone is selected but their partner
                        or children aren't, those are added automatically to the selection.""")
    parser.add_argument("-p", "--postal-addresses",
                        action='store_true',
                        help="""List people by address, grouping together those at the same address.
                        Without this, people are listed individually, with their email addresses.""")
    parser.add_argument("-e", "--email-addresses",
                        action='store_true',
                        help="""List people by email address.""")
    parser.add_argument("-j", "--json", action='store_true',
                        help="""Output full details as JSON.""")
    parser.add_argument("input")
    args = parser.parse_args()
    by_id, _ = contacts_data.read_contacts(args.input)
    if args.all:
        selected = by_id.values()
    else:
        selected = []
        if args.flag:
            flags = re.compile("[" + "".join(args.flag) + "]")
            selected += [someone for someone in by_id.values()
                         if flags.search(someone.get('Flags', "") or "")]
        if args.group:
            groups = set(args.group)
            selected += [someone for someone in by_id.values()
                         if len((groups.intersection(someone['_groups_']))) > 0]
        if args.surname:
            surnames = set(args.surname)
            selected += [someone for someone in by_id.values()
                         if someone['Surname'] in surnames]
        if args.given:
            given_names = set(args.given)
            selected += [someone for someone in by_id.values()
                         if someone['Given name'] in given_names]
        if not args.no_add_family:
            invited_ids = [whoever['ID'] for whoever in selected]
            for whoever in selected:
                for partner in whoever['Partners']:
                    if partner not in invited_ids:
                        # todo: make this only if they are at the same address
                        selected.append(by_id[partner])
            for whoever in selected:
                for offspring in whoever['Offspring']:
                    if offspring not in invited_ids:
                        print(contacts_data.make_name(by_id[offspring]), "  -- maybe add")
                        # todo: make this only if they are at the same address
                        selected.append(by_id[offspring])
    if args.postal_addresses:
        by_address = {}
        for contact in selected:
            address = contacts_data.make_address(contact)
            if address in by_address:
                by_address[address].append(contact)
            else:
                by_address[address] = [contact]
        print(len(by_address), "addresses")
        print("")
        for addr, residents in by_address.items():
            print(contacts_data.names_string(residents))
            print("  " + "\n  ".join([a for a in addr if a != ""]))
            print("")
    else:
        for contact in selected:
            if args.email_addresses:
                email = contact['Primary email']
                if email != "":
                    print(email + " <" + contact['_name_'] + ">")
            elif args.json:
                json.dump(contact, sys.stdout)
            else:
                print(contact['_name_'])

if __name__ == "__main__":
    main()

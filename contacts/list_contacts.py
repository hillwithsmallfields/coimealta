#!/usr/bin/env python

import argparse
import re
import contacts_data

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-f", "--flag", action='append')
    parser.add_argument("-g", "--group", action='append')
    parser.add_argument("-N", "--no-add-family",
                        help="""Without this option, if someone is selected but their partner
                        or children aren't, those are added automatically to the selection.""")
    parser.add_argument("-p", "--postal-addresses",
                        action='store_true',
                        help="""List people by address, grouping together those at the same address.
                        Without this, people are listed individually, with their email addresses.""")
    parser.add_argument("input")
    args = parser.parse_args()
    by_id, _ = contacts_data.read_contacts(args.input)
    selected = []
    if args.flag:
        flags = re.compile("[" + "".join(args.flag) + "]")
        selected += [someone for someone in by_id.values()
                     if flags.search(someone['Flags'])]
    if args.group:
        groups = set(args.group)
        selected += [someone for someone in by_id.values()
                     if len((groups.intersection(someone['_groups_']))) > 0]
    if not args.no_add_family:
        invited_ids = [whoever['ID'] for whoever in selected]
        for whoever in selected:
            for partner in whoever['Partners']:
                if partner not in invited_ids:
                    # todo: make this only if they are at the same address
                    selected.append(by_id[partner])
        for whoever in selected:
            print whoever['_name_'], "has offspring", whoever['Offspring']
            for offspring in whoever['Offspring']:
                print "  ", offspring
                if offspring not in invited_ids:
                    print "  -- needs inviting"
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
        for addr, residents in by_address.iteritems():
            # todo: sort residents to bring oldest (or most ancestral) to the start
            names = [contacts_data.make_name(person) for person in residents]
            print ", ".join(names[:-1])+" and "+names[-1] if len(names) >= 2 else names[0]
            print "  " + "\n  ".join([a for a in addr if a != ""])
            print ""
    else:
        for contact in selected:
            if args.email_addresses:
                email = contact['Primary email']
                if email != "":
                    print email + " <" + contact['_name_'] + ">"
            else:
                print contact['_name_']

if __name__ == "__main__":
    main()

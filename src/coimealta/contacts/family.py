#!/usr/bin/env python3

import argparse
import collections
import os

import coimealta.contacts.contacts_data as contacts_data

def gv_people_list(people):
    return "{" + ",".join(people) + "}"

def family_graph_main(person, across, contacts, output):

    """Update the connections between people, in the contacts file.
    Fills in the other direction for any that are given in only
    one direction."""

    by_id, by_name = contacts_data.read_contacts(contacts)

    starting_person = by_name.get(person, by_id.get(person))
    if not starting_person:
        raise ValueError("Could not find " + person)

    already_seen = set()
    already_linked = {}
    couples = collections.defaultdict(set)
    singles = set()
    queue = [starting_person['ID']]

    def add(p_id):
        if p_id not in already_seen:
            queue.append(p_id)

    def link(from_id, to_id, style):
        link_key = (from_id, to_id) if from_id < to_id else (to_id, from_id)
        if link_key not in already_linked:
            already_linked[link_key] = f"      {from_id} -> {to_id} {style}\n"

    def write_person(uid, person, margin="  "):
        outstream.write(f"""{margin}{uid} [label="{person['_initialled_name_']}" shape={("hexagon" if person['Gender'] == 'm' else "octagon")} {"style=dashed" if person['Died'] else ""}]\n""")

    with open(output or (person + ".gv"), "w") as outstream:
        outstream.write("digraph {\n")
        if across:
            outstream.write("  rankdir=LR\n")
        while queue:
            uid = queue.pop()
            person = by_id[uid]
            already_seen.add(uid)
            their_offspring = person['Offspring'] or []
            for offspring in their_offspring:
                link(uid, offspring, "[style=solid]")
                add(offspring)
            their_parents = person['Parents'] or []
            for parent in their_parents:
                link(parent, uid, "[style=solid]")
                add(parent)
            their_partners = person['Partners']
            if their_partners:
                for partner in their_partners:
                    couple_id = "_".join(sorted([uid] + list(their_partners)))
                    couples[couple_id].add(uid)
                    link(uid, partner, "[style=bold arrowhead=none]")
                    add(partner)
            else:
                singles.add(uid)
        for who in singles:
            write_person(who, by_id[who])
        for couple_key, couple_members in couples.items():
            outstream.write(f"  subgraph cluster_{couple_key}" + " {\n")
            for member in couple_members:
                write_person(member, by_id[member], margin="    ")
            outstream.write("  }\n")
            # outstream.write("    {rank=same " + uid + " " + gv_people_list(their_partners) + "}\n")
        for link in already_linked.values():
            outstream.write(link)
        outstream.write("}\n")

def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--contacts", "-c",
                        default=os.path.expandvars("$ORG/contacts.csv"),
                        help="""Name of contacts file.""")
    parser.add_argument("--output", "-o",
                        help="""Name of output file.""")
    parser.add_argument("--across", action='store_true')
    parser.add_argument("person",
                        help="""Name or ID of person to start from.""")
    return vars(parser.parse_args())

if __name__ == "__main__":
    family_graph_main(**get_args())

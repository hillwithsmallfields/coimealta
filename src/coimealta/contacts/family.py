#!/usr/bin/env python3

import argparse
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
        print("Could not find", person)
        raise ValueError("Could not find " + person)

    already_written = set()
    already_linked = set()
    queue = [starting_person['ID']]

    def add(p_id):
        if p_id not in already_written:
            queue.append(p_id)

    def link(from_id, to_id, style):
        link = (from_id, to_id) if from_id < to_id else (to_id, from_id)
        if link not in already_linked:
            outstream.write(f"      {from_id} -> {to_id} {style}\n")
            already_linked.add(link)

    with open(output or (person + ".gv"), "w") as outstream:
        outstream.write("digraph {\n")
        if across:
            outstream.write("  rankdir=LR\n")
        while queue:
            uid = queue.pop()
            person = by_id[uid]
            already_written.add(uid)
            outstream.write(f"""  {uid} [label="{person['_name_']}" shape={("box" if person['Gender'] == 'm' else "diamond")} {"style=dashed" if person['Died'] else ""}]\n""")
            their_partners = person['Partners'] or []
            their_offspring = person['Offspring'] or []
            their_parents = person['Parents'] or []
            for partner in their_partners:
                link(uid, partner, "")
                outstream.write("    {rank=same " + uid + " " + gv_people_list(their_partners) + "}\n")
                add(partner)
            for offspring in their_offspring:
                link(uid, offspring, "[style=dotted]")
                add(offspring)
            for parent in their_parents:
                link(parent, uid, "[style=dashed]")
                add(parent)
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

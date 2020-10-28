#!/usr/bin/env python3

import argparse
import re
import contacts_data

def offspring(person):
    return person['Offspring']

def parents(person):
    return person['Parents']

def partners(person):
    return person['Partners']

def siblings(person):
    return person['Siblings']

def normalize_to_IDs(people, by_name):
    return set([ (person
                  if re.match("[G-Z][0-9][A-Z][0-9]", person)
                  else by_name[person.replace('_', ' ')]['ID'])
                 for person in people ])

def find_siblings(person, by_id):
    sibs = person['Siblings']
    more = True
    if len(sibs) > 0:
        while more:
            for sib in list(person['Siblings']):
                sibsibs = by_id[sib]['Siblings']
                more = False
                for sibsib in sibsibs:
                    if sibsib not in sibs:
                        sibs.add(sibsib)
                        more = True
    yourself = person['ID']
    if yourself in sibs:
        sibs.remove(yourself)
    return sibs

def name(person):
    return person['_name_']

def accumulate(person, aspect, by_aspect):
    aspect = person[aspect]
    if aspect not in by_aspect:
        by_aspect[aspect] = []
    by_aspect[aspect].append(id)

def print_summary(by_aspect, label):
    by_frequency = {}
    for k, v in by_aspect.iteritems():
        frequency = len(v)
        if frequency not in by_frequency:
            by_frequency[frequency] = []
        by_frequency[frequency].append(k)
    print(label, "; ".join(
        [ "; ".join(
            ["%s(%d)" % (bf, freq)
             for bf in sorted(by_frequency[freq])])
          for freq in reversed(sorted(by_frequency.keys()))]))

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--analyze", action='store_true')
    parser.add_argument("--graph", action='store_true')
    parser.add_argument("input")
    parser.add_argument("output")
    args = parser.parse_args()
    by_nationality = {}
    by_gender = {}
    by_title = {}
    by_place_met = {}

    print("Reading contacts from", args.input)
    by_id, by_name = contacts_data.read_contacts(args.input)

    for person in by_id.values():
        person['Parents'] = normalize_to_IDs(person['Parents'], by_name)
        person['Offspring'] = normalize_to_IDs(person['Offspring'], by_name)
        person['Siblings'] = normalize_to_IDs(person['Siblings'], by_name)
        person['Partners'] = normalize_to_IDs(person['Partners'], by_name)
        person['Knows'] = normalize_to_IDs(person['Knows'], by_name)

    for person_id, person in by_id.iteritems():
        partner_ids = person['Partners']
        if len(partner_ids) == 1: # don't try this on non-monogamists
            partner = by_id[next(iter(partner_ids))]
            partners_partners = partner['Partners']
            if len(partners_partners) == 0: # again, for monogamists only
                partner['Partners'].add(person_id)
        for parent_id in person['Parents']:
            parent = by_id[parent_id]
            if person_id not in parent['Offspring']:
                parent['Offspring'].add(person_id)
        for offspring_id in person['Offspring']:
            child = by_id[offspring_id]
            if person_id not in child['Parents']:
                child['Parents'].add(person_id)
        for sibling_id in find_siblings(person, by_id):
            sibling = by_id[sibling_id]
            if person_id not in sibling['Siblings']:
                sibling['Siblings'].add(person_id)
        # todo: mutualize contacts

    if args.analyze:
        for id, person in by_id.iteritems():
            accumulate(person, 'Nationality', by_nationality)
            accumulate(person, 'Gender', by_gender)
            accumulate(person, 'Title', by_title)
            accumulate(person, 'Place met', by_place_met)
        n_people = len(by_id)
        print(n_people, "people")
        print_summary(by_nationality, "nationalities:")
        print_summary(by_gender, "genders:")
        print_summary(by_title, "titles:")
        print_summary(by_place_met, "places met:")
        ordained = contacts_data.count_grouped_titles(by_title, ["Revd", "Revd Dr", "Revd Prof", "RtRevd"])
        doctored = contacts_data.count_grouped_titles(by_title, ["Dr", "Revd Dr", "Prof", "Revd Prof"])
        print("%d ordained (%d%% of the people you know)" % (ordained, ordained*100 / n_people))
        print("%d with doctorates (%d%% of the people you know)" % (doctored, doctored * 100 / n_people))

    if args.graph:
        print("digraph {")
        for id, person in by_id.iteritems():
            their_partners = person['Partners']
            their_offspring = person['Offspring']
            their_parents = person['Parents']
            if len(their_partners) > 0 or len(their_offspring) > 0 or len(their_parents) > 0:
                print("  ", id, '[label="' + person['_name_'] + '" shape=' + ("box" if person['Gender'] == 'm' else "diamond") + "]")
            if len(their_partners) > 0:
                print("    ", id, "->", "{", ",".join(their_partners), "}")
                print("    {rank=same", id, " ".join(their_partners), "}")
            if len(their_offspring) > 0:
                print("    ", id, "->", "{", ",".join(their_offspring), "} [style=dotted]")
                print("    {rank=same", " ".join(their_offspring), "}")
            if len(their_parents) > 0:
                print("    ", id, "->", "{", ",".join(their_parents), "} [style=dashed]")
        print("}")

    contacts_data.write_contacts(args.output, by_name)

if __name__ == "__main__":
    main()

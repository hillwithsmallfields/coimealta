# from backports import csv
import csv
import io
import operator
import random

def count_grouped_titles(title_map, titles):
    """Count people with titles in a list of titles."""
    return reduce(operator.add,
                  [len(title_map[title]) for title in titles])

fieldnames = ['Given name', 'Middle names', 'Surname', 'Title', 'Old name', 'AKA',
              'Birthday', 'Died',
              'First contact', 'Last contact',
              'Gender',
              'ID', 'Parents', 'Offspring', 'Siblings', 'Partners', 'Ex-partners', 'Knows', 'Nationality',
              'Notes',
              'Group Membership', 'Flags', 'Other groups', 'Organizations', 'Place met',
              'Subjects', 'Jobs',
              'Primary email', 'Other emails',
              'Primary phone Type', 'Primary phone Value',
              'Secondary phone Type', 'Secondary phone Value',
              'Street', 'Village/District', 'City', 'County', 'State', 'Postal Code', 'Country', 'Extended Address']

# Fields to split into lists
multi_fields = ['Parents', 'Offspring', 'Siblings',
                'Partners', 'Ex-partners',
                'Knows',
                'Group Membership',
                'Organizations',
                'Other groups']

def make_name(person):
    return ' '.join([person.get('Given name', "")]
                    + person.get('Middle names', "").split()
                    + [person.get('Surname', "")])

def make_address(person):
    return (person.get('Street', ""),
            person.get('Village/District', ""),
            person.get('City', ""),
            person.get('County', ""),
            person.get('State', ""),
            person.get('Postal Code', ""),
            person.get('Country'))

def make_ID():
    return (str(chr(random.randint(0, 19) + ord('G')))
            + str(chr(random.randint(0, 9) + ord('0')))
            + str(chr(random.randint(0, 25) + ord('A')))
            + str(chr(random.randint(0, 9) + ord('0'))))

def read_contacts(filename):
    by_id = {}
    by_name = {}
    without_id = []
    with io.open(filename, 'r', encoding='utf-8') as instream:
        contacts_reader = csv.DictReader(instream)
        for row in contacts_reader:
            n = make_name(row)
            row['_name_'] = n
            by_name[n] = row
            uid = row.get('ID', "")
            if uid is not None and uid != "":
                by_id[uid] = row
            else:
                without_id.append(row)
            for multi in multi_fields:
                row[multi] = set((row.get(multi, "") or "").split())
            row['_groups_'] = row['Group Membership'].union(row['Organizations'],
                                                            row['Other groups'])

    for person in without_id:
        uid = make_ID()
        while uid in by_id:
            uid = make_ID()
        person['ID'] = uid
        by_id[uid] = person

    return by_id, by_name

def write_contacts(filename, by_name):
    with io.open(filename, 'w', encoding='utf-8') as output:
        contacts_writer = csv.DictWriter(output, fieldnames)
        contacts_writer.writeheader()
        for nm in sorted(by_name.keys()):
            row = by_name[nm]
            # print row
            for multi in multi_fields:
                row[multi] = ' '.join(row[multi])
            del row['_name_']
            del row['_groups_']
            contacts_writer.writerow(row)
            try:
                contacts_writer.writerow(row)
            except ValueError:
                print("Unwritable row: ", row)

"""Read, access, handle, and write data describing contacts.

The data is stored in a CSV file."""

import csv
import datetime
import functools
import operator
import os
import random
import re
import shutil
import tempfile

def count_grouped_titles(title_map, titles):
    """Count people with titles in a list of titles."""
    return functools.reduce(operator.add,
                            [len(title_map[title]) for title in titles])

FIELD_NAMES = ['Given name', 'Middle names', 'Surname', 'Title', 'Old name', 'AKA',
              'Birthday', 'Died',
              'First contact', 'In touch',
              'Gender',
              'ID', 'Parents', 'Offspring', 'Siblings',
              'Partners', 'Ex-partners', 'Knows',
              'Notes',
              'Flags',
              'Nationality', 'Place met',
              'Group Membership', 'Other groups', 'Organizations',
              'Universities', 'College', 'Subjects', 'Jobs',
              'Primary email', 'Other emails',
              'Primary phone Type', 'Primary phone Value',
              'Secondary phone Type', 'Secondary phone Value',
              'Street', 'Village/District', 'City', 'County', 'State',
              'Postal Code', 'Country', 'Extended Address']

# Fields to split into lists
MULTI_FIELDS = ['Parents', 'Offspring', 'Siblings',
                'Partners', 'Ex-partners',
                'Knows',
                'Group Membership',
                'Organizations',
                'Other groups']

def make_name(person):
    """Assemble a name from a person's fields."""
    first_name = (person.get('Given name', "") or "")
    middle_names = [name
                    for name in (person.get('Middle names', "") or "").split(' ')
                    if name]
    surname = (person.get('Surname', "") or "")
    return (first_name + " " + " ".join(middle_names) + " " + surname
            if middle_names
            else first_name + " " + surname)

def make_initialled_name(person):
    """Assemble a name from a person's fields."""
    first_name = (person.get('Given name', "") or "")
    middle_names = [name[0] + "."
                    for name in (person.get('Middle names', "") or "").split(' ')
                    if name]
    surname = (person.get('Surname', "") or "")
    return (first_name + " " + " ".join(middle_names) + " " + surname
            if middle_names
            else first_name + " " + surname)

def make_short_name(person):
    """Make a short form of a person's name."""
    return ' '.join([(person.get('Given name', "") or "")]
                    + [(person.get('Surname', "") or "")])

def string_list_with_and(items):
    """Return a comma-joined list of items using 'and' as I think appropriate."""
    return (", ".join(items[:-1])
            + ", and "
            + items[-1] if len(items) > 2 else items[0]
            + " and "
            + items[1] if len(items) == 2 else items[0])

# TODO: sort residents to bring oldest (or most ancestral) to the start
def names_string(people):
    """Return a string representing the names of several people."""
    by_surname = {}
    for person in people:
        surname = person.get('Surname', "")
        if surname not in by_surname:
            by_surname[surname] = []
        by_surname[surname].append(person.get('Given name', ""))
    names = [string_list_with_and(sorted(by_surname[surname]))
             + " "
             + surname for surname in sorted(by_surname.keys())]
    return string_list_with_and(names)

def make_address(person):
    """Put together an address tuple."""
    return (person.get('Street', ""),
            person.get('Village/District', ""),
            person.get('City', ""),
            person.get('County', ""),
            person.get('State', ""),
            person.get('Postal Code', ""),
            person.get('Country'))

def make_ID():
    """Make a letter-digit-letter-digit random ID that is not a valid hex string."""
    return (str(chr(random.randint(0, 19) + ord('G')))
            + str(chr(random.randint(0, 9) + ord('0')))
            + str(chr(random.randint(0, 25) + ord('A')))
            + str(chr(random.randint(0, 9) + ord('0'))))

def age_in_year(person, year):
    """Return how old a person is in a given year."""
    bday = person.get('Birthday', "") or ""
    match = re.match("[0-9][0-9][0-9][0-9]", bday)
    return (year - int(match.group(0))) if match else None

def birthday(person, this_year):
    """Return this year's birthday of a person, as a datetime.date.
    Returns None if their birthday is unknown or not in a recognised format."""
    bday_string = person.get('Birthday', "") or ""
    if bday_string == "":
        return None
    try:
        return datetime.date.fromisoformat(bday_string).replace(year=this_year)
    except ValueError:          # not a full ISOdate, try some subsets:
        match = re.search("-([0-9][0-9])-([0-9][0-9])", bday_string)
        if match:
            month = int(match.group(1))
            if month == 0:
                return None
            day = int(match.group(2))
            if day == 0:
                return None
            return datetime.date(year=this_year, month=month, day=day).replace(year=this_year)
        return None

def birthday_soon(person, this_year, today, within_days=30):
    """Return whether a person has a birthday soon."""
    bday = birthday(person, this_year)
    if not bday:
        return False
    interval_to_birthday = (bday - today).days
    return 0 <= interval_to_birthday < within_days

def last_contacted(person):
    """Return when I was last in touch with a person, or None if not recorded.
    The input is a person dictionary, and the result is a datetime.date."""
    cday_string = person.get('In touch', "")
    if not cday_string:
        return None
    try:
        return datetime.date.fromisoformat(cday_string)
    except ValueError:          # not a full ISOdate, try some subsets:
        match = re.search("([0-9][0-9][0-9][0-9])-([0-9][0-9])", cday_string)
        if match:
            year = int(match.group(1))
            if year == 0:
                return False
            month = int(match.group(2))
            return datetime.date(year=year, month=month if month > 0 else 1, day=1)
        match = re.search("([0-9][0-9][0-9][0-9])", cday_string)
        return datetime.date(year=int(match.group(1)), month=1, day=1) if match else None

def contact_soon(person, today, days_since_last_contact=90):
    """Return whether I haven't registered a contact with someone in a given time."""
    cday = last_contacted(person)
    # TODO: have a contact frequency field in the data for each person
    return cday and (today - cday).days > days_since_last_contact

def record_contact(person, date=None):
    """Record that I have contacted someone on a given date."""
    if date is None:
        date = datetime.date.today()
    set_field_if_greater(person, "last-contacted", date)
    set_field_if_not_empty(person, "keep-in-touch", date)

def age_string(person, year):
    """Return a person's age, as a string."""
    age = age_in_year(person, year)
    return str(age) if age else "?"

def by_name(people, name):
    return people.get(name)

def set_field_if_empty(person, field, value):
    """Set a field of a person dictionary only if there is no value already in that field."""
    if person and (field not in person or person[field] == ""):
        person[field] = value
        return True
    return False

def set_field_if_not_empty(person, field, value):
    """Set a field of a person dictionary only if there is already a value in that field."""
    if person and (field in person and person[field] != ""):
        person[field] = value
        return True
    return False

def set_field_if_greater(person, field, value):
    """Set a field of a person dictionary if the new value is greater than the old one."""
    if (person
        and (field not in person
             or person[field] == ""
             or value > person[field])):
        person[field] = value
        return True
    return False

def set_field(person, field, value):
    """Set a field of a person dictionary.
    None-safe."""
    if person:
        person[field] = value
        return True
    return False

def read_contacts(filename):
    """Read a contacts file and return a tuple of dictionaries.
    The first one lists contacts by ID, and the second by name."""
    people_by_id = {}
    people_by_name = {}
    without_id = []
    with open(os.path.expandvars(filename)) as instream:
        for row in csv.DictReader(instream):
            name = make_name(row)
            short_name = make_short_name(row)
            row['_name_'] = name
            row['_initialled_name_'] = make_initialled_name(row)
            people_by_name[name] = row
            # if short_name != name:
            #     people_by_name[short_name] = row
            uid = row.get('ID', "")
            if uid is not None and uid != "":
                people_by_id[uid] = row
            else:
                without_id.append(row)
            for multi in MULTI_FIELDS:
                row[multi] = set(
                    item.strip()
                    for item in
                    (row.get(multi, "") or "").split(';')
                    if item
                )
            row['_groups_'] = row['Group Membership'].union(row['Organizations'],
                                                            row['Other groups'])

    for person in without_id:
        uid = make_ID()
        while uid in people_by_id:
            uid = make_ID()
        person['ID'] = uid
        people_by_id[uid] = person

    return people_by_id, people_by_name

def write_contacts(filename, people_by_name):
    """Write a dictionary of contacts-by-name to a file.

    The data is written to a temporary file, and only copied to the
    specified file if there were no unwritable entries.
    """
    all_found_fields = set().union(*[set(row.keys()) for row in people_by_name.values()])
    if all_found_fields != set(FIELD_NAMES):
        print("These extra fields were found:", all_found_fields - set(FIELD_NAMES))
    with open(tempfile.NamedTemporaryFile(delete_on_close=False, suffix='.csv'), 'w') as output:
        tempname = output.name
        fails = 0
        contacts_writer = csv.DictWriter(output, FIELD_NAMES)
        contacts_writer.writeheader()
        for name in sorted(people_by_name.keys()):
            row = people_by_name[name]
            # print row
            for multi in MULTI_FIELDS:
                # print("converting", multi, row[multi])
                row[multi] = '; '.join(sorted(list(row[multi])))
                # print("converted", multi, row[multi])
            for deledend in ('', '_name_', '_initialled_name_', '_groups_'):
                if deledend in row:
                    del row[deledend]
            try:
                contacts_writer.writerow(row)
            except ValueError as ve:
                fails += 1
                print("Unwritable row:", row, "because of", ve)
    if fails == 0:
        shutil.copyfile(tempname, os.path.expandvars(filename))
        os.unlink(tempname)

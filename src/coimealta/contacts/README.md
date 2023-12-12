Contacts
========

Having had my contacts information spread out over bbdb and gmail
contacts, I decided to have one central definitive file, in an open
format.

Entries are cross-linked for family relationships, using a short UID
system (letter-digit-letter-digit, short enough to keep in your head
while editing links between people), to show who is in the same family
(with the aim of being able to group people together for sending
Christmas cards).

Programs
========

link_contacts.py
----------------

Processes a contacts file, converting names found in the link fields
to UIDs, then adding any missing links implied by the links that are
present.  The output goes to a separate file, to give you a chance to
check it before replacing the original file with it.  Any entries
without a link field are given one at random.

Usage:

    link-contacts.py [--analyze] [--graph] infile outfile

The `--analyze` option produces a report on the proportions of people
you know by gender, Dr-status, Revd-status, and nationality (and I may
add others from time to time).

The `--graph` option outputs graphviz-formatted data to show
connections between the people you know.  Not currently very good.

list_contacts.py
----------------

people.py
---------

csv-contacts.el
---------------

Files
=====

All people in the file must have distinct names, using the `Middle
names` field if necessary (imaginatively if necessary).

contacts.csv
------------

  - `Given name`
  - `Middle names`
  - `Surname`
  - `Title` Titles are partly for addressing people correctly for
    posting Christmas cards etc, and partly because I think I live in
    a bit of an educated and religious bubble and wanted to find what
    proportion of the people I know have "Dr" or "Revd" against their
    names.
  - `Old name` --- maiden names etc
  - `AKA`
  - `Birthday` so you can filter for upcoming birthdays
  - `Died` so you don't continue to send things when someone has died
    (but may want to send condolences to the bereaved); this is better
    than removing entries when people die, to preserve the links
    between their relatives.
  - `First contact` when you met someone
  - `Last contact` so you can indicate that you've lost contact with someone
  - `Gender` I wondered whether, as a programmer, I might know a lot
    more men than women (it turns out I know about the same number of each)
  - `ID` using the letter-number-letter-number system mentioned above
  - `Parents` by IDs, but if you put names there, `link-contacts.py`
    will convert them to IDs; use spaces between them, not commas, as
    CSV uses commas as delimiters but isn't strictly defined as to how
    to handle commas inside cells
  - `Offspring`as for `Parents`
  - `Siblings`as for `Parents`
  - `Partners` as for `Parents`
  - `Ex-partners` as for `Parents`
  - `Knows` linked as for `Parents`; out of interest, for constructing graphs
  - `Nationality` because I woondered how many countries I know people
    from (it turned out to be about 50)
  - `Notes`
  - `Group Membership`
  - `Flags` for filtering the list, for purposes like making your
    Christmas card list
  - `Other groups`
  - `Organizations`
  - `Place met`
  - `Subjects`
  - `Jobs`
  - `Primary email`
  - `Other emails`
  - `Primary phone Type`
  - `Primary phone Value`
  - `Secondary phone Type`
  - `Secondary phone Value`
  - `Street`
  - `City`
  - `Region`
  - `Postal Code`
  - `Country`
  - `Extended Address`
  

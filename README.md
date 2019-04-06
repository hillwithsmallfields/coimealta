John's inventories
==================

Simple CSV-based system for cataloguing my possessions and tracking
where I've put them.  I'm using bar-coded numbered labels on things
and storage locations, but the code should work alright without that.

I'm not currently planning a house move, but this should be good
groundwork for when I do.

It may also be helpful for tracking lending items to other people.

Programs
========

storage.py
----------

This is the main program, and it looks for where an item is stored, or
reports about storage locations.  It can be run as a one-shot command
line, or as a CLI, and when complete, as a server over TCP or UDP.

It takes the first entry on its command line, or an input line when
running as a CLI, as a command, and the rest as things to look for, if
relevant.

  - `books`
  - `capacities`
  - `counts`
  - `help`
  - `items`
  - `names`
  - `places`
  - `quit`
  - `what`
  - `where`

If you've filled in the sizes of storage locations, `capacities` will
tell you your total box volume and shelf length (aimed mostly at for
when I do eventually move house).

books.py
--------

This helps with entering book data, by looking up incomplete entries
by their ISBN numbers and filling them in where possible.  It marks
which entries it has processed, to avoid pestering the online database
repeatedly about books it doesn't know about.

Files
=====

By default, the inventory files are called `$ORG/inventory.csv` and
`$ORG/books.csv`, and the locations file is called `$ORG/storage.csv`.

`inventory.csv` is expected to have these columns:

  - Label number
  - Item
  - Type
  - Subtype
  - Normal location
  - Origin
  - Acquired
  - Brand
  - Model
  - Serial number
  - Usefulness
  - Nostalgia
  - Fun
  - Approx value when bought
  - Condition
  - Status

`Label number` is for your personal numbering of items; I stuck
serial-numbered barcoded name labels on all my non-trivial non-fabric
items, and on the coat-hangers for major clothing items.

As the code never writes this file back, this is not a strict list.

`books.csv` is expected to have these columns:

  - Number
  - MediaType
  - Title
  - Authors
  - Publisher
  - Year
  - ISBN
  - Area
  - Subject
  - Language
  - Source
  - Acquired
  - Location
  - Read
  - Lent
  - Comments
  - webchecked
  
The `Number` field is for your own catalogue numbering; I stuck
serial-numbered barcoded "Ex-libris" stickers inside all my books.
It's probably a good idea to make the number range distinct from your
other possession number labels; I thought of this too late for my own
labelling.
  
As `books.py` writes this back, any extra columns will cause an error,
and any omitted ones will be created.

`storage.csv` is expected to have these columns:

  - Number
  - Description
  - Level
  - Type
  - Variety
  - Size
  - ContainedWithin

`Number` lets you number your storage locations.  I got
serial-numbered barcoded stickers and stuck them on my boxes, shelves
etc.  I gave them a different range of numbers from my possessions and
books, with a view to writing a mobile app that can record where I'm
putting things, without having to tell it which barcode is the item
and which is the storage.
  
`ContainedWithin` is the number of the location containing the
location in this row, allowing you to represent a storage hierarchy;
for example, a box may be on a shelf, which is in a room, which is in
a building.

`Variety` lets you enter things like colour, and `Size`, if in actual
units (litres/metres) it can be used by the `capacities` command
of storage.py.  Also, they should help you spot things quickly, such
as `35L red box`.


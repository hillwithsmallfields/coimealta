#!/usr/bin/env python

import argparse
from backports import csv
import io
import isbnlib

fieldnames = ['Number','Title','Authors','Publisher','Year','ISBN','Area','Subject','Language','Source','Acquired','Read','Lent','Comments','webchecked']

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--batchsize", "-b", type=int, default=8)
    parser.add_argument("input")
    parser.add_argument("output")
    args = parser.parse_args()
    countdown = args.batchsize
    with io.open(args.input, 'r', encoding='utf-8') as input:
        books_reader = csv.DictReader(input)
        with io.open(args.output, 'w', encoding='utf-8') as output:
            books_writer = csv.DictWriter(output, fieldnames)
            books_writer.writeheader()
            for row in books_reader:
                print "row is", row
                if countdown > 0 and not row.get('webchecked', None):
                    isbn = row.get('ISBN', None)
                    if isbn:
                        countdown = countdown - 1
                        print "countdown", countdown
                        new_isbn = isbnlib.to_isbn13(isbnlib.canonical(isbn))
                        print "modified ISBN is", isbn
                        if new_isbn is None or new_isbn == "":
                            print "Could not canonicalize isbn", isbn
                        else:
                            row['ISBN'] = new_isbn
                        details = None
                        try:
                            details = isbnlib.meta(isbn)
                        except isbnlib.dev._exceptions.NoDataForSelectorError:
                            print "No data for ISBN", isbn, "title", row.get('Title', "Unknown")
                            row['webchecked'] = "No data for ISBN"
                        except isbnlib._exceptions.NotValidISBNError:
                            print "Invalid ISBN", isbn, "for", row['Title']
                            row['webchecked'] = "Invalid ISBN"
                        if details:
                            print "---"
                            print "Details from web:", details
                            if details.get('ISBN-13', "") != "" and row.get('ISBN', "") == "":
                                row['ISBN'] = details['ISBN-13']
                            if 'Authors' in row:
                                row['Authors'] = row['Authors'].split('/')
                            old_title = row['Title']
                            web_title = details['Title']
                            if old_title != web_title:
                                old_len = len(old_title)
                                web_len = len(web_title)
                                if ((web_len > old_len and old_title in web_title)
                                    or (web_len == old_len and old_title.lower() == web_title.lower())):
                                    print "Title improvement from", old_title, "to", web_title
                                else:
                                    print "Title discrepancy:", old_title, "in file,", web_title, "found online"
                                    details['Title'] = old_title
                            # don't use 'update', because we don't want to drag in random other fields that dictwriter will then object to
                            for key in fieldnames:
                                if key in details:
                                    row[key] = details[key]
                            if 'Authors' in row:
                                row['Authors'] = '/'.join(row['Authors'])
                            print "Combined data:", row
                            row['webchecked'] = "OK"
                else:
                    print "skipping lookup"
                # from https://docs.python.org/2/library/csv.html
                encoded_row = {k: (v.encode("utf-8") if isinstance(v, basestring) else v)
                               for k,v in row.iteritems()}
                books_writer.writerow(row)

if __name__ == "__main__":
    main()

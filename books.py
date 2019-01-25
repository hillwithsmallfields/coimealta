#!/usr/bin/env python

import argparse
import csv
import isbnlib

fieldnames = ['Number','Title','Authors','Publisher','Year','ISBN','Area','Subject','Language','Source','Acquired','Read','Lent','Comments','webchecked']

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--batchsize", "-b", type=int, default=8)
    parser.add_argument("input")
    parser.add_argument("output")
    args = parser.parse_args()
    countdown = args.batchsize
    with open(args.input) as input:
        books_reader = csv.DictReader(input)
        with open(args.output, 'w') as output:
            books_writer = csv.DictWriter(output, fieldnames)
            books_writer.writeheader()
            for row in books_reader:
                isbn = row.get('ISBN', None)
                if row.get('webchecked', False):
                    break
                countdown = countdown - 1
                if countdown <= 0:
                    break
                if isbn:
                    try:
                        details = isbnlib.meta(isbn)
                    except isbnlib.dev._exceptions.NoDataForSelectorError:
                        print "No data for ISBN", isbn, "title", row.get('Title', "Unknown")
                        continue
                    except isbnlib._exceptions.NotValidISBNError:
                        print "Invalid ISBN", isbn, "for", row['Title']
                        continue
                    if details:
                        print "---"
                        print "Details from web:", details
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
                        for key in fieldnames:
                            if key in details:
                                row[key] = details[key]
                        if 'Authors' in row:
                            row['Authors'] = '/'.join(row['Authors'])
                        print "Combined data:", row
                row['webchecked'] = 1
                books_writer.writerow({k: (v.encode("utf-8") if isinstance(v, basestring) else v)
                                       for k,v in row.iteritems()}) # from https://docs.python.org/2/library/csv.html

if __name__ == "__main__":
    main()

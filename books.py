#!/usr/bin/env python

import argparse
import csv
import isbnlib

sample = "9780872431607"

fieldnames = ["Number","Title","Author","Publisher","Date","ISBN","Area","Subject","Language","Source","Acquired","Read","Lent","Comments"]

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input")
    parser.add_argument("output")
    args = parser.parse_args()
    with open(args.input) as input:
        books_reader = csv.DictReader(input)
        with open(args.output, 'w') as output:
            books_writer = csv.DictWriter(output, fieldnames)
            books_writer.writeheader()
            for row in books_reader:
                isbn = row.get('ISBN', None)
                if isbn:
                    details = None
                    try:
                        details = isbnlib.meta(isbn)
                    except isbnlib.dev._exceptions.NoDataForSelectorError:
                        print "No data for ISBN", isbn
                    except isbnlib._exceptions.NotValidISBNError:
                        print "Invalid ISBN", isbn, "for", row['Title']
                    if details:
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
                        # row.update(details)
                        # print "Combined data:", details
                books_writer.writerow(row)

if __name__ == "__main__":
    main()

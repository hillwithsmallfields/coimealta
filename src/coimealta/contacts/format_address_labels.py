#!/usr/bin/python3

import argparse

def read_labels(input_file):
    with open(input_file) as instream:
        all_lines = instream.readlines()
        labels = []
        lines = []
        for line in all_lines:
            line = line.strip()
            if line == "":
                labels.append(lines)
                lines = []
            else:
                lines.append(line)
        labels.append(lines)
    return labels

def labels_to_pages(labels, n_per_page):
    return [labels[i:i + n_per_page] for i in range(0, len(labels), n_per_page)]
    
def begin_page(outstream, w, h):
    outstream.write('<svg width="%gmm" height="%gmm" viewBox="0 0 %g %g">\n' % (w, h, w, h))

def end_page(outstream):
    outstream.write('</svg>\n')

def write_label_at(x, y, config, label_lines, outstream):
    leading = config['leading']
    fontsize = config['label-height'] / ((len(label_lines) + 1) * leading)
    if config['verbose']:
        print("placing", label_lines[0], "at", x, y, "using fontsize", fontsize)
    outstream.write('  <g transform="translate(%g,%g)">\n' % (x, y))
    if config['outline']:
        outstream.write('    <rect x="0" y="0" width="%g" height="%g" fill="white" stroke="green"/>\n' % (config['label-width'], config['label-height']))
    outstream.write('    <g transform="translate(%g,%g)">\n' % (config['label-left-margin'], config['label-top-margin']))
    outstream.write('      <text font-size="%g">\n' % fontsize)
    for iline, line in enumerate(label_lines):
        outstream.write('        <tspan x="0" y="%gem">%s</tspan>\n' % ((iline+1) * leading, line))
    outstream.write('      </text>\n')
    outstream.write('    </g>\n')
    outstream.write('  </g>\n')

def main():
    parser = argparse.ArgumentParser()
    # the defaults are for labelplanet's LP12/99 label sheet
    parser.add_argument("-x", "--across",
                        type=int, default=2,
                        help="""How many labels fit across the page.""")
    parser.add_argument("-y", "--down",
                        type=int, default=6,
                        help="""How many labels fit down the page.""")
    parser.add_argument("-H", "--height",
                        type=float, default=42.3,
                        help="""The height of each label (excluding gap, margins etc)""")
    parser.add_argument("-W", "--width",
                        type=float, default=99.1,
                        help="""The width of each label (excluding gap, margins etc)""")
    parser.add_argument("-t", "--top-margin", "--top",
                        type=float, default=21.6,
                        help="""The top margin of the page.""")
    parser.add_argument("-l", "--left-margin", "--left",
                        type=float, default=4.65,
                        help="""The left margin of the page.""")
    parser.add_argument("-g", "--horizontal-gap",
                        type=float, default=2.5,
                        help="""The horizontal gap between labels.""")
    parser.add_argument("-V", "--vertical-gap",
                        type=float, default=2.5,
                        help="""The vertical gap between labels.""")
    parser.add_argument("-v", "--verbose",
                        action='store_true',
                        help="""Produce explanatory output.""")
    parser.add_argument("-b", "--box",
                        action='store_true',
                        help="""Draw a box around each label.""")
    parser.add_argument("-o", "--output",
                        default="labels-%d.svg",
                        help="""The file to write the formatted labels into.""")
    parser.add_argument("input_file")
    args = parser.parse_args()

    columns = args.across
    rows = args.down

    left_margin = args.left_margin
    top_margin = args.top_margin
    right_margin = left_margin
    bottom_margin = top_margin
    label_width_with_gap = args.width + args.horizontal_gap
    label_height_with_gap = args.height + args.vertical_gap 
    page_width = left_margin + label_width_with_gap * columns + right_margin
    page_height = top_margin + label_height_with_gap * rows + bottom_margin

    config = {
        'outline': args.box,
        'leading': 1.2,
        'label-width': args.width,
        'label-height': args.height,
        'vertical-gap': args.vertical_gap,
        'horizontal-gap': args.horizontal_gap,
        'label-left-margin': 5,
        'label-top-margin': 0,
        'verbose': args.verbose
    }
    
    for ipage, page in enumerate(labels_to_pages(read_labels(args.input_file), rows * columns)):
        with open(args.output % ipage, 'w') as outstream:
            row = 0
            column = 0
            begin_page(outstream, page_width, page_height)
            for label in page:
                write_label_at(left_margin + column * label_width_with_gap,
                               top_margin + row * label_height_with_gap,
                               config,
                               label,
                               outstream)
                row += 1
                if row == rows:
                    if args.verbose:
                        print("next label below the last would be at", top_margin + row * label_height_with_gap)
                    row = 0
                    column += 1
            end_page(outstream)
    
if __name__ == "__main__":
    main()
    

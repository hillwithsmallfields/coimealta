#!/usr/bin/env python3
import argparse
import client_server # the shell script ./storage-client makes this available
import decouple

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('data', nargs='*', action='append',
                        help="""The data to send to the server.""")
    client_server.client_server_add_arguments(parser, 9797)
    args=parser.parse_args()
    args.server = False
    query_passphrase = decouple.config('query_passphrase')
    reply_passphrase = decouple.config('reply_passphrase')
    client_server.check_private_key_privacy(args)
    query_key, reply_key = client_server.read_keys_from_files(args,
                                                              query_passphrase,
                                                              reply_passphrase)
    text = " ".join(args.data[0])

    received = client_server.get_response(
        text,
        args.host, args.port, args.tcp,
        encryption_version=ord('H' if query_key and reply_key else 'p'),
        query_key=query_key,
        reply_key=reply_key)

    print(received)
    return 0

if __name__ == "__main__":
    main()

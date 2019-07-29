#!/usr/bin/env python3

import argparse
import os
import sys
import re
import json
import requests

API_URL = "https://chapi.cloudhealthtech.com/v1/aws_accounts"

def main():
    parser = argparse.ArgumentParser(description='List AWS Accounts')
    parser.add_argument('-i', '--owner-id', required=False, default=None, help='Owner ID (AWS Account ID)')
    parser.add_argument('-k', '--api-key', required=False, default=os.environ.get('CH_API_KEY', None), help='CloudHealth API key')
    parser.add_argument('-p', '--per-page', required=False, default=30, type=int, help='Number of results per page')
    parser.add_argument('-v', '--verbose', required=False, default=False, action='store_true', help='Verbosity')
    args = parser.parse_args()

    if args.api_key is None:
        print("API key not set. Set environnement variable CH_API_KEY or invoke program with option -k/--api-key", file=sys.stderr)
        sys.exit(1)

    if re.match("^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", args.api_key) is None:
        print("API key is not valid. It must be a a globally unique identifier (GUID).", file=sys.stderr)
        print("See https://apidocs.cloudhealthtech.com/#how-cloudhealth-validates-api-requests for more details.", file=sys.stderr)
        sys.exit(1)

    if args.owner_id is not None:
        if (args.owner_id <= 0 or args.owner_id > 999999999999):
            print("'{}' is an invalid AWS account identifier.".format(args.owner_id), file=sys.stderr)
            sys.exit(1)

    if args.per_page <= 0:
        print('-p/--per-page argument must be a positive number.', file=sys.stderr)
        sys.exit(1)

    p = {"page": 1, "per_page": args.per_page}
    h = {"Authorization": "Bearer " + args.api_key, "Content-Type": "application/json"}

    aws_accounts = []
    while True:
        try:
            response = requests.get(API_URL, headers=h, params=p)
            response.raise_for_status()
            if args.verbose:
                print(response.request.url)
        except requests.exceptions.RequestException as e:
            print(e, file=sys.stderr)
            sys.exit(1)

        try:
            accounts = json.loads(response.content).get('aws_accounts')
            if accounts is None or type(accounts) is not list:
                raise ValueError
        except (json.decoder.JSONDecodeError, KeyError, ValueError):
            print('Malformed CloudHealth API response body.')
            sys.exit(1)

        if len(accounts) <= 0:
            break

        p['page'] += 1
        if args.owner_id is None:
            aws_accounts.extend(accounts)
        else:
            f = list(filter(lambda i: i['owner_id'] == args.owner_id, accounts))
            if len(f) > 0:
                aws_accounts.extend(f)
                break

    print(json.dumps(aws_accounts))

if __name__ == "__main__":
    main()

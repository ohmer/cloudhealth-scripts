#!/usr/bin/env python3

import sys
import argparse
import json
import botocore
import boto3


class CachedSession(boto3.session.Session):
    def __init__(self, **kwargs):
        session = botocore.session.get_session()
        kwargs['botocore_session'] = session
        super().__init__(**kwargs)
        session.get_component('credential_provider').get_provider('assume-role').cache = botocore.credentials.JSONFileCache()


def main():
    parser = argparse.ArgumentParser(description='Generate a CloudHealth API schema from a Terraform state stored in a S3')
    parser.add_argument('-b', '--s3-bucket', required=True, help='S3 bucket')
    parser.add_argument('-k', '--s3-key', required=True, help='S3 key')
    parser.add_argument('-p', '--profile', required=False, default='default', help='AWS SDK profile name')
    parser.add_argument('-v', '--verbose', required=False, default=False, action='store_true', help='Verbosity')
    args = parser.parse_args()

    try:
        if args.verbose:
            print("Getting session from profile {}".format(args.profile), file=sys.stderr)

        session = CachedSession(profile_name=args.profile)

        if args.verbose:
            client = session.client('sts')
            response = client.get_caller_identity()
            print("Caller identity is {}".format(response['Arn']), file=sys.stderr)

        s3obj = session.resource('s3').Object(args.s3_bucket, args.s3_key).get()
        state = json.load(s3obj.get('Body'))

        if args.verbose:
            print("state", file=sys.stderr)
            print(json.dumps(state), file=sys.stderr)

    except (json.decoder.JSONDecodeError, KeyError, ValueError) as e:
        print(e, file=sys.stderr)
        print('Malformed S3 response body.', file=sys.stderr)
        sys.exit(1)
    except (botocore.exceptions.ProfileNotFound, botocore.exceptions.ClientError) as e:
        print(str(e), file=sys.stderr)
        sys.exit(1)

    outputs = None
    for m in state.get('modules'):
        if m.get('path') == ['root']:
            outputs = m.get('outputs')
            break

    if outputs is None:
        print("Malformed Terraform state.", file=sys.stderr)
        sys.exit(1)

    if args.verbose:
        print("outputs", file=sys.stderr)
        print(json.dumps(outputs), file=sys.stderr)

    schema = {
        'name': outputs.get('account_alias').get('value'),
        'authentication': {
            'protocol': 'assume_role',
            'assume_role_arn': 'arn:aws:iam::{}:role/{}'.format(
                outputs.get('account_id').get('value'),
                outputs.get('cloudhealth_role_name').get('value')
            ),
            'assume_role_external_id': outputs.get('cloudhealth_role_external_id').get('value'),
            'access_key': '',
            'secret_key': ''
        },
        'billing': {
            'bucket': outputs.get('billing_bucket').get('value') if outputs.get('billing_bucket') else ''
        },
        'cloudtrail': {
            'enabled': outputs.get('cloudtrail_bucket') is not None,
            'bucket': outputs.get('cloudtrail_bucket').get('value') if outputs.get('cloudtrail_bucket') else '',
            'prefix': ''
        },
        'aws_config': {
            'enabled': outputs.get('config_bucket') is not None,
            'bucket': outputs.get('config_bucket').get('value') if outputs.get('config_bucket') else '',
            'prefix': ''
        },
        'cloudwatch': {
            'enabled': True
        },
        'tags': []
    }

    print(json.dumps(schema))

if __name__ == "__main__":
    main()

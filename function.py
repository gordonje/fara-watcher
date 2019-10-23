from datetime import date
import smtplib
import boto3
from botocore.exceptions import ClientError
from dateutil import parser
import requests


AWS_REGION = "us-east-1"
EMAIL_RECIPIENTS = (
    'gordonj@missouri.edu',
    'kielyk@missouri.edu',
    'elisevmulligan@gmail.com',
)


def get_registrant_docs(reg_id):
    # From FARA API docs: https://efile.fara.gov/ords/f?p=107:ENDPOINTS_REGDOCS
    url = f'https://efile.fara.gov/api/v1/RegDocs/json/{reg_id}'
    params = {
        'docType': 'SUPPLEMENTAL_STATEMENT'
    }
    r = requests.get(url, params)
    r.raise_for_status()

    return r.json()['REGISTRANTDOCS']['ROW']


def is_since_today(date_stamped_str):
    date_stamped = parser.parse(date_stamped_str).date()

    return date_stamped >= date.today()


# https://alexwlchan.net/2017/07/listing-s3-keys/
def get_s3_keys():
    """Generate all the keys in an S3 bucket."""
    s3 = boto3.client('s3', region_name=AWS_REGION)
    kwargs = {'Bucket': 'fara-watcher'}
    while True:
        resp = s3.list_objects_v2(**kwargs)
        if 'Contents' in resp:
            for obj in resp['Contents']:
                yield obj['Key']

            try:
                kwargs['ContinuationToken'] = resp['NextContinuationToken']
            except KeyError:
                break
        else:
            break


def get_file_name(url):
    return url.split('/')[-1]


def copy_to_s3(url):
    content = requests.get(url).content
    file_name = get_file_name(url)
    s3 = boto3.client('s3', region_name=AWS_REGION)
    obj = s3.put_object(
        ACL='public-read',
        Body=requests.get(url).content,
        Bucket='fara-watcher',
        Key=file_name,
    )
    return obj


def get_s3_url(file_name):
    return f'https://fara-watcher.s3.amazonaws.com/{file_name}' 


def format_message(context):
    body = '''
    This is an automatic email notification to inform you that a new Supplemental Statement for MSLGROUP Americas is now available, as of {Date_Stamped}.

    The official URL for this document is {Url}.

    You will also find a backup of this document at {s3_url}.
    '''.format(**context)
    return {
        'Body': {
            'Text': {
                'Charset': "UTF-8",
                'Data': body,
            },
        },
        'Subject': {
            'Charset': "UTF-8",
            'Data': "New Supplemental Statement for MSLGROUP Americas",
        },
    }


def send_email(recipient, message):
    # From AWS SES docs: https://docs.aws.amazon.com/ses/latest/DeveloperGuide/send-using-sdk-python.html
    ses = boto3.client('ses', region_name=AWS_REGION)
    try:
        response = ses.send_email(
            Destination={
                'ToAddresses': [recipient],
            },
            Message=message,
            Source="James Gordon <gordonj@rjionline.org>",
        )
    except ClientError as e:
        print(e.response['Error']['Message'])
    else:
        print("Email sent! Message ID:"),
        print(response['MessageId'])


def main():
    docs = get_registrant_docs(5483)

    stored_docs = [d for d in get_s3_keys()]

    new_docs = [
        d for d in docs if is_since_today(d['Date_Stamped'])
        and get_file_name(d['Url']) not in stored_docs
    ]

    if len(new_docs) > 0:
        for d in new_docs:
            s3_obj = copy_to_s3(d['Url'])
            file_name = get_file_name(d['Url'])
            
            context = d
            context['s3_url'] = get_s3_url(file_name)
            msg = format_message(context)
            
            for recipient in EMAIL_RECIPIENTS:
                send_email(recipient, msg)

    return {'message' : f"Count new docs: {len(new_docs)}"}  


def lambda_handler(event, context):
    return main()


if __name__ == "__main__":
    main()

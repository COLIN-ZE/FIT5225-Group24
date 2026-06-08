import boto3
import os
import json

sns = boto3.client('sns')
TOPIC_ARN = os.environ['SNS_TOPIC_ARN']

def lambda_handler(event, context):
    print("=== EVENT ===")
    print(json.dumps(event, default=str))
    print("triggerSource:", event.get('triggerSource'))

    email = event['request']['userAttributes']['email']
    print("email:", email)

    try:
        resp = sns.subscribe(
            TopicArn=TOPIC_ARN,
            Protocol='email',
            Endpoint=email,
            ReturnSubscriptionArn=True,
            Attributes={
                'FilterPolicy': json.dumps({'species': ['__none__']}),
            },
        )
        print("SUBSCRIBE OK:", resp['SubscriptionArn'])
    except Exception as e:
        print("SUBSCRIBE FAILED:", str(e))
        raise

    return event

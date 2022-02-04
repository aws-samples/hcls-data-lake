import json, logging, boto3
import random
import os

logger = logging.getLogger()
logger.setLevel(logging.INFO)

sf = boto3.client('stepfunctions')
sns = boto3.client('sns')

def lambda_handler(event, lambda_context):
  # Get data that was passed from SNS
  input_data = {
    'MessageId': event['Records'][0]['Sns']['MessageId'],
    'Message':event['Records'][0]['Sns']['Message'],
    'MessageAttributes': event['Records'][0]['Sns']['MessageAttributes']
  }
  logger.info(input_data)

  # Invoke our parser
  response = sf.start_sync_execution(
    stateMachineArn=os.environ['state_machine'],
    input= json.dumps({'Message': input_data['Message']})
  )
  status = response['status']

  if status == 'SUCCEEDED':
    msg = response['output']
    state = 'staged'
    format_type = 'json'
    logger.info(status)
  elif status == 'FAILED':
    msg = response['input']
    state = 'error'
    format_type = "txt"
    logger.warn(response['error'])

  # Publish to pub-sub-hub
  sns.publish(
    TopicArn=os.environ['topic'],
    Message=msg,
    MessageAttributes={
      'event': {
        'DataType': 'String',
        'StringValue': state,
      },
      'protocol': {
        'DataType': 'String',
        'StringValue': 'hl7v2',
      },
      'format': {
        'DataType': 'String',
        'StringValue': format_type,
      },
      'source': {
        'DataType': 'String',
        'StringValue': input_data['MessageId'], 
      }
    }
  )
  logger.info("Published to SNS topic")
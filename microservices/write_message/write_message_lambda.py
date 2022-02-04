import boto3, json, os, logging
import hashlib, uuid
from botocore.exceptions import ClientError
from boto3.dynamodb.conditions import Key, Attr

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize clients outside of the main function to reuse between calls
sns = boto3.client('sns')
s3 = boto3.client('s3')
catalog = boto3.resource('dynamodb').Table(os.environ['catalog'])


def lambda_handler(event, context):
  logger.info(event)
  
  # Get data that was passed from SNS
  data = {
    'MessageId': event['Records'][0]['Sns']['MessageId'],
    'Message':event['Records'][0]['Sns']['Message'], 
    'MessageAttributes': event['Records'][0]['Sns']['MessageAttributes']
    
  }
  logger.info(data)
  logger.info(data['MessageAttributes'])
  msg = data['Message']
  

  #---------- Write to the data lake
  
  # Determine the attributes
  protocol = data['MessageAttributes']['protocol']['Value']
  format_type = data['MessageAttributes']['format']['Value']
  source = data['MessageAttributes']['source']['Value']
  event = data['MessageAttributes']['event']['Value']
  
  if event == 'ingested': zone = 'ingestion'
  elif event == 'staged': zone = 'staging'
  elif event == 'error': zone = 'error'
  
  if format_type == 'json':
    content_type = "application/json; charset=utf-8"
  else:
    content_type = "text/plain; charset=utf-8"
  
  # Assemble the key
  key = zone + '/protocol=' + protocol + '/' + data['MessageId'] +"." +format_type
  logger.info('Key: {}'.format(key))
  
  # Write to the bucket
  s3.put_object(
    Bucket = os.environ['bucket_name'],
    Key=key,
    Body=msg,
    ContentType=content_type
  )
  logger.info("Message written to S3 bucket")
  
  # Update the catalog
  catalog.put_item(
    Item={
      'message_id': data['MessageId'],
      'bucket': os.environ['bucket_name'],
      'key': key,
      'source': source
    }
  )
  logger.info("Catalog updated")
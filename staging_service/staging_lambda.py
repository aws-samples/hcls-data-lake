import json, logging, boto3
import random
import os

logger = logging.getLogger()
logger.setLevel(logging.INFO)

s3 = boto3.client('s3')

def lambda_handler(event, lambda_context):
  logger.info(event)
  
  # Get data that was passed from SNS
  data = {'Message':event['Records'][0]['Sns']['Message'],
  'MessageAttributes': event['Records'][0]['Sns']['MessageAttributes']
  }
  logger.info(data)
  
  logger.info(data['MessageAttributes'])
  
  metadata = {
    'source_bucket':data['MessageAttributes']['ingest_bucket']['Value'],
    'source_key': data['MessageAttributes']['ingest_key']['Value']
  }
  
  hl7v2_json = data['Message']
  logger.info(hl7v2_json)
    
  s3.put_object(
    Bucket = os.environ['bucket_name'],
    Key='staging/my_test_{}.json'.format(str(random.randint(0,999999999))),
    Body=hl7v2_json,
    ContentType="application/json; charset=utf-8",
    Metadata=metadata
  )
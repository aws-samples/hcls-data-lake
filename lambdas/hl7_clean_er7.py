import json
import logging
import boto3

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# This can be made more robust with some regex
def fix_segment_terminator(message, segment_terminator):
  return message.replace(segment_terminator, "\r") # \r is the only allowed segment terminator in HL7v2

def lambda_handler(event, context):
  logger.info("Start")
  logger.info(event)
  
  s3 = boto3.client('s3')
  bucket_name = event['bucketName']
  object_key = event['key']

  response = s3.get_object(Bucket=bucket_name, Key=object_key)
  
  er7 = response["Body"].read().decode("utf-8")
  logger.info(er7)
  metadata = response["Metadata"]
  logger.info(metadata)
  
  # Correct segment terminators
  segTerm = json.loads(metadata["seg-term"])
  for s in segTerm:
    er7 = fix_segment_terminator(er7, s)

  event['er7'] = er7
  return event
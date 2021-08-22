import boto3
import os, json, base64
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def encode_to_base64(string, encoding):
  str_bytes = string.encode(encoding)
  base64_bytes = base64.b64encode(str_bytes)
  return base64_bytes.decode(encoding)

def lambda_handler(event, context):
  logger.info("Start")
  logger.debug(event)
  
  s3 = boto3.client('s3')
  bucket = os.environ['data_lake_bucket']
  
  logger.debug("Retrieving parameters from event")
  format = event['pathParameters']['format']
  msg_uuid = event['pathParameters']['msg_uuid']
  
  if format == "original":
    key = "raw/hl7v2/{}.txt".format(msg_uuid) 
  elif format == "er7":
    # Change this to backward conversion from the cleansed json
    key = "raw/hl7v2/{}.txt".format(msg_uuid) 
  elif format == "json":
    key = "staging/hl7v2/{}.json".format(msg_uuid)
  
  response = s3.get_object(Bucket=bucket, Key=key)
  msg_er7 = response["Body"].read().decode("utf-8")
  
  encoding = 'utf-8'
  msg_base64 = encode_to_base64(msg_er7, encoding)
  
  return {
    'statusCode': 200,
    'body': msg_base64
  }
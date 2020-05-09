import boto3, logging, os, json
import uuid
import base64

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def decode_from_base64(encoded_message, encoding):
  base64_bytes = encoded_message.encode(encoding)
  message_bytes = base64.b64decode(base64_bytes)
  return message_bytes.decode(encoding)

def lambda_handler(event, context):
  logger.info("Start")
  s3 = boto3.client('s3')
  bucket = os.environ['data_lake_bucket']
  logger.debug(event)
  
  logger.debug("Extracting data")
  body = json.loads(event["body"])
  msg_b64 =body['msg']
  encoding = body['encoding']
  
  logger.info("Decoding from Base64")
  msg_raw = decode_from_base64 (msg_b64, encoding)
  
  key = "raw/hl7v2/{}.txt".format(str(uuid.uuid4()))
  
  metadata = {}

  try: 
    metadata['seg-term'] = json.dumps(body['seg-term']) # Amazon S3 stores user-defined metadata keys in lowercase
  except Exception as e:
    errMsg = str(e)
    logger.warn(e)
    
  logger.info(metadata)
  
  logger.info("Writing original message")
  s3.put_object(
    Bucket=bucket,
    Key=key,
    Body=msg_raw,
    ContentType= "text/plain; charset=utf-8",
    Metadata=metadata
  )
  
  return {
    'statusCode': 200,
    'body': json.dumps("Message added to raw zone")
  }
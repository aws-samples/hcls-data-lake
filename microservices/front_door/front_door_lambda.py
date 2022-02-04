import boto3, json, os, logging, base64
import hashlib
from boto3.dynamodb.conditions import Key, Attr

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize clients outside of the main function to reuse between calls
sns = boto3.client('sns')
table = boto3.resource('dynamodb').Table(os.environ['table'])

def lambda_handler(event, context):
  # Extract data from the event  
  idToken = event['headers']['authorization']
  b64_msg = json.loads(event["body"])['msg'] 
  msg = __decode_from_base64 (b64_msg, 'utf-8')
  owner = event['requestContext']['authorizer']['jwt']['claims'].get('custom:write')

  # Verify authZ
  if owner == None:
    logger.warn("Unauthorized write attempt rejected")
    return __get_response(403, "Insufficient privileges to write")
  logger.debug("Owner: "+owner)
  
  # Check hash against unique 
  msg_hash = hashlib.sha256(msg.encode()).hexdigest()
  count = table.query(KeyConditionExpression=Key('message_hash').eq(msg_hash))['Count']
    
  if count > 0:
    logger.warn("Duplicate message ignored")
    return __get_response(400, "Rejected due to being a duplicate")

  # Publish to pub-sub-hub
  sns.publish(
    TopicArn=os.environ['topic'],
    Message=msg,
    MessageAttributes={
      'event': {
        'DataType': 'String',
        'StringValue': 'ingested',
      },
      'protocol': {
        'DataType': 'String',
        'StringValue': 'hl7v2',
      },
      'format': {
        'DataType': 'String',
        'StringValue': 'er7',
      },
      'source': {
        'DataType': 'String',
        'StringValue': owner,
      }
    }
  )
  logger.info("Published to SNS topic")
  
  # Update DynamoDB received message table
  table.put_item(
    Item={
      'message_hash': msg_hash
    }
  )
  logger.debug("Message hash written to DynamoDB table")

  return __get_response(201, 'Message ingested')
  
def __get_response(code, description):
  return {
    'statusCode': code, 
    "body": json.dumps({
      "status": description
    })
  }

def __decode_from_base64(encoded_message, encoding):
  base64_bytes = encoded_message.encode(encoding)
  message_bytes = base64.b64decode(base64_bytes)
  return message_bytes.decode(encoding)
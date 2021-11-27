import boto3, json, os, logging, base64, hashlib
from botocore.exceptions import ClientError
from boto3.dynamodb.conditions import Key, Attr

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize clients outside of the main function to reuse between calls
sns = boto3.client('sns')
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(os.environ['table'])
cognito_identity = boto3.client('cognito-identity')
sf = boto3.client('stepfunctions')

def lambda_handler(event, context):
  idToken = event['headers']['authorization']
  claims = event['requestContext']['authorizer']['jwt']['claims']
  source = claims.get('custom:write','')
  
  if len(source) == 0:
    logger.warn("Unauthorized write attempt rejected")
    return __get_response("", 403, "Insufficient privileges to write")
    
  logger.debug("Source: "+source) 

  # Verify the payload is unique through the SHA256[:12] of B64 message (mId)
  logger.debug("Checking that message is unique")
  body = json.loads(event["body"]) # Body is a JSON payload passed in
  msg = body['msg']
  msg_hash = hashlib.sha256(msg.encode()).hexdigest()[:12]
  logger.debug("Message hash: "+msg_hash)

  count = table.query(
    KeyConditionExpression=Key('source').eq(source) & Key('message_id').eq(msg_hash)
  )['Count']
    
  if count > 0:
    logger.warn("Duplicate payload rejected")
    return __get_response(msg_hash, 400, "Rejected due to being a duplicate")
    
  logger.debug("Message {} is unique".format(msg_hash))

  # Invoke our parser
  response = sf.start_sync_execution(
    stateMachineArn=os.environ['state_machine'],
    input= json.dumps({'Message':msg})
  )
  status = response['status']
  logger.info(response)
  
  if status == 'SUCCEEDED':
    state = "parsed"
    json_msg = json.loads(response['output'])['json']
    logger.info("JSON: {}".format(json_msg))
  else:
    state = "error"
    logger.warn(json.loads(response['cause'])['errorMessage'])

  # Store the message (after parsing attempt since we want that status on the tags)
  key = "source={}/protocol=hl7v2/format=er7/zone=ingest/{}.txt".format(source, msg_hash)
  tags = 'source={}&state={}'.format(source, state)
  __store_message(idToken, msg, key, tags, msg_hash, source)
  logger.info("Message written to bucket '{}' with key '{}'".format(os.environ['bucket_name'], key))
  
  if status == 'SUCCEEDED':
    __publish_to_topic(json.dumps(json_msg), 'json', state, key)
    return __get_response(msg_hash, 201, 'Message added and parsed')
  else:
    __publish_to_topic(msg, 'unknown', state, key)
    return __get_response(msg_hash, 400, 'Message added, but could not be parsed')
  logger.info("Published to SNS topic")
  
def __get_response(msgId, code, description):
  return {
    'statusCode': code, 
    "body": json.dumps({
      "messageId":msgId,
      "status": description
    })
  }

def __get_credentials(userPoolId, identityPoolId, cognitoEndpoint, idToken):
  # Get the identity pool ID of the user
  idId = cognito_identity.get_id(
    IdentityPoolId=identityPoolId,
    Logins={
        cognitoEndpoint+"/"+userPoolId: idToken
    }
  )['IdentityId']

  # Get credentials
  response = cognito_identity.get_credentials_for_identity(
    IdentityId=idId,
    Logins={
        cognitoEndpoint+"/"+userPoolId: idToken
    }
  )
  return (response['Credentials'])

def __publish_to_topic(msg, format, state, key):
  sns.publish(
    TopicArn=os.environ['topic'],
    Message=msg,
    MessageAttributes={
      'protocol': {
        'DataType': 'String',
        'StringValue': 'hl7v2',
      },
      'format': {
        'DataType': 'String',
        'StringValue': format,
      },
      'state': {
        'DataType': 'String',
        'StringValue': state,
      },
      'ingest_bucket': {
        'DataType': 'String',
        'StringValue': os.environ['bucket_name'],
      },
      'ingest_key': {
        'DataType': 'String',
        'StringValue': key,
      }
    }
  )

def __store_message(idToken, msg, key, tags, msg_hash, source):
  logger.debug("Getting user credentials")
  credentials = __get_credentials(
    os.environ['user_pool_id'], 
    os.environ['identity_pool_id'], 
    os.environ['cognito_endpoint'], 
    idToken
  )
  
  client = __get_client('s3', credentials) # Client with user credentials
  
  logger.debug("Putting in the bucket")
  client.put_object(
    Bucket=os.environ['bucket_name'],
    Key=key,
    Body=msg,
    ContentType="text/plain; charset=utf-8",
    Tagging=tags
  )
  
   # Update DynamoDB message table
  logger.debug("Writing to our DynamoDB table")
  table.put_item(
    Item={
      'source': source,
      'message_id': msg_hash,
      'bucket': os.environ['bucket_name'],
      'key': key
    }
  )

def __get_client(service, credentials):
  client = boto3.client(
    service,
    aws_access_key_id=credentials['AccessKeyId'],
    aws_secret_access_key=credentials['SecretKey'],
    aws_session_token=credentials['SessionToken']
  )
  return client
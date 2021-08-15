import boto3, json, os, logging, base64, hashlib
from botocore.exceptions import ClientError
from boto3.dynamodb.conditions import Key, Attr

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def decode_from_base64(encoded_message, encoding):
  base64_bytes = encoded_message.encode(encoding)
  message_bytes = base64.b64decode(base64_bytes)
  return message_bytes.decode(encoding)

def get_credentials(userPoolId, identityPoolId, cognitoEndpoint, idToken):
  client = boto3.client('cognito-identity')

  # Get the identity pool ID of the user
  cognitoId = client.get_id(
    IdentityPoolId=identityPoolId,
    Logins={
        cognitoEndpoint+"/"+userPoolId: idToken
    }
  )['IdentityId']

  # Get credentials
  response = client.get_credentials_for_identity(
    IdentityId=cognitoId,
    Logins={
        cognitoEndpoint+"/"+userPoolId: idToken
    }
  )
  return (response['Credentials'])

def get_client(service, credentials):
  client = boto3.client(
    service,
    aws_access_key_id=credentials['AccessKeyId'],
    aws_secret_access_key=credentials['SecretKey'],
    aws_session_token=credentials['SessionToken']
  )
  return client

def lambda_handler(event, context):
  # Verify user has write permission
  claims = event['requestContext']['authorizer']['jwt']['claims']
  source = claims.get('custom:write','')
  
  if len(source) == 0:
    return {
      'statusCode': 403,
      "body": json.dumps({
        "status": "Insufficient privilages to write"
      })
    }
  logger.info("Source: "+source) 

  # Verify the payload is unique through the SHA256[:12] of B64 message (mId)
  logger.info("Checking that message is unique")
  body = json.loads(event["body"]) # Body is a JSON payload passed in
  msg_b64 = body['msg']
  msg_hash = hashlib.sha256(msg_b64.encode()).hexdigest()[:12]
  logger.debug("Message hash: "+msg_hash)

  dynamodb = boto3.resource('dynamodb')
  table = dynamodb.Table(os.environ['table'])
  count = table.query(
    KeyConditionExpression=Key('source').eq(source) & Key('message_id').eq(msg_hash)
  )['Count']
    
  if count > 0:
    return {
      'statusCode': 400,
      'body': json.dumps({
        "status": "Payload rejected due to being a duplicate"
      })
    }
  logger.info("Message "+msg_hash +" is unique")
  
  # Decode the B64 message to UTF-8
  logger.info("Decoding from Base64")
  msg_raw = decode_from_base64 (msg_b64, 'utf-8')
  
  # Get the principal credentials
  idToken = event['headers']['authorization']
  cognito_endpoint = os.environ['cognito_endpoint']
  user_pool_id = os.environ['user_pool_id']
  identity_pool_id = os.environ['identity_pool_id']
  
  credentials = get_credentials(user_pool_id, identity_pool_id, cognito_endpoint, idToken)

  # Write message to S3
  key="source="+source+"/format=hl7v2_er7/zone=ingest/"+msg_hash+".txt"
  bucket_name = os.environ['bucket_name']
  state="new"
  tags = 'source={}&state={}'.format(source, state)
  
  client = get_client('s3', credentials)

  client.put_object(
    Bucket=bucket_name,
    Key=key,
    Body=msg_raw,
    ContentType="text/plain; charset=utf-8",
    Tagging=tags
  )
  logger.info("Message written to bucket {}, key {}".format(bucket_name, key))
  
  # Update DynamoDB message table
  table.put_item(
    Item={
      'source': source,
      'message_id': msg_hash,
      'bucket': bucket_name,
      'key': key
    }
  )
  logger.info("Message table updated")
  
  # Notify via SNS
  sns = boto3.client('sns')
  sns.publish(
    TopicArn=os.environ['topic'],
    Message=msg_raw,
    Subject='string',
    MessageAttributes={
      'format': {
        'DataType': 'String',
        'StringValue': 'er7',
      },
      'state': {
        'DataType': 'String',
        'StringValue': state,
      },
      'key': {
        'DataType': 'String',
        'StringValue': key,
      }
    }
  )
  logger.info("Published to SNS topic")
  
  return {
    'statusCode': 200,
    'body': json.dumps({
      "status": 'Message added with ID {}'.format(msg_hash)
    })
  }
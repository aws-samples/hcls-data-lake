import json
import hl7apy
from hl7apy import parser
import logging
import boto3
from boto3.dynamodb.conditions import Key, Attr
import uuid
import time
import base64
import os

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Recursively builds our data structure
def add_child_element(parent_data, child_element):
  logger.debug("Working on element: " +str(child_element))

  # Throw exception if this element does not exist in the version being parsed
  if child_element.name is None:
    raise Exception("{} with value {} not found in this version of HL7".format(
      type(child_element).__name__, child_element.value))
  
  # Use the short name
  #c_name = child_element.name if child_element.long_name is None else child_element.long_name
  c_name = child_element.name

  # Add element name (key) and value directly if it's a leaf type and then return
  if child_element.reference[0] == "leaf":
    logger.debug(type(child_element.value)) 
    if isinstance(child_element.value, str):
      parent_data[c_name] = child_element.value
    elif isinstance(child_element.value, hl7apy.base_datatypes.ST):
      # Needed because a value of two double quotes ("") seems to throw things off
      parent_data[c_name] = child_element.value.value
    return

  # Since it is not a key-value leaf, it's going to be a dictionary
  c_data = {}
  
  # Check the max occurances: if it's unique then the child dictionary can be added directly
  if child_element.parent.repetitions[child_element.name][1] == 1:
    parent_data[c_name] = c_data

  # If it can repeat then the child needs to be in a list
  else:
    # Create a new list if we haven't already got one
    if c_name not in parent_data: parent_data[c_name] = []
    
    parent_data[c_name].append(c_data)

  # Add the next generation
  for gc in child_element.children: 
    add_child_element(c_data, gc)

def decode_from_base64(encoded_message, encoding):
  base64_bytes = encoded_message.encode(encoding)
  message_bytes = base64.b64decode(base64_bytes)
  return message_bytes.decode(encoding)

# This can be made more robust with some regex
def fix_segment_terminators(message, segment_terminators):
  for st in segment_terminators:
    message = message.replace(st, "\r")
  return message

def get_pid_component_value(field, component):
  # Check if exists and not blank
  if field.get(component) != None and field[component]: return str(field[component])
  else: return ''
  
# Basic attempt at getting patient ID's
def get_pid_codes(msg):
  codes = []
  try:
    pid = msg["PID"]["PID_2"] # External ID (older versions of HL7 V2)
    
    # ASSIGNING_AUTHORITY # IDENTIFIER_TYPE_CODE # ID value
    codes.append('#'.join([
      get_pid_component_value(pid,"CX_4"),
      get_pid_component_value(pid,"CX_5"),
      get_pid_component_value(pid,"CX_1")
    ]))
  except Exception as e: 
    logger.debug(str(e))
  
  try:
    pids = msg["PID"]["PID_3"] # List of PIDs

    for pid in pids:
      # ASSIGNING_AUTHORITY # IDENTIFIER_TYPE_CODE # ID value
      codes.append('#'.join([
        get_pid_component_value(pid,"CX_4"),
        get_pid_component_value(pid,"CX_5"),
        get_pid_component_value(pid,"CX_1")
      ]))
  except Exception as e: 
    logger.debug(str(e))

  return codes

# Link our pids to a global PID
def get_global_id(pids):
  dynamodb = boto3.resource('dynamodb')
  table = dynamodb.Table(os.environ['patient_mapping_table'])
  g_id = None
  no_global = []
  
  for pid in pids:
    response = table.query(
      KeyConditionExpression=Key('local_id').eq(pid),
      IndexName='local_index'
    )
    try:
      g_id = response['Items'][0]['uuid'] # If it is there we should only have one
    except:
      no_global.append(pid)
  
  # Create if we didn't find one
  if g_id is None: g_id = str(uuid.uuid4())
  
  # Update any local ids that weren't associated to the global
  for pid in no_global:
    response = table.put_item(
      Item={
        'uuid': g_id,
        'local_id': pid
      }
    )
  return g_id

def lambda_handler(event, context):
  logger.info("Start")
  s3 = boto3.client('s3')
  dynamodb = boto3.resource('dynamodb')
  bucket = os.environ['data_lake_bucket']
  logger.info(event)
  
  # ----------------------------------- Parse to ER7 object
  try: 
    body = json.loads(event["body"])
    message = decode_from_base64(body['msg'], body['encoding'])

    # Replace segment terminators if provided
    try: message = fix_segment_terminators(message, body['segTerm'])
    except: pass
    logger.info("Message: " + message)
    
    er7_msg = parser.parse_message(message)
  except Exception as e:
    errMsg = str(e)
    logger.error(e)
    return {
      'statusCode': 400,
      'body': json.dumps("Could not convert to ER7 object: "+errMsg)
    }

  msg_id = er7_msg.children[0].MESSAGE_CONTROL_ID.value
  event = er7_msg.children[0].MSH_9.value
  version = er7_msg.children[0].MSH_12.value
  logger.info("Parsed message {} to ER7".format(msg_id))
    
  # ----------------------------------- Convert to JSON
  json_msg = {}
  try:
    for c in er7_msg.children:
      add_child_element(json_msg, c)
  except KeyError as e:
    errMsg = "Our library does not support {} events for HL7 version {}, message {} not written".format(
      event, version, msg_id)
    logger.error(errMsg)
    
    error_key = "error/hl7v2/{}_{}_{}.txt".format(version,event,msg_id)
    
    s3.put_object(
      Bucket=bucket,
      Key=error_key,
      Body=message
    )
    
    table = dynamodb.Table(os.environ['error_table'])
    table.put_item(
      Item={
        'type': "HL7_"+event+"_"+version,
        's3_key': error_key,
        'provided_id': msg_id
      }
    )
    
    return {
      'statusCode': 400,
      'body': json.dumps(errMsg)
    }
    
  logger.info("ER7 converted to JSON")  

  # ------------------------------------------------- Get our catalog data
  logger.debug("Getting PID codes")
  pids = get_pid_codes(json_msg)
  for pid in pids:
    logger.info("Found local PID: "+pid)

  logger.debug("Get our patient global ID") 
  global_id = get_global_id(pids)
  logger.info("Global ID: " + global_id)
    
  logger.info("Setting the keys")
  timestamp = str(json_msg["MSH"]["MSH_7"]["TS_1"])
  sort_key = "HL7_"+er7_msg.name +"_"+timestamp #msg_id
  bucket_key_suffix = er7_msg.name +"_"+timestamp + "_" +msg_id
  raw_key = "raw/hl7v2/{}.txt".format(bucket_key_suffix)
  staging_key = "staging/hl7v2/{}.json".format(bucket_key_suffix)
    
  #------------------------------------------------- Write to S3 and DynamoDB
  logger.info("Writing original message to raw")
  s3.put_object(
    Bucket=bucket,
    Key=raw_key,
    Body=message
  )

  logger.info("Writing JSON message to staging")
  s3.put_object(
    Bucket=bucket,
    Key=staging_key,
    Body=json.dumps(json_msg)
  )
    
  logger.info("Tagging the data lineage")
  s3.put_object_tagging(
    Bucket=bucket,
    Key=staging_key,
    Tagging={
      'TagSet': [{'Key': 'data_src','Value': raw_key}]
    }
  )
  
  logger.info("Updating the data catalog")
  table = dynamodb.Table(os.environ['message_table'])
  table.put_item(
    Item={
      'patient_uuid': global_id,
      "code": sort_key,
      's3_key': staging_key,
      'provided_id': msg_id
    }
  )
  return {
    'statusCode': 200,
    'body': json.dumps("Message {} successfully written".format(msg_id))
  }
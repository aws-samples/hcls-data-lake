import json
import hl7apy
from hl7apy import parser
import logging
import boto3
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
  
  # Use the long name if present, default (short) name otherwise
  c_name = child_element.name if child_element.long_name is None else child_element.long_name

  # Add element name (key) and value directly if it's a leaf type and then return
  if child_element.reference[0] == "leaf":
    print(type(child_element.value)) 
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

def fix_segment_terminators(message, segment_terminators):
  for st in segment_terminators:
    message = message.replace(st, "\r")
  return message

def lambda_handler(event, context):
  logger.info("Start")
  s3 = boto3.client('s3')
  bucket = os.environ['data_lake_bucket']
  
  try: 
    logger.debug(event)
    
    body = json.loads(event["body"])
    message = decode_from_base64(body['msg'], body['encoding'])
    
    logger.info("Writing the original message to our bucket")
    
    event_id = json.dumps(event["requestContext"]["authorizer"]["jwt"]["claims"]["event_id"]).replace('"','')
    
    # Replace segment terminators if provided
    try: message = fix_segment_terminators(message, body['segTerm'])
    except: pass
    logger.info("Message: " + message)
    
    er7_msg = parser.parse_message(message)
    m_id = er7_msg.children[0].MESSAGE_CONTROL_ID.value
    logger.info("Parsed message {} to ER7".format(m_id))
    
    json_msg = {}
    for c in er7_msg.children:
      add_child_element(json_msg, c)
    logger.info("Record built")  

    logger.info("Writing original message to raw")
    s3.put_object(
      Bucket=bucket,
      Key="raw/hl7v2/{}.txt".format(event_id),
      Body=message
    )

    logger.info("Writing formatted message to staging")
    s3.put_object(
      Bucket=bucket,
      Key="staging/hl7v2/{}_{}.json".format(time.time(), m_id),
      Body=json.dumps(json_msg)
    )
    
    return {
      'statusCode': 200,
      'body': json.dumps("Message {} successfully written".format(m_id))
    }
    
  except Exception as e:
    errMsg = str(e)
    logger.error(errMsg)
    
    s3.put_object(
      Bucket=bucket,
      Key="error/hl7v2/{}.txt".format(event_id),
      Body="*** " + errMsg + " ***" +'\r'+message
    )
    
    return {
      'statusCode': 400,
      'body': json.dumps(errMsg)
    }
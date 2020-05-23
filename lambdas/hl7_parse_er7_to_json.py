import json
import hl7apy
from hl7apy import parser
import logging
import boto3
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

def parse_er7_object_to_json(er7_obj):
  json_msg = {}

  msg_id = er7_obj.children[0].MESSAGE_CONTROL_ID.value
  event = er7_obj.children[0].MSH_9.value
  version = er7_obj.children[0].MSH_12.value

  try:
    for c in er7_obj.children:
      add_child_element(json_msg, c)
  except KeyError as e:
    errMsg = "We cannot infer structure for {} events in HL7 version {}; message {} not written".format(event, version, msg_id)
    logger.error(errMsg)
    raise

  return json_msg

def lambda_handler(event, context):
  logger.info("Start")
  logger.info(event)

  # Obtain ER7 object
  hl7_er7 = parser.parse_message(event['er7'])

  # Parse to JSON
  hl7_json = parse_er7_object_to_json(hl7_er7)
  logger.info(json.dumps(hl7_json))

  # Write to staging
  s3 = boto3.client('s3')
  bucket = os.environ['data_lake_bucket']
  prefix = os.environ['data_lake_prefix']

  raw_key = event['key']
  file_name = raw_key.split("/")[-1]
  dest_key = prefix + file_name.replace(".txt",".json")
  raw_src = "S3://" + event['bucketName'] +"/" + raw_key # Source and destination buckets might not be the same

  logger.info("Writing JSON file to bucket")
  s3.put_object(
    Bucket=bucket,
    Key=dest_key,
    ContentType= "application/json",
    Body=json.dumps(hl7_json)
  )

  logger.info("Tagging the data lineage")
  s3.put_object_tagging(
    Bucket=bucket,
    Key=dest_key,
    Tagging={
      'TagSet': [{'Key': 'data_src','Value': raw_src}]
    }
  )

  # temp test
  payload = {
    'method': 'GET_GID',
    'data': get_local_ids_from_hl7_json(hl7_json)
  }
  boto3.client('lambda').invoke(
    FunctionName=os.environ['PATIENT_MATCHER_API_ARN'] ,
    InvocationType='RequestResponse',
    Payload=json.dumps(payload)
  )


"""
Temp utility methods for testing patient matcher API
"""
def get_local_ids_from_hl7_json(data):
  local_ids = list()
  pid_2 = data['PID'].get('PID_2', None)
  formatted_pid2 = format_local_id_components(pid_2)
  if formatted_pid2 is not None:
    local_ids.append(formatted_pid2)
  pid_3 = data['PID'].get('PID_3', None)
  if pid_3 is not None:
    for pid_3_component in pid_3:
      formatted_pid_3_component = format_local_id_components(pid_3_component)
      if formatted_pid_3_component is not None:
        local_ids.append(formatted_pid_3_component)

  return local_ids


def format_local_id_components(local_id_field):
  result = None
  if local_id_field is not None:
    result = dict()
    logger.info(f'local id: {local_id_field}')
    for key, value in local_id_field.items():
      if isinstance(value, str):
        result[key] = value

  return result

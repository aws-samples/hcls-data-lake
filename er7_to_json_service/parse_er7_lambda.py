import json, logging
import hl7apy
from hl7apy import parser

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(er7, lambda_context):
  logger.info(er7)
  er7_obj = parser.parse_message(er7)
  logger.info(er7_obj)
  
  hl7_json = __parse_er7_object_to_json(er7_obj)
  logger.info(json.dumps(hl7_json))
  
  return hl7_json

def __parse_er7_object_to_json(er7_obj):
  json_msg = {}
  
  try:
    for c in er7_obj.children:
      __add_child_element(json_msg, c)
  except KeyError as e:
    errMsg = "Unable to determine structure, message not written"
    logger.error(errMsg)
    raise

  return json_msg

# Recursively builds our data structure
def __add_child_element(parent_data, child_element):
  logger.debug("Working on element: " +str(child_element))

  # Throw exception if this element does not exist in the version being parsed
  if child_element.name is None:
    raise Exception("{} with value {} not found in this version of HL7".format(
      type(child_element).__name__, child_element.value))
  
  # Use the short name
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
    __add_child_element(c_data, gc)
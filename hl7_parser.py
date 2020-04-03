import json
from hl7apy import parser
import hl7apy
import re
import logging
import boto3
import time

logger = logging.getLogger()
logger.setLevel(logging.INFO)

s3 = boto3.client('s3')

def get_messages_from_input(content):
    # Get rid of blank lines
    content = re.sub(r'^$\n', '', content, flags=re.MULTILINE)

    # HL7 requires that a carriage return be used to seperate segments
    content = content.replace("\r\n", "\r")
    content = content.replace("\n", "\r")

    # File may have multiple messages, split by "MSH"
    chunks = content.split("MSH")
    
    # Put "MSH" back in front of each message
    messages = []
    for m in chunks:
        # Skip blanks
        if len(m) == 0: continue
    
        messages.append("MSH"+m)
    
    return messages   

# Recursively builds our data structure
def add_child_element(parent_data, child_element):
    logger.info("Working on element: " +str(child_element))

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

def lambda_handler(event, context):
    logger.info("Start")
    # retrieve bucket name and file_key from the S3 event
    bucket_name = event['Records'][0]['s3']['bucket']['name']
    file_key = event['Records'][0]['s3']['object']['key']
    logger.info('Reading {} from {}'.format(file_key, bucket_name))

    # get the object
    obj = s3.get_object(Bucket=bucket_name, Key=file_key)

    # get file content
    content = obj['Body'].read().decode("utf-8")
    msgs = get_messages_from_input(content)
    
    logger.info('Found {} messages'.format(len(msgs)))
    
    for msg in msgs:
        m_id = ""
        try:
            logger.debug("Working on message "+ msg)
        
            er7_msg = parser.parse_message(msg)
            m_id = er7_msg.children[0].MESSAGE_CONTROL_ID.value
            
            logger.info("Parsed message {} to ER7".format(m_id))
            
            rec = {}
            for c in er7_msg.children:
                add_child_element(rec, c)
            
            logger.info("Record built, writing to file")
            key = "staging/{}_{}.json".format(time.time(), m_id)
            
            # Do not use indents or linebreaks within a message/record, takes more file space and does not work with JSON-SerDe (used by Athena)
            content = json.dumps(rec)   
        
        except Exception as e:
            errMsg = str(e)
            logger.error(errMsg)
            key = "error/{}_{}.txt".format(time.time(), m_id)
            content="*** " + errMsg + " ***" +'\r'+msg

        response = s3.put_object(
            Bucket=bucket_name,
            Key=key,
            Body=content
        )

    logger.info("Completed parsing")
    
    return {
        'statusCode': 200,
        'body': json.dumps('Job complete')
    }
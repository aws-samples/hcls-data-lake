{"filter":false,"title":"hl7_parser.py","tooltip":"/hl7_parser.py","undoManager":{"mark":16,"position":16,"stack":[[{"start":{"row":0,"column":0},"end":{"row":129,"column":3},"action":"remove","lines":["import json","from hl7apy import parser","import hl7apy","import re","import logging","import boto3","import time","","logger = logging.getLogger()","logger.setLevel(logging.INFO)","","s3 = boto3.client('s3')","","def get_messages_from_input(content):","  # Get rid of blank lines","  content = re.sub(r'^$\\n', '', content, flags=re.MULTILINE)","","  # HL7 requires that a carriage return be used to seperate segments","  content = content.replace(\"\\r\\n\", \"\\r\")","  content = content.replace(\"\\n\", \"\\r\")","","  # File may have multiple messages, split by \"MSH\"","  chunks = content.split(\"MSH\")","  ","  # Put \"MSH\" back in front of each message","  messages = []","  for m in chunks:","    # Skip blanks","    if len(m) == 0: continue","  ","    messages.append(\"MSH\"+m)","  ","  return messages   ","","# Recursively builds our data structure","def add_child_element(parent_data, child_element):","  logger.info(\"Working on element: \" +str(child_element))","","  # Throw exception if this element does not exist in the version being parsed","  if child_element.name is None:","    raise Exception(\"{} with value {} not found in this version of HL7\".format(","      type(child_element).__name__, child_element.value))","  ","  # Use the long name if present, default (short) name otherwise","  c_name = child_element.name if child_element.long_name is None else child_element.long_name","","  # Add element name (key) and value directly if it's a leaf type and then return","  if child_element.reference[0] == \"leaf\":","    print(type(child_element.value)) ","    if isinstance(child_element.value, str):","      parent_data[c_name] = child_element.value","    elif isinstance(child_element.value, hl7apy.base_datatypes.ST):","      # Needed because a value of two double quotes (\"\") seems to throw things off","      parent_data[c_name] = child_element.value.value","    return","","  # Since it is not a key-value leaf, it's going to be a dictionary","  c_data = {}","  ","  # Check the max occurances: if it's unique then the child dictionary can be added directly","  if child_element.parent.repetitions[child_element.name][1] == 1:","    parent_data[c_name] = c_data","  ","  # If it can repeat then the child needs to be in a list","  else:","    # Create a new list if we haven't already got one","    if c_name not in parent_data: parent_data[c_name] = []","    ","    parent_data[c_name].append(c_data)","","  # Add the next generation","  for gc in child_element.children: ","    add_child_element(c_data, gc)","","def lambda_handler(event, context):","  logger.info(\"Start\")","  ","  # retrieve bucket name and file_key from the S3 event","  bucket_name = event['Records'][0]['s3']['bucket']['name']","  file_key = event['Records'][0]['s3']['object']['key']","  logger.info('Reading {} from {}'.format(file_key, bucket_name))","","  # get the object","  obj = s3.get_object(Bucket=bucket_name, Key=file_key)","","  # get file content","  content = obj['Body'].read().decode(\"utf-8\")","  msgs = get_messages_from_input(content)","  ","  logger.info('Found {} messages'.format(len(msgs)))","  ","  for msg in msgs:","    m_id = \"\"","    try:","      logger.debug(\"Working on message \"+ msg)","    ","      er7_msg = parser.parse_message(msg)","      m_id = er7_msg.children[0].MESSAGE_CONTROL_ID.value","      ","      logger.info(\"Parsed message {} to ER7\".format(m_id))","      ","      rec = {}","      for c in er7_msg.children:","        add_child_element(rec, c)","      ","      logger.info(\"Record built, writing to file\")","      key = \"staging/{}_{}.json\".format(time.time(), m_id)","      ","      # Do not use indents or linebreaks within a message/record; ","      # takes more file space and does not work with JSON-SerDe (used by Athena)","      content = json.dumps(rec)   ","    ","    except Exception as e:","      errMsg = str(e)","      logger.error(errMsg)","      key = \"error/{}_{}.txt\".format(time.time(), m_id)","      content=\"*** \" + errMsg + \" ***\" +'\\r'+msg","","    response = s3.put_object(","      Bucket=bucket_name,","      Key=key,","      Body=content","    )","","  logger.info(\"Completed parsing\")","  ","  return {","    'statusCode': 200,","    'body': json.dumps('Job complete')","  }"],"id":2},{"start":{"row":0,"column":0},"end":{"row":124,"column":36},"action":"insert","lines":["import json","import hl7apy","from hl7apy import parser","import re","import logging","import boto3","import time","import base64","import os","","logger = logging.getLogger()","logger.setLevel(logging.INFO)","","# Recursively builds our data structure","def add_child_element(parent_data, child_element):","  logger.debug(\"Working on element: \" +str(child_element))","","  # Throw exception if this element does not exist in the version being parsed","  if child_element.name is None:","    raise Exception(\"{} with value {} not found in this version of HL7\".format(","      type(child_element).__name__, child_element.value))","  ","  # Use the long name if present, default (short) name otherwise","  c_name = child_element.name if child_element.long_name is None else child_element.long_name","","  # Add element name (key) and value directly if it's a leaf type and then return","  if child_element.reference[0] == \"leaf\":","    print(type(child_element.value)) ","    if isinstance(child_element.value, str):","      parent_data[c_name] = child_element.value","    elif isinstance(child_element.value, hl7apy.base_datatypes.ST):","      # Needed because a value of two double quotes (\"\") seems to throw things off","      parent_data[c_name] = child_element.value.value","    return","","  # Since it is not a key-value leaf, it's going to be a dictionary","  c_data = {}","  ","  # Check the max occurances: if it's unique then the child dictionary can be added directly","  if child_element.parent.repetitions[child_element.name][1] == 1:","    parent_data[c_name] = c_data","  ","  # If it can repeat then the child needs to be in a list","  else:","    # Create a new list if we haven't already got one","    if c_name not in parent_data: parent_data[c_name] = []","    ","    parent_data[c_name].append(c_data)","","  # Add the next generation","  for gc in child_element.children: ","    add_child_element(c_data, gc)","","def decode_from_base64(encoded_message, encoding):","  base64_bytes = encoded_message.encode(encoding)","  message_bytes = base64.b64decode(base64_bytes)","  return message_bytes.decode(encoding)","","def fix_segment_terminators(message, segment_terminators):","  for st in segment_terminators:","    message = message.replace(st, \"\\r\")","  return message","","def lambda_handler(event, context):","  logger.info(\"Start\")","  s3 = boto3.client('s3')","  bucket = os.environ['data_lake_bucket']","  ","  try: ","    logger.debug(event)","    ","    body = json.loads(event[\"body\"])","    message = decode_from_base64(body['msg'], body['encoding'])","    ","    logger.info(\"Writing the original message to our bucket\")","    ","    event_id = json.dumps(event[\"requestContext\"][\"authorizer\"][\"jwt\"][\"claims\"][\"event_id\"]).replace('\"','')","    key = \"raw/hl7v2/{}.txt\".format(event_id)","    response = s3.put_object(","      Bucket=bucket,","      Key=key,","      Body=message","    )","    ","    message = fix_segment_terminators(message, body['segTerm'])","    logger.info(\"Message: \"+message)","    ","    er7_msg = parser.parse_message(message)","    m_id = er7_msg.children[0].MESSAGE_CONTROL_ID.value","    logger.info(\"Parsed message {} to ER7\".format(m_id))","    ","    json_msg = {}","    for c in er7_msg.children:","      add_child_element(json_msg, c)","      ","    # Do not use indents or linebreaks within a message/record; ","    # takes more file space and does not work with JSON-SerDe (used by Athena)","    content = json.dumps(json_msg)","    logger.info(\"Record built\")","    ","    key = \"staging/hl7v2/{}_{}.json\".format(time.time(), m_id)","","    return {","      'statusCode': 200,","      'body': json.dumps(\"Message {} successfully written\".format(m_id))","    }","    ","  except Exception as e:","    errMsg = str(e)","    logger.error(errMsg)","    key = \"error/hl7v2/{}_{}.txt\".format(time.time(), m_id)","    content=\"*** \" + errMsg + \" ***\" +'\\r'+msg","    ","    return {","      'statusCode': 400,","      'body': json.dumps(errMsg)","    }","","  finally:","    response = s3.put_object(","      Bucket=bucket,","      Key=key,","      Body=content","    )","    logger.info(\"Completed parsing\")"]}],[{"start":{"row":0,"column":0},"end":{"row":124,"column":36},"action":"remove","lines":["import json","import hl7apy","from hl7apy import parser","import re","import logging","import boto3","import time","import base64","import os","","logger = logging.getLogger()","logger.setLevel(logging.INFO)","","# Recursively builds our data structure","def add_child_element(parent_data, child_element):","  logger.debug(\"Working on element: \" +str(child_element))","","  # Throw exception if this element does not exist in the version being parsed","  if child_element.name is None:","    raise Exception(\"{} with value {} not found in this version of HL7\".format(","      type(child_element).__name__, child_element.value))","  ","  # Use the long name if present, default (short) name otherwise","  c_name = child_element.name if child_element.long_name is None else child_element.long_name","","  # Add element name (key) and value directly if it's a leaf type and then return","  if child_element.reference[0] == \"leaf\":","    print(type(child_element.value)) ","    if isinstance(child_element.value, str):","      parent_data[c_name] = child_element.value","    elif isinstance(child_element.value, hl7apy.base_datatypes.ST):","      # Needed because a value of two double quotes (\"\") seems to throw things off","      parent_data[c_name] = child_element.value.value","    return","","  # Since it is not a key-value leaf, it's going to be a dictionary","  c_data = {}","  ","  # Check the max occurances: if it's unique then the child dictionary can be added directly","  if child_element.parent.repetitions[child_element.name][1] == 1:","    parent_data[c_name] = c_data","  ","  # If it can repeat then the child needs to be in a list","  else:","    # Create a new list if we haven't already got one","    if c_name not in parent_data: parent_data[c_name] = []","    ","    parent_data[c_name].append(c_data)","","  # Add the next generation","  for gc in child_element.children: ","    add_child_element(c_data, gc)","","def decode_from_base64(encoded_message, encoding):","  base64_bytes = encoded_message.encode(encoding)","  message_bytes = base64.b64decode(base64_bytes)","  return message_bytes.decode(encoding)","","def fix_segment_terminators(message, segment_terminators):","  for st in segment_terminators:","    message = message.replace(st, \"\\r\")","  return message","","def lambda_handler(event, context):","  logger.info(\"Start\")","  s3 = boto3.client('s3')","  bucket = os.environ['data_lake_bucket']","  ","  try: ","    logger.debug(event)","    ","    body = json.loads(event[\"body\"])","    message = decode_from_base64(body['msg'], body['encoding'])","    ","    logger.info(\"Writing the original message to our bucket\")","    ","    event_id = json.dumps(event[\"requestContext\"][\"authorizer\"][\"jwt\"][\"claims\"][\"event_id\"]).replace('\"','')","    key = \"raw/hl7v2/{}.txt\".format(event_id)","    response = s3.put_object(","      Bucket=bucket,","      Key=key,","      Body=message","    )","    ","    message = fix_segment_terminators(message, body['segTerm'])","    logger.info(\"Message: \"+message)","    ","    er7_msg = parser.parse_message(message)","    m_id = er7_msg.children[0].MESSAGE_CONTROL_ID.value","    logger.info(\"Parsed message {} to ER7\".format(m_id))","    ","    json_msg = {}","    for c in er7_msg.children:","      add_child_element(json_msg, c)","      ","    # Do not use indents or linebreaks within a message/record; ","    # takes more file space and does not work with JSON-SerDe (used by Athena)","    content = json.dumps(json_msg)","    logger.info(\"Record built\")","    ","    key = \"staging/hl7v2/{}_{}.json\".format(time.time(), m_id)","","    return {","      'statusCode': 200,","      'body': json.dumps(\"Message {} successfully written\".format(m_id))","    }","    ","  except Exception as e:","    errMsg = str(e)","    logger.error(errMsg)","    key = \"error/hl7v2/{}_{}.txt\".format(time.time(), m_id)","    content=\"*** \" + errMsg + \" ***\" +'\\r'+msg","    ","    return {","      'statusCode': 400,","      'body': json.dumps(errMsg)","    }","","  finally:","    response = s3.put_object(","      Bucket=bucket,","      Key=key,","      Body=content","    )","    logger.info(\"Completed parsing\")"],"id":3},{"start":{"row":0,"column":0},"end":{"row":122,"column":5},"action":"insert","lines":["import json","import hl7apy","from hl7apy import parser","import re","import logging","import boto3","import time","import base64","import os","","logger = logging.getLogger()","logger.setLevel(logging.INFO)","","# Recursively builds our data structure","def add_child_element(parent_data, child_element):","  logger.debug(\"Working on element: \" +str(child_element))","","  # Throw exception if this element does not exist in the version being parsed","  if child_element.name is None:","    raise Exception(\"{} with value {} not found in this version of HL7\".format(","      type(child_element).__name__, child_element.value))","  ","  # Use the long name if present, default (short) name otherwise","  c_name = child_element.name if child_element.long_name is None else child_element.long_name","","  # Add element name (key) and value directly if it's a leaf type and then return","  if child_element.reference[0] == \"leaf\":","    print(type(child_element.value)) ","    if isinstance(child_element.value, str):","      parent_data[c_name] = child_element.value","    elif isinstance(child_element.value, hl7apy.base_datatypes.ST):","      # Needed because a value of two double quotes (\"\") seems to throw things off","      parent_data[c_name] = child_element.value.value","    return","","  # Since it is not a key-value leaf, it's going to be a dictionary","  c_data = {}","  ","  # Check the max occurances: if it's unique then the child dictionary can be added directly","  if child_element.parent.repetitions[child_element.name][1] == 1:","    parent_data[c_name] = c_data","  ","  # If it can repeat then the child needs to be in a list","  else:","    # Create a new list if we haven't already got one","    if c_name not in parent_data: parent_data[c_name] = []","    ","    parent_data[c_name].append(c_data)","","  # Add the next generation","  for gc in child_element.children: ","    add_child_element(c_data, gc)","","def decode_from_base64(encoded_message, encoding):","  base64_bytes = encoded_message.encode(encoding)","  message_bytes = base64.b64decode(base64_bytes)","  return message_bytes.decode(encoding)","","def fix_segment_terminators(message, segment_terminators):","  for st in segment_terminators:","    message = message.replace(st, \"\\r\")","  return message","","def lambda_handler(event, context):","  logger.info(\"Start\")","  s3 = boto3.client('s3')","  bucket = os.environ['data_lake_bucket']","  ","  try: ","    logger.debug(event)","    ","    body = json.loads(event[\"body\"])","    message = decode_from_base64(body['msg'], body['encoding'])","    ","    logger.info(\"Writing the original message to our bucket\")","    ","    event_id = json.dumps(event[\"requestContext\"][\"authorizer\"][\"jwt\"][\"claims\"][\"event_id\"]).replace('\"','')","    ","    message = fix_segment_terminators(message, body['segTerm'])","    logger.info(\"Message: \"+message)","    ","    er7_msg = parser.parse_message(message)","    m_id = er7_msg.children[0].MESSAGE_CONTROL_ID.value","    logger.info(\"Parsed message {} to ER7\".format(m_id))","    ","    json_msg = {}","    for c in er7_msg.children:","      add_child_element(json_msg, c)","    logger.info(\"Record built\")  ","","    logger.info(\"Writing original message to raw\")","    s3.put_object(","      Bucket=bucket,","      Key=\"raw/hl7v2/{}.txt\".format(event_id),","      Body=message","    )","","    logger.info(\"Writing formatted message to staging\")","    s3.put_object(","      Bucket=bucket,","      Key=\"staging/hl7v2/{}_{}.json\".format(time.time(), m_id),","      Body=json.dumps(json_msg)","    )","    ","    return {","      'statusCode': 200,","      'body': json.dumps(\"Message {} successfully written\".format(m_id))","    }","    ","  except Exception as e:","    errMsg = str(e)","    logger.error(errMsg)","    ","    s3.put_object(","      Bucket=bucket,","      Key=\"error/hl7v2/{}.txt\".format(event_id)","      Body=\"*** \" + errMsg + \" ***\" +'\\r'+message","    )","    ","    return {","      'statusCode': 400,","      'body': json.dumps(errMsg)","    }"]}],[{"start":{"row":3,"column":0},"end":{"row":3,"column":9},"action":"remove","lines":["import re"],"id":4},{"start":{"row":3,"column":0},"end":{"row":4,"column":0},"action":"remove","lines":["",""]}],[{"start":{"row":114,"column":47},"end":{"row":114,"column":48},"action":"insert","lines":[","],"id":5}],[{"start":{"row":0,"column":0},"end":{"row":121,"column":5},"action":"remove","lines":["import json","import hl7apy","from hl7apy import parser","import logging","import boto3","import time","import base64","import os","","logger = logging.getLogger()","logger.setLevel(logging.INFO)","","# Recursively builds our data structure","def add_child_element(parent_data, child_element):","  logger.debug(\"Working on element: \" +str(child_element))","","  # Throw exception if this element does not exist in the version being parsed","  if child_element.name is None:","    raise Exception(\"{} with value {} not found in this version of HL7\".format(","      type(child_element).__name__, child_element.value))","  ","  # Use the long name if present, default (short) name otherwise","  c_name = child_element.name if child_element.long_name is None else child_element.long_name","","  # Add element name (key) and value directly if it's a leaf type and then return","  if child_element.reference[0] == \"leaf\":","    print(type(child_element.value)) ","    if isinstance(child_element.value, str):","      parent_data[c_name] = child_element.value","    elif isinstance(child_element.value, hl7apy.base_datatypes.ST):","      # Needed because a value of two double quotes (\"\") seems to throw things off","      parent_data[c_name] = child_element.value.value","    return","","  # Since it is not a key-value leaf, it's going to be a dictionary","  c_data = {}","  ","  # Check the max occurances: if it's unique then the child dictionary can be added directly","  if child_element.parent.repetitions[child_element.name][1] == 1:","    parent_data[c_name] = c_data","  ","  # If it can repeat then the child needs to be in a list","  else:","    # Create a new list if we haven't already got one","    if c_name not in parent_data: parent_data[c_name] = []","    ","    parent_data[c_name].append(c_data)","","  # Add the next generation","  for gc in child_element.children: ","    add_child_element(c_data, gc)","","def decode_from_base64(encoded_message, encoding):","  base64_bytes = encoded_message.encode(encoding)","  message_bytes = base64.b64decode(base64_bytes)","  return message_bytes.decode(encoding)","","def fix_segment_terminators(message, segment_terminators):","  for st in segment_terminators:","    message = message.replace(st, \"\\r\")","  return message","","def lambda_handler(event, context):","  logger.info(\"Start\")","  s3 = boto3.client('s3')","  bucket = os.environ['data_lake_bucket']","  ","  try: ","    logger.debug(event)","    ","    body = json.loads(event[\"body\"])","    message = decode_from_base64(body['msg'], body['encoding'])","    ","    logger.info(\"Writing the original message to our bucket\")","    ","    event_id = json.dumps(event[\"requestContext\"][\"authorizer\"][\"jwt\"][\"claims\"][\"event_id\"]).replace('\"','')","    ","    message = fix_segment_terminators(message, body['segTerm'])","    logger.info(\"Message: \"+message)","    ","    er7_msg = parser.parse_message(message)","    m_id = er7_msg.children[0].MESSAGE_CONTROL_ID.value","    logger.info(\"Parsed message {} to ER7\".format(m_id))","    ","    json_msg = {}","    for c in er7_msg.children:","      add_child_element(json_msg, c)","    logger.info(\"Record built\")  ","","    logger.info(\"Writing original message to raw\")","    s3.put_object(","      Bucket=bucket,","      Key=\"raw/hl7v2/{}.txt\".format(event_id),","      Body=message","    )","","    logger.info(\"Writing formatted message to staging\")","    s3.put_object(","      Bucket=bucket,","      Key=\"staging/hl7v2/{}_{}.json\".format(time.time(), m_id),","      Body=json.dumps(json_msg)","    )","    ","    return {","      'statusCode': 200,","      'body': json.dumps(\"Message {} successfully written\".format(m_id))","    }","    ","  except Exception as e:","    errMsg = str(e)","    logger.error(errMsg)","    ","    s3.put_object(","      Bucket=bucket,","      Key=\"error/hl7v2/{}.txt\".format(event_id),","      Body=\"*** \" + errMsg + \" ***\" +'\\r'+message","    )","    ","    return {","      'statusCode': 400,","      'body': json.dumps(errMsg)","    }"],"id":6},{"start":{"row":0,"column":0},"end":{"row":123,"column":5},"action":"insert","lines":["import json","import hl7apy","from hl7apy import parser","import logging","import boto3","import time","import base64","import os","","logger = logging.getLogger()","logger.setLevel(logging.INFO)","","# Recursively builds our data structure","def add_child_element(parent_data, child_element):","  logger.debug(\"Working on element: \" +str(child_element))","","  # Throw exception if this element does not exist in the version being parsed","  if child_element.name is None:","    raise Exception(\"{} with value {} not found in this version of HL7\".format(","      type(child_element).__name__, child_element.value))","  ","  # Use the long name if present, default (short) name otherwise","  c_name = child_element.name if child_element.long_name is None else child_element.long_name","","  # Add element name (key) and value directly if it's a leaf type and then return","  if child_element.reference[0] == \"leaf\":","    print(type(child_element.value)) ","    if isinstance(child_element.value, str):","      parent_data[c_name] = child_element.value","    elif isinstance(child_element.value, hl7apy.base_datatypes.ST):","      # Needed because a value of two double quotes (\"\") seems to throw things off","      parent_data[c_name] = child_element.value.value","    return","","  # Since it is not a key-value leaf, it's going to be a dictionary","  c_data = {}","  ","  # Check the max occurances: if it's unique then the child dictionary can be added directly","  if child_element.parent.repetitions[child_element.name][1] == 1:","    parent_data[c_name] = c_data","  ","  # If it can repeat then the child needs to be in a list","  else:","    # Create a new list if we haven't already got one","    if c_name not in parent_data: parent_data[c_name] = []","    ","    parent_data[c_name].append(c_data)","","  # Add the next generation","  for gc in child_element.children: ","    add_child_element(c_data, gc)","","def decode_from_base64(encoded_message, encoding):","  base64_bytes = encoded_message.encode(encoding)","  message_bytes = base64.b64decode(base64_bytes)","  return message_bytes.decode(encoding)","","def fix_segment_terminators(message, segment_terminators):","  for st in segment_terminators:","    message = message.replace(st, \"\\r\")","  return message","","def lambda_handler(event, context):","  logger.info(\"Start\")","  s3 = boto3.client('s3')","  bucket = os.environ['data_lake_bucket']","  ","  try: ","    logger.debug(event)","    ","    body = json.loads(event[\"body\"])","    message = decode_from_base64(body['msg'], body['encoding'])","    ","    logger.info(\"Writing the original message to our bucket\")","    ","    event_id = json.dumps(event[\"requestContext\"][\"authorizer\"][\"jwt\"][\"claims\"][\"event_id\"]).replace('\"','')","    ","    # Replace segment terminators if provided","    try:","      message = fix_segment_terminators(message, body['segTerm'])","    logger.info(\"Message: \"+message)","    ","    er7_msg = parser.parse_message(message)","    m_id = er7_msg.children[0].MESSAGE_CONTROL_ID.value","    logger.info(\"Parsed message {} to ER7\".format(m_id))","    ","    json_msg = {}","    for c in er7_msg.children:","      add_child_element(json_msg, c)","    logger.info(\"Record built\")  ","","    logger.info(\"Writing original message to raw\")","    s3.put_object(","      Bucket=bucket,","      Key=\"raw/hl7v2/{}.txt\".format(event_id),","      Body=message","    )","","    logger.info(\"Writing formatted message to staging\")","    s3.put_object(","      Bucket=bucket,","      Key=\"staging/hl7v2/{}_{}.json\".format(time.time(), m_id),","      Body=json.dumps(json_msg)","    )","    ","    return {","      'statusCode': 200,","      'body': json.dumps(\"Message {} successfully written\".format(m_id))","    }","    ","  except Exception as e:","    errMsg = str(e)","    logger.error(errMsg)","    ","    s3.put_object(","      Bucket=bucket,","      Key=\"error/hl7v2/{}.txt\".format(event_id),","      Body=\"*** \" + errMsg + \" ***\" +'\\r'+message","    )","    ","    return {","      'statusCode': 400,","      'body': json.dumps(errMsg)","    }"]}],[{"start":{"row":80,"column":27},"end":{"row":80,"column":28},"action":"insert","lines":[" "],"id":7}],[{"start":{"row":80,"column":29},"end":{"row":80,"column":30},"action":"insert","lines":[" "],"id":8}],[{"start":{"row":79,"column":65},"end":{"row":80,"column":0},"action":"insert","lines":["",""],"id":9},{"start":{"row":80,"column":0},"end":{"row":80,"column":6},"action":"insert","lines":["      "]}],[{"start":{"row":80,"column":4},"end":{"row":80,"column":6},"action":"remove","lines":["  "],"id":10}],[{"start":{"row":80,"column":4},"end":{"row":80,"column":5},"action":"insert","lines":["e"],"id":11},{"start":{"row":80,"column":5},"end":{"row":80,"column":6},"action":"insert","lines":["x"]}],[{"start":{"row":80,"column":4},"end":{"row":80,"column":6},"action":"remove","lines":["ex"],"id":12},{"start":{"row":80,"column":4},"end":{"row":80,"column":10},"action":"insert","lines":["except"]}],[{"start":{"row":80,"column":10},"end":{"row":80,"column":11},"action":"insert","lines":[":"],"id":13}],[{"start":{"row":80,"column":11},"end":{"row":80,"column":12},"action":"insert","lines":[" "],"id":14},{"start":{"row":80,"column":12},"end":{"row":80,"column":13},"action":"insert","lines":["P"]},{"start":{"row":80,"column":13},"end":{"row":80,"column":14},"action":"insert","lines":["a"]},{"start":{"row":80,"column":14},"end":{"row":80,"column":15},"action":"insert","lines":["s"]},{"start":{"row":80,"column":15},"end":{"row":80,"column":16},"action":"insert","lines":["s"]}],[{"start":{"row":80,"column":12},"end":{"row":80,"column":13},"action":"remove","lines":["P"],"id":15}],[{"start":{"row":80,"column":12},"end":{"row":80,"column":13},"action":"insert","lines":["p"],"id":16}],[{"start":{"row":78,"column":8},"end":{"row":78,"column":9},"action":"insert","lines":[" "],"id":17}],[{"start":{"row":78,"column":9},"end":{"row":79,"column":0},"action":"remove","lines":["",""],"id":18},{"start":{"row":78,"column":9},"end":{"row":78,"column":10},"action":"remove","lines":[" "]},{"start":{"row":78,"column":9},"end":{"row":78,"column":10},"action":"remove","lines":[" "]},{"start":{"row":78,"column":9},"end":{"row":78,"column":10},"action":"remove","lines":[" "]},{"start":{"row":78,"column":9},"end":{"row":78,"column":10},"action":"remove","lines":[" "]},{"start":{"row":78,"column":9},"end":{"row":78,"column":10},"action":"remove","lines":[" "]},{"start":{"row":78,"column":9},"end":{"row":78,"column":10},"action":"remove","lines":[" "]}]]},"ace":{"folds":[],"scrolltop":991.3333129882812,"scrollleft":0,"selection":{"start":{"row":105,"column":4},"end":{"row":105,"column":4},"isBackwards":false},"options":{"tabSize":2,"useSoftTabs":true,"guessTabSize":false,"useWrapMode":false,"wrapToView":true},"firstLineState":{"row":93,"state":"start","mode":"ace/mode/python"}},"timestamp":1587431112443,"hash":"611c19052719966273a69e3884fe7c37a16528f0"}
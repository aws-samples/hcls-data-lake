import json, logging, boto3
import base64

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(er7, lambda_context):
  logger.info(er7)

  if not ('\n' in er7) and not ('\r' in er7):
    er7 = __decode_from_base64 (er7, 'utf-8')
    logger.info("Decoded from Base64: {}".format(er7))

  # The most common issues, add more complicated rules if required
  er7 = er7.replace('\r\n','\r')
  er7 = er7.replace('\n','\r')
  er7 = er7.replace('\r','\r')
  
  return (er7)

def __decode_from_base64(encoded_message, encoding):
  base64_bytes = encoded_message.encode(encoding)
  message_bytes = base64.b64decode(base64_bytes)
  return message_bytes.decode(encoding)
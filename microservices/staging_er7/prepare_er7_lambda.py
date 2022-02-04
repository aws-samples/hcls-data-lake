import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(er7, lambda_context):
  logger.info(er7)

  # The most common issues, add more complicated rules if required
  er7 = er7.replace('\r\n','\r')
  er7 = er7.replace('\n','\r')
  er7 = er7.replace('\r','\r')
  
  return (er7)
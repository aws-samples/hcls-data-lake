import boto3, json, logging, os
from botocore.exceptions import ClientError

logger = logging.getLogger()
logger.setLevel(logging.INFO)

sfn = boto3.client('stepfunctions')

def lambda_handler(event, context):
  logger.info(event)
  sfn_arn = os.environ["step_function"]
  
  # Transfer items from event to pass to Step Function
  data = {'Message':event['Records'][0]['Sns']['Message'], 'MessageAttributes': event['Records'][0]['Sns']['MessageAttributes']}
  logger.info(data)
  
  response = sfn.start_execution(
    stateMachineArn=sfn_arn,
    input= json.dumps(data)
  )
  
  logger.info(response)
import boto3
from botocore.exceptions import ClientError
import random

from lib import cf_util

def deploy(stack_name):
  # Get the CloudFormation template
  with open("core_infrastructure/hcdl_core_stack.yml") as template_fileobj: template_data = template_fileobj.read()
  
  try:
    cf = boto3.client('cloudformation')
    
    if cf_util.stack_exists(stack_name):
      # Retrieve existing names
      bucket_name = cf_util.get_physical_resource_id(stack_name, "Bucket")
      artifact_bucket_name = cf_util.get_physical_resource_id(stack_name, "ArtifactBucket")
      
      # Set the parameters
      parameter_map=[
        {
          'ParameterKey': 'BucketName',
          'ParameterValue': bucket_name
        },
        {
          'ParameterKey': 'ArtifactBucketName',
          'ParameterValue': artifact_bucket_name
        }
      ]
      
      # Create the stack
      response = cf.update_stack(
          StackName=stack_name,
          TemplateBody=template_data,
          Parameters=parameter_map,
      )
      
      print ("Stack updated")
    else:
      # Get a random number to ensure bucket name is unique
      rand_num = str(random.randint(0,999999999))
 
      # Set the parameters
      parameter_map=[
        {
          'ParameterKey': 'BucketName',
          'ParameterValue': "healthcare-data-lake-" + rand_num
        },
        {
          'ParameterKey': 'ArtifactBucketName',
          'ParameterValue': "healthcare-data-lake-artifacts-" + rand_num
        }
      ]
  
      # Create the stack
      response = cf.create_stack(
          StackName=stack_name,
          TemplateBody=template_data,
          Parameters=parameter_map,
      )
      
      print ("Stack created")
      
    # Wait until it completes
    waiter = cf.get_waiter('stack_create_complete')
    waiter.wait(StackName=stack_name)
  except ClientError as ex:
    error_message = ex.response['Error']['Message']
    if error_message == 'No updates are to be performed.':
      print("No changes to stack")
    else:
      raise
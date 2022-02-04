import boto3
import time
import os
from lib import cf_util
from lib import lambda_util

local_folder = os.path.dirname(os.path.realpath(__file__))
template_file_path = local_folder + "/front_door_stack.yml"

def deploy(stack_name, core_stack_name):
  # Sync our lambda function
  artifact_bucket_name = cf_util.get_physical_resource_id(core_stack_name, "ArtifactBucket")
  key, version = lambda_util.sync_lambda_function(local_folder+"/front_door_lambda.py", artifact_bucket_name)
  
  params = {
    'CoreStack':core_stack_name,
    'FunctionKey': key,
    'FunctionVersion': version, 
    'FunctionHandler': 'front_door_lambda.lambda_handler'
  }
  
  # Explicitly acknowledge that we are creating IAM roles
  capabilities=['CAPABILITY_IAM']

  action = cf_util.create_or_update_stack(stack_name, template_file_path, params, capabilities)
  if action == 'create':
    __set_attribute_map(stack_name) # Set attribute map through Boto as 'set-principal-tag-attribute-map' operation is not yet in CloudFormation
    print("User attributes mapped")
  
  return action

def __set_attribute_map(stack_name):
  identity_pool_id = cf_util.get_physical_resource_id(stack_name, "IdentityPool")
  user_pool_id = cf_util.get_physical_resource_id(stack_name, "UserPool")

  # Cognito endpoint isn't a Physical ID in the stack, so we get it from the Outputs
  cognito_endpoint = cf_util.get_output_value(stack_name, 'CognitoEndpoint')

  cid = boto3.client('cognito-identity')
  response = cid.set_principal_tag_attribute_map(
    IdentityPoolId=identity_pool_id,
    IdentityProviderName=cognito_endpoint+"/"+user_pool_id,
    PrincipalTags={
      'read': 'custom:read',
      'write': 'custom:write'
    }
  )
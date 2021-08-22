import os
from lib import lambda_util, cf_util

local_folder = os.path.dirname(os.path.realpath(__file__))
template_file_path = local_folder+"/ingest_er7_stack.yml"

def deploy(stack_name, core_stack_name, auth_stack_name, parse_stack_name):
  # Sync our lambda function
  artifact_bucket_name = cf_util.get_physical_resource_id(core_stack_name, "ArtifactBucket")
  key, version = lambda_util.sync_lambda_function(local_folder+"/ingest_er7_lambda.py", artifact_bucket_name)

  params = {
    'CoreStack':core_stack_name, 
    'AuthStack': auth_stack_name,
    'ParseStack': parse_stack_name,
    'FunctionKey': key,
    'FunctionVersion': version, 
    'FunctionHandler': 'ingest_er7_lambda.lambda_handler'
  }
 
  # Explicitly acknowledge that we are creating IAM roles
  capabilities=['CAPABILITY_IAM']
  
  action = cf_util.create_or_update_stack(stack_name, template_file_path, params, capabilities)
  if action == 'create': print("Stack created")
  elif action == 'update': print("Stack updated")
  elif action == 'none': print("No changes")
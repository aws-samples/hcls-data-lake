import os
from lib import lambda_util, cf_util

local_folder = os.path.dirname(os.path.realpath(__file__))
template_file_path = local_folder+"/write_message_stack.yml"

def deploy(stack_name, core_stack_name):
  # Sync our lambda function
  artifact_bucket_name = cf_util.get_physical_resource_id(core_stack_name, "ArtifactBucket")
  key, version = lambda_util.sync_lambda_function(local_folder+"/write_message_lambda.py", artifact_bucket_name)
  
  params = {
    'CoreStack':core_stack_name, 
    'LambdaKey': key,
    'LambdaVersion': version, 
    'Handler': 'write_message_lambda.lambda_handler'
  }
  
  return cf_util.create_or_update_stack(stack_name, template_file_path, params, ['CAPABILITY_IAM'])
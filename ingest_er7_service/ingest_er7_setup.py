import sys

from lib import lambda_util, cf_util

def deploy(stack_name, core_stack_name, auth_stack_name):
  # Upload our lambda function
  artifact_bucket_name = cf_util.get_physical_resource_id(core_stack_name, "ArtifactBucket")
  key = lambda_util.upload_python_function("ingest_er7_service/ingest_er7_lambda.py", artifact_bucket_name)
  print ("Lambda function uploaded")
  
  template_file_path = "ingest_er7_service/hcdl_ingest_er7_stack.yml"
  params = {'CoreStack':core_stack_name, 'AuthStack': auth_stack_name, 'FunctionKey': key}
 
  # Explicitly acknowledge that we are creating IAM roles
  capabilities=['CAPABILITY_IAM']
  
  action = cf_util.create_or_update_stack(stack_name, template_file_path, params, capabilities)
  if action == 'create': print("Stack created")
  elif action == 'update': print("Stack updated")
  elif action == 'none': print("No changes")
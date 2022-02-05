import boto3
from botocore.exceptions import ClientError
from lib import lambda_util, cf_util
import os

local_folder = os.path.dirname(os.path.realpath(__file__))
template_file_path = local_folder + "/staging_stack.yml"
hl7apyUrl="https://files.pythonhosted.org/packages/6d/97/9903a942be1d3d7a193d643ef29c73ad300ab8594e01e6f8d23285bcf77a/hl7apy-1.3.3.tar.gz"

def deploy(stack_name, core_stack_name, wait=False):
  params = {
    'CoreStack':core_stack_name
  }
  artifact_bucket = cf_util.get_physical_resource_id(core_stack_name, "ArtifactBucket")
  
  # Sync our Lambda functions
  params.update(__sync_and_get_params("trigger_lambda.py", artifact_bucket, 'Trigger'))
  params.update(__sync_and_get_params("prepare_er7_lambda.py", artifact_bucket, 'Prepare'))
  params.update(__sync_and_get_params("parse_er7_lambda.py", artifact_bucket, 'Parse'))

  # Deploy the Lambda Layer 
  layer_key = lambda_util.upload_external_library_for_lambda_layer(hl7apyUrl, artifact_bucket, 'python')
  params.update({'Hl7ParsingLibKey':layer_key})
  
  return cf_util.create_or_update_stack(stack_name, template_file_path, params,['CAPABILITY_IAM'], wait)
  
def __sync_and_get_params(file_name, artifact_bucket, prefix):
  key, version = lambda_util.sync_lambda_function(local_folder+"/"+file_name, artifact_bucket)
  handler = file_name.replace('.py',".lambda_handler")
  
  return {"{}LambdaKey".format(prefix):key, '{}LambdaVersion'.format(prefix): version, '{}Handler'.format(prefix): handler}
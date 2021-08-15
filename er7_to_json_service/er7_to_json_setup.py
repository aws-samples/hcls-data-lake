from lib import lambda_util, cf_util

# Deploy the Lambdas
def deploy(stack_name, core_stack_name):
  # Deploy the Lambda Layer
  hl7apyUrl="https://files.pythonhosted.org/packages/6d/97/9903a942be1d3d7a193d643ef29c73ad300ab8594e01e6f8d23285bcf77a/hl7apy-1.3.3.tar.gz"
  artifact_bucket_name = cf_util.get_physical_resource_id(core_stack_name, "ArtifactBucket")
  
  lambda_util.upload_external_library_for_lambda_layer(hl7apyUrl, artifact_bucket_name, 'python')
  
  #__upload_hl7apy_as_lambda_library()
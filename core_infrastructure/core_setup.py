import random
from lib import cf_util
import os

local_folder = os.path.dirname(os.path.realpath(__file__))
template_file_path = local_folder + "/core_stack.yml"

def deploy(stack_name):
  if cf_util.stack_exists(stack_name):
    params = {'BucketName':cf_util.USE_PREVIOUS_VALUE, 'ArtifactBucketName':cf_util.USE_PREVIOUS_VALUE}
  else:
    # Get a random number to ensure bucket name is unique
    rand_num = str(random.randint(0,999999999))
    params = {'BucketName':"healthcare-data-lake-" + rand_num, 'ArtifactBucketName':"healthcare-data-lake-artifacts-" + rand_num}

  action = cf_util.create_or_update_stack(stack_name, template_file_path, params)
  
  if action == 'create': print("Stack created")
  elif action == 'update': print("Stack updated")
  elif action == 'none': print("No changes")
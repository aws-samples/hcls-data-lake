from concurrent.futures import ThreadPoolExecutor
import boto3
from botocore.exceptions import ClientError
import argparse, sys, os
from lib import cf_util

# Lets us find our lib folder for import
sys.path.append(".")
from microservices.core import core_setup
from microservices.front_door import front_door_setup
from microservices.staging_er7 import staging_setup

cf = boto3.client('cloudformation')

def main():
  # Get the arguments
  parser = argparse.ArgumentParser()
  parser.add_argument('-s', '--stack-name', help="Stack name", required=True)
  parser.add_argument('-d', help="Delete stack", action='store_true')

  args = parser.parse_args()
  stack_name = args.stack_name
  
  # Stack names
  core_stack_name = stack_name +"-core"
  front_door_stack_name = stack_name +"-front-door"
  staging_stack_name = stack_name +"-staging"
  
  if (args.d):
    # Delete all but core in parallel first
    print ("Delete all but core first...")
    cf_util.delete_stacks(front_door_stack_name, staging_stack_name)
    
    # Delete core
    print("Delete core...")
    
    # Delete all objects from our buckets
    s3 = boto3.resource('s3')
    try:
      s3.Bucket(cf_util.get_physical_resource_id(core_stack_name, "Bucket")).object_versions.delete()
      s3.Bucket(cf_util.get_physical_resource_id(core_stack_name, "ArtifactBucket")).object_versions.delete()
    except ClientError as e:
      if "does not exist" in e.response['Error']['Message']: None # Stack already isn't there
      else: raise
    
    cf_util.delete_stacks(core_stack_name)
  else: 
    print ("Deploying the core stack...")
    core_setup.deploy(core_stack_name, True)
    
    print ("Deploying the remaining stacks...")
    front_door_setup.deploy(front_door_stack_name, core_stack_name, False)
    staging_setup.deploy(staging_stack_name, core_stack_name, False)
    
if __name__== "__main__":
  main()
import boto3
from botocore.exceptions import ClientError
import argparse, sys, os
from lib import cf_util

# Lets us find our lib folder for import
sys.path.append(".")
from core_infrastructure import core_setup
from auth_service import auth_setup
from ingest_er7_service import ingest_er7_setup
from er7_to_json_service import er7_to_json_setup
from staging_service import staging_setup

def main():
  # Get the arguments
  parser = argparse.ArgumentParser()
  parser.add_argument('-s', '--stack-name', help="Stack name", required=True)
  parser.add_argument('-d', help="Delete stack", action='store_true')

  args = parser.parse_args()
  stack_name = args.stack_name
  
  # Stack names
  core_stack_name = stack_name +"-core"
  auth_stack_name = stack_name +"-auth"
  er7_to_json_stack_name = stack_name +"-er7-to-json"
  ingest_er7_stack_name = stack_name +"-ingest-er7"
  staging_stack_name = stack_name +"-staging"
  
  if (args.d):
    print("Delete staging")
    cf_util.delete_stack(staging_stack_name)
    
    print("Delete ingest")
    cf_util.delete_stack(ingest_er7_stack_name)
    
    print("Delete parse ER7 to JSON")
    cf_util.delete_stack(er7_to_json_stack_name)
    
    print("Delete auth")
    cf_util.delete_stack(auth_stack_name)

    print("Delete core")
    
    # Delete all objects from our buckets
    s3 = boto3.resource('s3')
    try:
      s3.Bucket(cf_util.get_physical_resource_id(core_stack_name, "Bucket")).object_versions.delete()
      s3.Bucket(cf_util.get_physical_resource_id(core_stack_name, "ArtifactBucket")).object_versions.delete()
    except ClientError as e:
      if "does not exist" in e.response['Error']['Message']: None # Stack already isn't there
      else: raise
    
    cf_util.delete_stack(core_stack_name)
  else: 
    print ("Deploying the core stack")
    core_setup.deploy(core_stack_name)
    
    print ("Deploying the authentication stack")
    auth_setup.deploy(auth_stack_name, core_stack_name)  
    
    print ("Deploying the ER7 to JSON stack")
    er7_to_json_setup.deploy(er7_to_json_stack_name, cf_util.get_physical_resource_id(core_stack_name, "ArtifactBucket"))
    
    print ("Deploying the ingest ER7 stack")
    ingest_er7_setup.deploy(ingest_er7_stack_name, core_stack_name, auth_stack_name, er7_to_json_stack_name)
    
    print ("Deploying the temporary staging service")
    staging_setup.deploy(staging_stack_name, core_stack_name)
  
if __name__== "__main__":
  main()
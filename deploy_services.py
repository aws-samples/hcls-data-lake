from concurrent.futures import ThreadPoolExecutor
import time
import boto3
from botocore.exceptions import ClientError
import argparse, sys, os
from lib import cf_util

# Lets us find our lib folder for import
sys.path.append(".")
from microservices.core import core_setup
from microservices.front_door import front_door_setup
from microservices.write_message import write_message_setup
from microservices.staging_er7 import staging_setup
# from ingest_er7_service import ingest_er7_setup
# from er7_to_json_service import er7_to_json_setup
# from staging_service import staging_setup

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
  write_stack_name = stack_name +"-write"
  # er7_to_json_stack_name = stack_name +"-er7-to-json"
  # ingest_er7_stack_name = stack_name +"-ingest-er7"
  staging_stack_name = stack_name +"-staging"
  
  if (args.d):
    with ThreadPoolExecutor(max_workers=3) as executor:
      print ("Deleting all but core")
      fdr_future = executor.submit(cf_util.delete_stack, front_door_stack_name)
      wrt_future = executor.submit(cf_util.delete_stack, write_stack_name)
      stg_future = executor.submit(cf_util.delete_stack, staging_stack_name)
      
      while True:
        if(fdr_future.running()): print("Front door deleting...")
        if(wrt_future.running()): print("Write deleting...")
        if(stg_future.running()): print("Staging deleting...")

        if(fdr_future.done() and wrt_future.done() and stg_future.done()):
          break
    
        time.sleep(5)
      
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
    action = core_setup.deploy(core_stack_name)
    print ("Core stack: "+action)
    
    with ThreadPoolExecutor(max_workers=3) as executor:
      print ("Deploying the remaining stacks")
      fdr_future = executor.submit(front_door_setup.deploy, front_door_stack_name, core_stack_name)
      wrt_future = executor.submit(write_message_setup.deploy, write_stack_name, core_stack_name)
      stg_future = executor.submit(staging_setup.deploy, staging_stack_name, core_stack_name)
    
      while True:
        if(fdr_future.running()): print("Front door deploying...")
        if(wrt_future.running()): print("Write deploying...")
        if(stg_future.running()): print("Staging deploying...")

        if(fdr_future.done() and wrt_future.done() and stg_future.done()):
          print("Front door: " + fdr_future.result())
          print("Write: " + wrt_future.result())
          print("Staging: " + stg_future.result())
          break
    
        time.sleep(5)

if __name__== "__main__":
  main()
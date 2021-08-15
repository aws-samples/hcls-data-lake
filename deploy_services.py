import boto3
from botocore.exceptions import ClientError
import argparse, sys, os

# Lets us find our lib folder for import
sys.path.append(".")
from core_infrastructure import core_setup
from auth_service import auth_setup
from ingest_er7_service import ingest_er7_setup
from er7_to_json_service import er7_to_json_setup

def main():
  # Get the arguments
  parser = argparse.ArgumentParser()
  parser.add_argument('-s', '--stack-name', help="Stack name", required=True)

  args = parser.parse_args()
  stack_name = args.stack_name

  print ("Creating the core stack")
  core_stack_name = stack_name +"-core"
  core_setup.deploy(core_stack_name)
  
  print ("Creating the authentication stack")
  auth_stack_name = stack_name +"-auth"
  auth_setup.deploy(auth_stack_name, core_stack_name)  
  
  print ("Creating the ingest ER7 stack")
  ingest_er7_stack_name = stack_name +"-ingest-er7"
  ingest_er7_setup.deploy(ingest_er7_stack_name, core_stack_name, auth_stack_name)
  
  print ("Creating the ER7 to JSON stack")
  er7_to_json_stack_name = stack_name +"-er7-to-json"
  
if __name__== "__main__":
  main()
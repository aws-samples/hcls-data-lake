import boto3
from botocore.exceptions import ClientError
import argparse, sys, requests, json, base64
import random

# Lets us find our lib folder for import
sys.path.append(".")
from microservices.core import core_setup
from microservices.front_door import front_door_setup
from lib import cognito_util, cf_util

def __create_user_if_not_exists(stack_name, username, password, r_institution, w_institution):
  userPoolId = cf_util.get_physical_resource_id(stack_name, "UserPool")
  appClientId = cf_util.get_physical_resource_id(stack_name, "UserPoolClient")
  
  userAttributes=[
    {'Name': 'custom:read', 'Value': r_institution},
    {'Name': 'custom:write', 'Value': w_institution}
  ]
  
  try:
    cognito_util.create_and_authenticate_user(userPoolId, appClientId, username, password, userAttributes)
  except ClientError as e:
    if e.response['Error']['Code'] == "UsernameExistsException": None
    else: raise

def encodeToBase64(string, encoding):
  str_bytes = string.encode(encoding)
  base64_bytes = base64.b64encode(str_bytes)
  return base64_bytes.decode(encoding)

def sendRequest(idToken, url, msg, encoding):
  headers = { 
    'Authorization': idToken, 
    'Content-Type': "application/json"
  }

  data = json.dumps({'msg': encodeToBase64(msg, encoding), "encoding": encoding})

  resp = requests.post(url, headers=headers, data=data, verify=True)
  
  j_resp = json.loads(resp.text)
  return json.dumps(j_resp, indent=2)

def main():
  # Get the arguments
  parser = argparse.ArgumentParser()
  parser.add_argument('-s', '--stack-name', help="Stack name", required=True)
  args = parser.parse_args()
  stack_name = args.stack_name

  front_door_stack_name = stack_name +"-front-door"
  # ingest_er7_stack_name = stack_name +"-ingest-er7"

  # Pull data from our stacks
  url = cf_util.get_output_value(front_door_stack_name, "PostEr7RouteUrl")
  app_client_id = cf_util.get_physical_resource_id(front_door_stack_name, "UserPoolClient")

  users = ["admin@example.com","reader@example.com","writer@example.com"]
  password = "3C{KWLrXieQ#"
  institution="my_hospital_123"
  
  # Create our user
  print("Create users")
  __create_user_if_not_exists(front_door_stack_name, users[0], password, institution, institution)
  __create_user_if_not_exists(front_door_stack_name, users[1], password, institution, "")
  __create_user_if_not_exists(front_door_stack_name, users[2], password, "", institution)
 
  # Create a simple HL7v2 message with a random element so we can keep uploading
  rand_num = str(random.randint(0,99999))
  msgs={"""MSH|^~\&|SOURCEEHR|WA|MIRTHDST|WA|201611111111||ADT^A01|MSGID{}|P|2.3|
EVN|A01|201611111111||
PID|1|100001^^^1^MRN1|900001||DOE^JOHN^^^^||19601111|M||WH|111 THAT PL^^HERE^WA^98020^USA||(206)555-5309|||M|NON|999999999|
NK1|1|DOE^JANE^|WIFE||(206)555-5555||||NK^NEXT OF KIN
PV1|1|O|1001^2002^01||||123456^DOCTOR^BOB^T^^DR|||||||ADM|A0|""".format(rand_num), "I'm just a random number: {}".format(rand_num)}
  
  for user in users:
    idToken = cognito_util.get_id_token(user, password, app_client_id)
    
    for msg in msgs:
      print ("Send message")
      response = sendRequest(idToken, url, msg, 'utf-8')
      print (response)

if __name__== "__main__":
  main()
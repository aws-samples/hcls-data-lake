import boto3
from botocore.exceptions import ClientError
import argparse, sys, requests, json, base64

def main():
  # Get the arguments
  parser = argparse.ArgumentParser()
  parser.add_argument('-s', '--stack-name', help="The name of the healthcare data lake stack", required=True)
  parser.add_argument('-u', '--username', help="User username for testing (direct or from Parameter Store)", required=True)
  parser.add_argument('-p', '--password', help="User password for testing (direct or from Parameter Store)", required=True)
  
  args = parser.parse_args()
  stackName = args.stack_name
  
  # Get the username and password
  client = boto3.client('ssm')
  
  try: 
    username = client.get_parameter(Name=args.username)["Parameter"]["Value"]
  except ClientError: 
    username = args.username
  
  try: 
    password = client.get_parameter(Name=args.password, WithDecryption=True)["Parameter"]["Value"]
  except ClientError: 
    password = args.password
  
  # Extract variables from our stack output
  client = boto3.client('cloudformation')
  response = client.describe_stacks(StackName=stackName)
  outputs = response["Stacks"][0]["Outputs"]
  
  appClientId = next(item for item in outputs if item["OutputKey"] == "AppClientId")["OutputValue"]
  apiGatewayId  = next(item for item in outputs if item["OutputKey"] == "ApiGatewayId")["OutputValue"]

  #--------------------------- Get the idToken
  idToken = get_user_password_auth(username, password, appClientId)
  
  #--------------------------- Send the request
  msg="""MSH|^~\&|SOURCEEHR|WA|MIRTHDST|WA|201611111111||ADT^A01|MSGID10001|P|2.3|
EVN|A01|201611111111||
PID|1|100001^^^1^MRN1|900001||DOE^JOHN^^^^||19601111|M||WH|111 THAT PL^^HERE^WA^98020^USA||(206)555-5309|||M|NON|999999999|
NK1|1|DOE^JANE^|WIFE||(206)555-5555||||NK^NEXT OF KIN
PV1|1|O|1001^2002^01||||123456^DOCTOR^BOB^T^^DR|||||||ADM|A0|"""

  response = sendRequest(idToken, apiGatewayId, msg, 'utf-8', ["\r\n", "\n"])
  print (response)

def get_user_password_auth(username, password, appClientId):
  # Get the JSON Web Token (JWT)
  client = boto3.client('cognito-idp')
  
  response = client.initiate_auth(
    AuthFlow='USER_PASSWORD_AUTH',
    AuthParameters={
      'USERNAME': username,
      'PASSWORD': password
    },
    ClientId=appClientId
  )
  return response["AuthenticationResult"]["IdToken"]

def encodeToBase64(string, encoding):
  str_bytes = string.encode(encoding)
  base64_bytes = base64.b64encode(str_bytes)
  return base64_bytes.decode(encoding)

def sendRequest(idToken, apiGatewayId, msg, encoding, segTerm=None):
  region_name = boto3.session.Session().region_name
  headers = { 
    'Authorization': idToken, 
    "Content-Type": "application/json"
  }
  route="hl7v2/er7"
  url="https://"+apiGatewayId+".execute-api."+region_name+".amazonaws.com/"+route

  if segTerm is not None:
    data = json.dumps({'msg': encodeToBase64(msg, encoding), "encoding": encoding, "segTerm": ["\r\n", "\n"]})
  else:
    data = json.dumps({'msg': encodeToBase64(msg, encoding), "encoding": encoding})
  
  resp = requests.post(url, headers=headers, data=data, verify=True)
  
  j_resp = json.loads(resp.text)
  return json.dumps(j_resp, indent=4)

if __name__== "__main__":
  main()
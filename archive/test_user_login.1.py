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
  idToken = response["AuthenticationResult"]["IdToken"]
  
  #--------------------------- Good request
  msg="""MSH|^~\&|SendingApp|SendingFac|ReceivingApp|ReceivingFac|2007509101832132||ADT^A01^ADT_A01|200760910183213200723|D|2.5
EVN||2007509101832132
PID|1||P410000^^^||""||196505|M|||^^^OR^97007
PV1|1|I||||||||||||||||||||||||||||||||||||||||||200750816122536
PV2|||^^^^POSSIBLE MENINGITIS OR CVA
OBX|1|NM|21612-7^REPORTED PATIENT AGE^LN||40|a^Year^UCUM|||||F
DG1|1||784.3^APHASIA^I9C||200750816|A
DG1|2||784.0^HEADACHE^I9C||200750816|A
DG1|3||781.6^MENINGISMUS^I9C||200750816|A"""

  print(sendRequest(idToken, apiGatewayId, msg, 'utf-8', ["\r\n", "\n"]))
  
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
  print (resp)
  
  j_resp = json.loads(resp.text)
  return json.dumps(j_resp, indent=4)

if __name__== "__main__":
  main()
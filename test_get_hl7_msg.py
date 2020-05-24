import boto3
from botocore.exceptions import ClientError
import argparse, sys, requests, json, base64

def main():
  # Get the arguments
  parser = argparse.ArgumentParser()
  parser.add_argument('-s', '--stack-name', help="The name of the healthcare data lake stack", required=True)
  parser.add_argument('-u', '--username', help="User username for testing", required=True)
  parser.add_argument('-p', '--password', help="User password for testing", required=True)
  parser.add_argument('-g', '--gateway-id', help="ID of the API Gateway", required=True)
  parser.add_argument('-c', '--client-app-id', help="ID of the client app", required=True)
  parser.add_argument('-m', '--message-id', help="ID of the message", required=True)
  parser.add_argument('-f', '--format', help="Format to retrieve in", required=True)

  args = parser.parse_args()
  stackName = args.stack_name
  username = args.username
  password = args.password
  appClientId = args.client_app_id
  apiGatewayId  = args.gateway_id
  msgId = args.message_id
  msgFormat = args.format

  #--------------------------- Get the idToken
  idToken = get_user_password_auth(username, password, appClientId)
  
  getRequest(idToken, apiGatewayId, msgId, msgFormat)

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

def decode_from_base64(encoded_message, encoding):
  base64_bytes = encoded_message.encode(encoding)
  message_bytes = base64.b64decode(base64_bytes)
  return message_bytes.decode(encoding)

def getRequest(idToken, apiGatewayId, msgId, msgFormat):
  region_name = boto3.session.Session().region_name
  headers = { 
    'Authorization': idToken, 
  }
  route="hl7v2/format/"+msgFormat+"/msg_uuid/"+msgId
  url="https://"+apiGatewayId+".execute-api."+region_name+".amazonaws.com/"+route
  resp = requests.get(url, headers=headers, verify=True)
  print (url)
  print(resp)
  decode = decode_from_base64(resp.text,'utf-8')
  print (decode)

if __name__== "__main__":
  main()
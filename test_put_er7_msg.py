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

  args = parser.parse_args()
  stackName = args.stack_name
  username = args.username
  password = args.password
  appClientId = args.client_app_id
  apiGatewayId  = args.gateway_id

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
  
  msg2="""MSH|^~\&|SendingApp|SendingFac|ReceivingApp|ReceivingFac|2007509101832132||ADT^A01^ADT_A01|200760910183213200723|D|2.5
EVN||2007509101832132
PID|1||P410000^^^||""||196505|M|||^^^OR^97007
PV1|1|I||||||||||||||||||||||||||||||||||||||||||200750816122536
PV2|||^^^^POSSIBLE MENINGITIS OR CVA
OBX|1|NM|21612-7^REPORTED PATIENT AGE^LN||40|a^Year^UCUM|||||F
DG1|1||784.3^APHASIA^I9C||200750816|A
DG1|2||784.0^HEADACHE^I9C||200750816|A
DG1|3||781.6^MENINGISMUS^I9C||200750816|A"""
  response = sendRequest(idToken, apiGatewayId, msg2, 'utf-8', ["\r\n", "\n"])
  print (response)

  msg3 = """MSH|^~\&|ATHENANET|99999^MA - athenahealth Testing^1^Test Clinic|TestInterface||201505181347||ADT^A31|183M90009|T|2.3.1
EVN|A31|201505180146|||username
PID||456789|456789|456789|LASTNAME^FIRSTNAME^MIDDLE^SUFFIX||19900101|M|PREFERREDNAME|2028-9^Asian|ADDRESS^ADDRESS (CTD)^CITY^STATE^00000^COUNTRY||(111)111-1111^PRN^PH^^1^111^1111111~(333)333-3333^WPN^PH^^1^333^3333333~Patientemail@email.com^NET^^Patientemail@email.com~(222)222-2222^ORN^CP^^1^222^2222222|(333)333-3333^WPN^PH^^1^333^3333333|eng^English|S|||000000000||ATHENA|2186-5^Not Hispanic or Latino
PD1||||A12123^PCPLASTNAME^PCPFIRSTNAME
NK1|1|KIN^NEXTOF|CHILD||||N
NK1|2|CONTACT^EMERGENCY|PARENT||||C
PV1|||2^TEST DEPARTMENT^^TEST DEPARTMENT||||12345678^SEUSS^DOC|98765432^REFERRING^DOC|||||||||12345678^SEUSS^DOC
GT1|1||GTORLASTNAME^GTORFIRSTNAME^GTORMIDDLE^GTORSUFFIX||ADDRESS^ADDRESS (CTD)^CITY^STATE^00000^COUNTRY|(gtorphone^gtoremail@email.com||19600601|||Child|||||ATHENA|GTOREMPLOYERADDRESS^^CITY^STATE^00000|(999)999-9999|||||||||||||||||||||||||||EMERGENCY CONTACT|(EChomephone||PARENT
IN1|1|982^UNITED HEALTHCARE|123^United Healthcare|United Healthcare|PO BOX 740800^^ATLANTA^GA^30374-0800||(877)842-3210||||ATHENA||||C1|LASTNAME^FIRSTNAME^MIDDLENNAME|Self|19880601|ADDRESS^ADDRESS (CTD)^BRIGHTON^MA^02135^1^000000000|||1||||20150409||||||||||12345|||||||M"""
  response = sendRequest(idToken, apiGatewayId, msg3, 'utf-8', ["\r\n", "\n"])
  print (response)

  msg4 = """MSH|^~\&||.|||199908180016||ADT^A04|ADT.1.1698593|P|2.7
PID|1||000395122||LEVERKUHN^ADRIAN^C||19880517180606|M|||6 66TH AVE NE^^WEIMAR^DL^98052||(157)983-3296|||S||12354768|87654321
NK1|1|TALLIS^THOMAS^C|GRANDFATHER|12914 SPEM ST^^ALIUM^IN^98052|(157)883-6176
NK1|2|WEBERN^ANTON|SON|12 STRASSE MUSIK^^VIENNA^AUS^11212|(123)456-7890
IN1|1|PRE2||LIFE PRUDENT BUYER|PO BOX 23523^WELLINGTON^ON^98111|||19601||||||||THOMAS^JAMES^M|F|||||||||||||||||||ZKA535529776"""
  response = sendRequest(idToken, apiGatewayId, msg4, 'utf-8', ["\r\n", "\n"])
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
    data = json.dumps({'msg': encodeToBase64(msg, encoding), "encoding": encoding, "seg-term": ["\r\n", "\n"]})
  else:
    data = json.dumps({'msg': encodeToBase64(msg, encoding), "encoding": encoding})
  
  resp = requests.post(url, headers=headers, data=data, verify=True)
  
  j_resp = json.loads(resp.text)
  return json.dumps(j_resp, indent=4)

if __name__== "__main__":
  main()
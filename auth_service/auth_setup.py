import boto3
import time
import os
from lib import cf_util

local_folder = os.path.dirname(os.path.realpath(__file__))
template_file_path = local_folder + "/auth_stack.yml"

def deploy(stack_name, core_stack_name):
  params = {'CoreStack':core_stack_name}
  
  # Explicitly acknowledge that we are creating IAM roles
  capabilities=['CAPABILITY_IAM']

  action = cf_util.create_or_update_stack(stack_name, template_file_path, params, capabilities)
  if action == 'create':
    print("Stack created")
    __set_attribute_map(stack_name) # Set attribute map through Boto as 'set-principal-tag-attribute-map' operation is not yet in CloudFormation
    print("User attributes mapped")
  elif action == 'update': print("Stack updated")
  elif action == 'none': print("No changes")

def __set_attribute_map(stack_name):
  identity_pool_id = cf_util.get_physical_resource_id(stack_name, "IdentityPool")
  user_pool_id = cf_util.get_physical_resource_id(stack_name, "UserPool")

  # Cognito endpoint isn't a Physical ID in the stack, so we get it from the Outputs
  cf = boto3.client('cloudformation')
  cognito_endpoint = ""
  outputs = cf.describe_stacks(StackName=stack_name)['Stacks'][0]['Outputs']
  for o in outputs:
    if o['OutputKey'] == 'CognitoEndpoint': cognito_endpoint = o['OutputValue'] 
  
  cid = boto3.client('cognito-identity')
  response = cid.set_principal_tag_attribute_map(
    IdentityPoolId=identity_pool_id,
    IdentityProviderName=cognito_endpoint+"/"+user_pool_id,
    PrincipalTags={
      'read': 'custom:read',
      'write': 'custom:write'
    }
  )

def create_and_authenticate_user(stack_name, username, password, can_read='', can_write=''):
  # Get the user pool ID and Client ID
  userPoolId = cf_util.get_physical_resource_id(stack_name, "UserPool")
  appClientId = cf_util.get_physical_resource_id(stack_name, "UserPoolClient")

  client = boto3.client('cognito-idp')
  
  # Create the user
  response = client.admin_create_user(
    UserPoolId=userPoolId,
    Username=username,
    
    # The tag is simply not created if an empty string is used for value
    UserAttributes=[
      {
        'Name': 'custom:read',
        'Value': can_read
      },{
        'Name': 'custom:write',
        'Value': can_write
      }
    ],
    TemporaryPassword=password,
    MessageAction='SUPPRESS'
  )
      
  # Initiate the authentication
  response = client.admin_initiate_auth(
    UserPoolId=userPoolId,
    ClientId=appClientId,
    AuthFlow='ADMIN_USER_PASSWORD_AUTH',
    AuthParameters={
        'USERNAME': username,
        'PASSWORD': password
    }
  )
  session = response['Session']
  
  # Respond to challenge
  response = client.admin_respond_to_auth_challenge(
    UserPoolId=userPoolId,
    ClientId=appClientId,
    ChallengeName='NEW_PASSWORD_REQUIRED',
    ChallengeResponses={
      'NEW_PASSWORD': password,
      'USERNAME': username
    },
    Session=session
  )
  
  time.sleep(2) # Give a little time to finish
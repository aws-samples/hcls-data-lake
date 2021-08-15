import boto3
import random, string, argparse

def create_and_authenticate_user(userPoolId, appClientId, username, password, can_read, can_write):
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

def main():
  # Get the arguments
  parser = argparse.ArgumentParser()
  parser.add_argument('-p', '--user-pool-id', help="ID of user pool", required=True)
  parser.add_argument('-e', '--cognito-endpoint', help="Cognito endpoint", required=True)
  parser.add_argument('-i', '--identity-pool-id', help="ID of identity pool", required=True)
  parser.add_argument('-c', '--client-app-id', help="ID of the client app", required=True)
  parser.add_argument('-u', '--username', help="Username", required=True)
  parser.add_argument('-x', '--password', help="Password", required=True)
  parser.add_argument('-r', '--read-institution', help="Institution the user can read for", required=False)
  parser.add_argument('-w', '--write-institution', help="Institution the user can write for", required=False)

  args = parser.parse_args()
  username = args.username
  password = args.password
  cognitoEndpoint = args.cognito_endpoint
  identityPoolId = args.identity_pool_id
  userPoolId = args.user_pool_id
  appClientId = args.client_app_id
  can_read = "" if args.read_institution is None else args.read_institution
  can_write = "" if args.write_institution is None else args.write_institution

  create_and_authenticate_user(userPoolId, appClientId, username, password, can_read, can_write)
  
# Not used, but this is a way to generate a random Cognito password
def randomPassword(length):
  cognitoSpecialCharacters="^$*.[]{}()?-\"!@#%&/\,><':;|_~`"
  randomSource = string.ascii_letters + string.digits + cognitoSpecialCharacters
  
  # At least one of each type
  password = random.choice(string.ascii_lowercase)
  password += random.choice(string.ascii_uppercase)
  password += random.choice(string.digits)
  password += random.choice(cognitoSpecialCharacters)

  # Fill the remainder with random characters 
  for i in range(length-4):
    password += random.choice(randomSource)

  # Shuffle
  passwordList = list(password)
  random.SystemRandom().shuffle(passwordList)
  password = ''.join(passwordList)
  
  return password
  
if __name__== "__main__":
  main()
  print ("User created")
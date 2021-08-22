import boto3
import random, string, time

cognitoIdp = boto3.client('cognito-idp')
COGNITO_SPECIAL_CHARACTERS = "^$*.[]{}()?-\"!@#%&/\,><':;|_~`"

def create_and_authenticate_user(userPoolId, appClientId, username, password, userAttributes=None):
  # Create the user
  response = cognitoIdp.admin_create_user(
    UserPoolId=userPoolId,
    Username=username,
    UserAttributes=userAttributes, 
    TemporaryPassword=password,
    MessageAction='SUPPRESS'
  )
      
  # Initiate the authentication
  response = cognitoIdp.admin_initiate_auth(
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
  response = cognitoIdp.admin_respond_to_auth_challenge(
    UserPoolId=userPoolId,
    ClientId=appClientId,
    ChallengeName='NEW_PASSWORD_REQUIRED',
    ChallengeResponses={
      'USERNAME': username,
      'NEW_PASSWORD': password
    },
    Session=session
  )
  
  time.sleep(2) # Give a little time to finish

def get_id_token(username, password, appClientId):
  response = cognitoIdp.initiate_auth(
    AuthFlow='USER_PASSWORD_AUTH',
    AuthParameters={
      'USERNAME': username,
      'PASSWORD': password
    },
    ClientId=appClientId
  )
  return response["AuthenticationResult"]["IdToken"]

def get_random_password(length):
  randomSource = string.ascii_letters + string.digits + COGNITO_SPECIAL_CHARACTERS
  
  # At least one of each type
  password = random.choice(string.ascii_lowercase)
  password += random.choice(string.ascii_uppercase)
  password += random.choice(string.digits)
  password += random.choice(COGNITO_SPECIAL_CHARACTERS)

  # Fill the remainder with random characters 
  for i in range(length-4):
    password += random.choice(randomSource)

  # Shuffle
  passwordList = list(password)
  random.SystemRandom().shuffle(passwordList)
  password = ''.join(passwordList)
  
  return password
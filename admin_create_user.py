import boto3
import random, string, sys

def main():
  stackName = sys.argv[1] # Pass in the name of your stack!
  print ("Stack: "+stackName)

  # Example username and random password
  username = "user@example.com"
  password = randomPassword(12)

  # Extract variables from our stack output
  client = boto3.client('cloudformation')
  userPoolId = client.describe_stack_resource(StackName=stackName, LogicalResourceId='UserPool')["StackResourceDetail"]["PhysicalResourceId"]
  appClientId = client.describe_stack_resource(StackName=stackName, LogicalResourceId='UserPoolClient')["StackResourceDetail"]["PhysicalResourceId"]

  client = boto3.client('cognito-idp')
  
  # Create the user
  response = client.admin_create_user(
    UserPoolId=userPoolId,
    Username=username,
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
  
  # Add the user name and password to our Parameter Store for later use
  ssm = boto3.client('ssm')
  
  ssm.put_parameter(
    Name="/healthcare-data-lake/"+stackName+"/example-user/username", 
    Description='Example user username', 
    Value=username, 
    Type="String",
    Overwrite=True)
  
  ssm.put_parameter(
    Name="/healthcare-data-lake/"+stackName+"/example-user/password", 
    Description='Example user password', 
    Value=password, 
    Type="SecureString",
    Overwrite=True)
    
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
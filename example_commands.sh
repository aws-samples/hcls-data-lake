# Change your directory in the terminal to the parent folder (i.e. 'hcls-data-lake')

# Upload zip artifacts to an artifact bucket
python predeploy_artifacts.py

# Create the stack
stack="testStack"
aws cloudformation create-stack --stack-name $stack --template-body file://hcdl_stack.yml --capabilities CAPABILITY_IAM --parameters ParameterKey=DataLakeBucketName,ParameterValue=healthcare-data-lake-$RANDOM$RANDOM

# Updating the stack
# To avoid updating the bucket we need to fetch the random name that we assigned
bucketName=$(aws cloudformation describe-stack-resource --stack-name $stack --logical-resource-id DataLakeBucket --query 'StackResourceDetail.PhysicalResourceId' --output text)
aws cloudformation update-stack --stack-name $stack --template-body file://hcdl_stack.yml --capabilities CAPABILITY_IAM --parameters ParameterKey=DataLakeBucketName,ParameterValue=$bucketName

# Create a Cognito user
python admin_create_user.py $stack

# Test user login and message submission
username=$(aws ssm get-parameter --name /healthcare-data-lake/$stack/example-user/username --query 'Parameter.Value' --output text)
password=$(aws ssm get-parameter --name /healthcare-data-lake/$stack/example-user/password --with-decryption --query 'Parameter.Value' --output text)
gatewayId=$(aws cloudformation describe-stack-resource --stack-name $stack --logical-resource-id HttpAPI --query 'StackResourceDetail.PhysicalResourceId' --output text)
clientAppId=$(aws cloudformation describe-stack-resource --stack-name $stack --logical-resource-id UserPoolClient --query 'StackResourceDetail.PhysicalResourceId' --output text)
python test_er7_msg.py -s $stack -u $username -p $password -g $gatewayId -c $clientAppId
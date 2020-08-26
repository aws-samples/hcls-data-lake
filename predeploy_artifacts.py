#---------------------------------------------------------------------
# Ensures we have the artifact bucket and zip files needed by our CloudFormation
# Only need to run this when the artifacts change
#---------------------------------------------------------------------

import yaml, os, sys, uuid, tempfile, urllib, tarfile, zipfile, shutil
import boto3
from botocore.exceptions import ClientError

#---------------------------------------------------- Globals
hl7apyUrl="https://files.pythonhosted.org/packages/6d/97/9903a942be1d3d7a193d643ef29c73ad300ab8594e01e6f8d23285bcf77a/hl7apy-1.3.3.tar.gz"
parsingLambda="er7_to_json.py"

ssm = boto3.client('ssm')

#---------------------------------------------------- Main
def main():
  # Set working directory to file location
  os.chdir(os.path.dirname(os.path.abspath(__file__)))

  print ("Getting our bucket, creating if it does not exist")
  bucketName = get_bucket()
  print ("Using bucket "+bucketName)

  print ("Processing Lambda Layer")
  upload_lambda_library(bucketName)

  print("Zip and upload our parsing function "+parsingLambda)
  upload_lambda_function(bucketName)

  print("Done")

def get_bucket():
  artifactBucketParam = "/healthcare-data-lake/artifact-bucket"

  # Get the bucket name from parameter, set otherwise
  try:
    artifactBucketName = ssm.get_parameter(Name=artifactBucketParam)["Parameter"]["Value"]
  except ClientError: # Create this parameter and bucket if it does not exist
    artifactBucketName = "healthcare-data-lake-artifacts-" + str(uuid.uuid4())[0:12]

  # Create bucket if it does not exist
  create_bucket(artifactBucketName)
  ssm.put_parameter(
    Name=artifactBucketParam,
    Description='Name of the S3 bucket holding .zip artifacts for the healthcare data lake',
    Value=artifactBucketName,
    Type="String",
    Overwrite=True)

  return artifactBucketName

def create_bucket(bucket_name):
  s3_client = boto3.client('s3')
  region_name = boto3.session.Session().region_name

  try:
    if region_name == 'us-east-1':
      s3_client.create_bucket(Bucket=bucket_name)
    else:
      s3_client.create_bucket(Bucket=bucket_name, CreateBucketConfiguration={'LocationConstraint': region_name})
  except ClientError as e:
    return False
  return True

def upload_lambda_library(bucket):
  wd = os.getcwd()

  # Create temporary directory
  td = tempfile.mkdtemp()
  os.chdir(td)

  # Download HL7apy file
  print ("Downloading file: "+hl7apyUrl)
  file_name = hl7apyUrl[hl7apyUrl.rindex('/')+1:]
  urllib.request.urlretrieve(hl7apyUrl, file_name)

  print ("Processing to make Lambda Layer friendly")
  # Untar
  tar = tarfile.open(file_name)
  tar.extractall()
  tar.close()

  # Rename top folder to work as Lambda Layer
  lib_folder = file_name.replace(".tar.gz","")
  os.rename(lib_folder, "python") # Top folder for Lambda Layer expects 'python'

  # The file name and key to use
  key = lib_folder+".zip"

  # Zip up folder
  zipfolder(key, 'python')

  print("Uploading "+key)
  upload_file(key, bucket, None)

  # Go back to initial working directory
  os.chdir(wd)

  # Delete the temporary directory and contents
  shutil.rmtree(td)

  # Put the parameter
  ssm.put_parameter(
    Name="/healthcare-data-lake/hl7v2-parsing-Lambda-Layer",
    Description='The S3 key for the Lambda Layer being used to support HL7v2 parsing',
    Value=key,
    Type="String",
    Overwrite=True)

def zipfolder(foldername, target_dir):
  zipobj = zipfile.ZipFile(foldername, 'w', zipfile.ZIP_DEFLATED)
  rootlen = len(target_dir) + 1
  for base, dirs, files in os.walk(target_dir):
    for file in files:
      fn = os.path.join(base, file)
      zipobj.write(fn, target_dir+"/"+fn[rootlen:])

def upload_file(file_name, bucket, object_name=None, wait=True):
  s3_client = boto3.client('s3')

  # If S3 object_name was not specified, use file_name
  if object_name is None: object_name = file_name

  # Upload the file
  try:
    s3_client.upload_file(file_name, bucket, object_name)
  except ClientError as e:
    print(e)
    return False

  # Wait until completion if requested
  if wait:
    waiter = s3_client.get_waiter('object_exists')
    waiter.wait(Bucket=bucket, Key=object_name)

  return True

def upload_lambda_function(bucketName):
  lambdaKey = parsingLambda.replace(".py",".zip")
  with zipfile.ZipFile(lambdaKey, mode='w') as archive:
    archive.write(parsingLambda)
    archive.write('data_access_layer.py')
  upload_file(lambdaKey, bucketName)

  # Put in the parameter
  ssm.put_parameter(
    Name="/healthcare-data-lake/hl7v2-parsing-Lambda",
    Description='The S3 key for the the HL7v2 parsing Lambda function',
    Value=lambdaKey,
    Type="String",
    Overwrite=True)

  # Delete the temporary zip file
  os.remove(lambdaKey)

if __name__== "__main__":
  main()

import yaml
import boto3
from botocore.exceptions import ClientError
import uuid
import tempfile
import os
import shutil
import urllib.request
import zipfile
import tarfile
import logging
import sys

def main():
    # Set working directory to file location
    os.chdir(os.path.dirname(sys.argv[0]))
    
    # Load config file
    with open("config.yml", 'r') as ymlfile: cfg = yaml.full_load(ymlfile)
    
    region = cfg['region']
    stackName = cfg['stack_name']
    
    # Quit if this stack already exists
    if stack_exists(stackName, region):
        print ("Stack exists")
        return
    
    tempBucket = stackName.lower() + "-" + str(uuid.uuid4())
    tempLibraryKey = str(uuid.uuid4()) +".zip"
    
    # Upload our Lambda Layer
    upload_lambda_library_to_temp_bucket(cfg['url'], tempBucket, tempLibraryKey, region)
    
    # Zip and upload our Lambda Function
    tempFuncKey = str(uuid.uuid4()) +".zip"
    upload_lambda_function_to_temp_bucket("hl7_parser.py", tempBucket, tempFuncKey, region)
    
    # Deploy CloudFormation
    print("Deploying CloudFormation template")
    
    # Get the CloudFormation template
    with open('hl7_stack.yml') as template_fileobj: template_data = template_fileobj.read()
    
    if (region is None):
        cf = boto3.client('cloudformation')
    else:
        cf = boto3.client('cloudformation', region_name=region)
        
    response = cf.create_stack(
        StackName=cfg['stack_name'],
        TemplateBody=template_data,
        Parameters=[
            {
                'ParameterKey': 'TempBucket',
                'ParameterValue': tempBucket
            },{
                'ParameterKey': 'TempLibKey',
                'ParameterValue': tempLibraryKey
            },{
                'ParameterKey': 'TempFuncKey',
                'ParameterValue': tempFuncKey
            },{
                'ParameterKey': 'IngestBucket',
                'ParameterValue': cfg['ingest_bucket']
            }
        ],
        Capabilities=[
            'CAPABILITY_IAM'
        ],
    )
    
    # Wait until it's finished
    waiter = cf.get_waiter('stack_create_complete')
    waiter.wait(
        StackName=cfg['stack_name']
    )
    print ("Deployment complete")
    
    # Clean up
    print ("Deleting temporary bucket")
    s3 = boto3.resource('s3')
    bucket = s3.Bucket(tempBucket)
    for key in bucket.objects.all():
        key.delete()
    bucket.delete()

def stack_exists(name, region):
    if (region is None):
        cf = boto3.client('cloudformation')
    else:
        cf = boto3.client('cloudformation', region_name=region)
        
    try:
        data = cf.describe_stacks(StackName = name)
    except:
        return False
    return True

def upload_lambda_function_to_temp_bucket(file_name, bucket_name, key, region):
    # Create a temporary zip file with our function
    zipfile.ZipFile(key, mode='w').write(file_name)
    
    # Upload
    upload_file(key, bucket_name, None, region)
    
    # Delete the temporary zip file
    os.remove(key)

def upload_lambda_library_to_temp_bucket(url, bucket, key, region):
    wd = os.getcwd()
    
    # Create temporary directory
    td = tempfile.mkdtemp()
    os.chdir(td)
    
    # Download HL7apy file
    print ("Downloading file: "+url)
    file_name = url[url.rindex('/')+1:]
    urllib.request.urlretrieve(url, file_name)
    
    print ("Processing to make Lambda Layer friendly")
    # Untar 
    tar = tarfile.open(file_name)
    tar.extractall()
    tar.close()  
    
    # Rename top folder to work as Lambda Layer
    lib_folder = file_name.replace(".tar.gz","")
    os.rename(lib_folder, "python") # Top folder for Lambda Layer expects 'python'
    
    # Zip up folder
    zipfolder(key, 'python') #insert your variables here

    # Create temporary bucket
    print("Creating bucket "+bucket)
    create_bucket(bucket, region)
    
    print("Uploading "+key)
    upload_file(key, bucket, None, region)

    # Go back to initial working directory
    os.chdir(wd)
    
    # Delete the temporary directory and contents
    shutil.rmtree(td)

def zipfolder(foldername, target_dir):            
    zipobj = zipfile.ZipFile(foldername, 'w', zipfile.ZIP_DEFLATED)
    rootlen = len(target_dir) + 1
    for base, dirs, files in os.walk(target_dir):
        for file in files:
            fn = os.path.join(base, file)
            zipobj.write(fn, target_dir+"/"+fn[rootlen:])

def create_bucket(bucket_name, region=None):
    # Create bucket
    try:
        if region is None:
            s3_client = boto3.client('s3')
            s3_client.create_bucket(Bucket=bucket_name)
        else:
            s3_client = boto3.client('s3', region_name=region)
            location = {'LocationConstraint': region}
            s3_client.create_bucket(Bucket=bucket_name, CreateBucketConfiguration=location)
    except ClientError as e:
        logging.error(e)
        return False
    return True

def upload_file(file_name, bucket, object_name=None, region=None, wait=True):
    """Upload a file to an S3 bucket

    :param file_name: File to upload
    :param bucket: Bucket to upload to
    :param object_name: S3 object name. If not specified then file_name is used
    :return: True if file was uploaded, else False
    """

    # If S3 object_name was not specified, use file_name
    if object_name is None:
        object_name = file_name
        
    if region is None:
        s3_client = boto3.client('s3')
    else:
        s3_client = boto3.client('s3', region_name=region) 
        
    # Upload the file
    try:
        response = s3_client.upload_file(file_name, bucket, object_name)
    except ClientError as e:
        logging.error(e)
        return False
    
    # Wait until completion if requested
    if wait:
        waiter = s3_client.get_waiter('object_exists')
        waiter.wait(
            Bucket=bucket,
            Key=object_name
            )
            
    return True

if __name__== "__main__":
    main()
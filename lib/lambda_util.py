import tempfile, urllib, tarfile, shutil, os, zipfile
import boto3
from botocore.exceptions import ClientError

s3 = boto3.client('s3')

def sync_lambda_function(function_file, bucket_name):
  # Get the file name without the path
  function_name = os.path.basename(function_file)
  
  # The zip file will have the same name, but with a .zip extension
  if function_file.endswith('.py'): object_key = function_name.replace(".py",".zip")
  
  # Get the last modified date of the file (seconds since the Epoch)
  file_mtime = os.path.getmtime(function_file)

  # Check attributes of object on S3
  try:
    header = s3.head_object(Bucket=bucket_name, Key=object_key)
    object_mtime = header['LastModified'].timestamp()
  
    # If the local file is older than the one on S3, simply return the existing key and version
    if file_mtime <= object_mtime:
      return object_key, header['VersionId']
  except ClientError as e:
    if e.response['Error']['Code'] == "404": None # If the file isn't found then proceed with the upload
    else:
      raise
  
  # Create a zip file from the function
  zipfile.ZipFile(object_key, mode='w').write(function_file, arcname=function_name)
  
  try:
    __upload_file(object_key, bucket_name)
    return object_key, s3.head_object(Bucket=bucket_name, Key=object_key)['VersionId']
  except ClientError as e: raise
  finally:
    os.remove(object_key) # Delete the temporary zip file

def upload_external_library_for_lambda_layer(url, bucket, language):
  # Determine the key
  file_name = url[url.rindex('/')+1:]
  
  # Key will replace existing extension with zip
  zip_key = file_name.replace(".tar.gz","") + ".zip"

  # If this key is already in our bucket then just return the key and version
  try: 
    header = s3.head_object(Bucket=bucket, Key=zip_key)
    print("Library '{}' already exists, skipping download and sync".format(zip_key))
    return zip_key
  except ClientError as e:
    if e.response['Error']['Code'] == "404": None # If the file isn't found then proceed with the upload
    else: raise
  
  # Determine working directory
  wd = os.getcwd()
  
  # Create temporary directory and move to it
  td = tempfile.mkdtemp()
  os.chdir(td)
  
  # Download the file
  print ("Downloading file '{}' as '{}'".format(url, file_name))
  urllib.request.urlretrieve(url, file_name)
  
  # ----------- Process to make Lambda Layer friendly
  # Untar 
  tar = tarfile.open(file_name)
  tar.extractall()
  tar.close()  
  
  # Rename top folder to work as Lambda Layer
  lib_folder = file_name.replace(".tar.gz","")

  if language == 'python':
    os.rename(lib_folder, language) # Top folder for Lambda Layer expects 'python'
  
  # ----------- Zip and upload
  __zip_folder(zip_key, language)
  __upload_file(zip_key, bucket)

  # Go back to initial working directory
  os.chdir(wd)
  
  # Delete the temporary directory and contents
  shutil.rmtree(td)
  
  return zip_key

def __upload_file(file_name, bucket, object_name=None):
    # If S3 object_name was not specified, use file_name
    if object_name is None: object_name = os.path.basename(file_name)

    s3.upload_file(file_name, bucket, object_name)
    
    # Wait until completion
    waiter = s3.get_waiter('object_exists')
    waiter.wait(Bucket=bucket, Key=object_name)

def __zip_folder(foldername, target_dir):            
    zipobj = zipfile.ZipFile(foldername, 'w', zipfile.ZIP_DEFLATED)
    rootlen = len(target_dir) + 1
    for base, dirs, files in os.walk(target_dir):
        for file in files:
            fn = os.path.join(base, file)
            zipobj.write(fn, target_dir+"/"+fn[rootlen:])
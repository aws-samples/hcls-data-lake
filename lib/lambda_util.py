import boto3, os, zipfile
import tempfile, urllib, tarfile, shutil
from botocore.exceptions import ClientError

def upload_python_function(function_file, bucket_name, wait=True):
  # Get the file name without the path
  function_name = os.path.basename(function_file)
  
  # The zip file will have the same name and a different extension
  object_key = function_name.replace(".py",".zip")
  
  # Create a zip file from the function
  zipfile.ZipFile(object_key, mode='w').write(function_file, arcname=function_name)
  
  try:
    __upload_file(object_key, bucket_name)

    # Return the key used in S3
    return object_key
  except ClientError as e:
    raise
  finally:
    # Delete the temporary zip file
    os.remove(object_key)

def upload_external_library_for_lambda_layer(url, bucket, language):
    wd = os.getcwd()
    
    # Create temporary directory
    td = tempfile.mkdtemp()
    os.chdir(td)
    
    # Download the file
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
    key = lib_folder+".zip"
    
    if language == 'python':
      os.rename(lib_folder, "python") # Top folder for Lambda Layer expects 'python'
    
    # Zip up folder
    __zip_folder(key, 'language') 

    print("Uploading "+key)
    __upload_file(key, bucket)

    # Go back to initial working directory
    os.chdir(wd)
    
    # Delete the temporary directory and contents
    shutil.rmtree(td)

def __upload_file(file_name, bucket, object_name=None):
    # If S3 object_name was not specified, use file_name
    if object_name is None: object_name = os.path.basename(file_name)

    # Upload the file
    s3_client = boto3.client('s3')
    try: 
      response = s3_client.upload_file(file_name, bucket, object_name)
      
      # Wait until completion
      waiter = s3_client.get_waiter('object_exists')
      waiter.wait(Bucket=bucket, Key=object_name)
    except ClientError as e:
        raise
    return True

def __zip_folder(foldername, target_dir):            
    zipobj = zipfile.ZipFile(foldername, 'w', zipfile.ZIP_DEFLATED)
    rootlen = len(target_dir) + 1
    for base, dirs, files in os.walk(target_dir):
        for file in files:
            fn = os.path.join(base, file)
            zipobj.write(fn, target_dir+"/"+fn[rootlen:])
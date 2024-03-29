import boto3
from botocore.exceptions import ClientError
import time

cf = boto3.client('cloudformation')
USE_PREVIOUS_VALUE = "4978#@#$@!)*&@#/$3423" # Random string to avoid collision; not a complex enough case to warrant Enums
NO_UPDATES = "NO_UPDATES"
cache_map = {} # Used to cache results

def create_or_update_stack(stack_name, template_file_path, params, capabilities=[], wait=True):
  template_data = __parse_template(template_file_path)
  parameter_map = __get_parameter_map(params)
  
  try:
    if stack_exists(stack_name):
      response = cf.update_stack(
        StackName=stack_name,
        TemplateBody=template_data,
        Parameters=parameter_map,
        Capabilities=capabilities
      )
      waiter = cf.get_waiter('stack_update_complete')
    else:
      response = cf.create_stack(
        StackName=stack_name,
        TemplateBody=template_data,
        Parameters=parameter_map,
        Capabilities=capabilities,
        OnFailure='DELETE'
      )
      waiter = cf.get_waiter('stack_create_complete')
    
    if wait:  
      # Wait until stack deployment has finished
      waiter.wait(StackName=stack_name)
  except ClientError as ex:
    error_message = ex.response['Error']['Message']
    if error_message == 'No updates are to be performed.': return NO_UPDATES
    else: raise
  
  return cf.describe_stacks(StackName=stack_name)['Stacks'][0]['StackStatus']

# Delete batches of stacks in parallel
def delete_stacks(*stack_names):
  stack_ids = []
  
  # Kick off the deletes
  for stack_name in stack_names:
    stack_id = cf.describe_stacks(StackName=stack_name)['Stacks'][0]['StackId']
    stack_ids.append(stack_id)
    cf.delete_stack(StackName=stack_name)
  
  # Wait until they all complete
  while True:
    complete = True
    for stack_id in stack_ids:
      status = cf.describe_stacks(StackName=stack_id)['Stacks'][0]['StackStatus']
      if status not in ['DELETE_COMPLETE', 'DELETE_FAILED']:
        complete = False
        break
    
    if complete: break
    else: time.sleep(5)

def stack_exists(stack_name):
  stacks = cf.list_stacks()['StackSummaries']
  for stack in stacks:
    if stack['StackStatus'] == 'DELETE_COMPLETE':
      continue
    if stack_name == stack['StackName']:
      return True
  return False
  
def get_physical_resource_id(stack_name, logical_resource_id):
  key = stack_name +":" +logical_resource_id
  
  if not key in cache_map:
    physical_resource_id = cf.describe_stack_resource(
      StackName=stack_name, LogicalResourceId=logical_resource_id
      )['StackResourceDetail']['PhysicalResourceId']
    cache_map[key] = physical_resource_id
      
  return cache_map[key]

def get_output_value(stack_name, output_name):
  response = cf.describe_stacks(StackName=stack_name)
  outputs = response["Stacks"][0]["Outputs"]
  for output in outputs:
    keyName = output["OutputKey"]
    if keyName == output_name:
      return output["OutputValue"]
  
  return None
  
def __parse_template(template):
  with open(template) as template_fileobj: template_data = template_fileobj.read()
  response = cf.validate_template(TemplateBody=template_data)
  # if "CapabilitiesReason" in response:
  #   raise ValueError("Template '{}' failed validation: '{}'".format(template, response['CapabilitiesReason']))

  return template_data

def __get_parameter_map(params):
  parameter_map=[]
  for key, value in params.items(): 
    if value == USE_PREVIOUS_VALUE:
      parameter_map.append({'ParameterKey': key,'UsePreviousValue': True})
    else:
      parameter_map.append({'ParameterKey': key,'ParameterValue': value})
  return parameter_map
import boto3
import logging
from boto3.dynamodb.conditions import Key, Attr
from datetime import datetime


logger = logging.getLogger()
logger.setLevel(logging.INFO)


class DynamoDB():
    def __init__(self, dynamodb_table_name):
        self.dynamodb = self.dynamodb_resource()
        self.table = self.dynamodb_table()

    def dynamodb_resource(self):
        return boto3.resource('dynamodb')

    def dynamodb_table(self):
        return self.dynamodb.Table(self.dynamodb_table_name)

    def get_global_id(pids: List[str]):
        g_id = None
        no_global = []

        for pid in pids:
            response = self.table.query(
                KeyConditionExpression=Key('GSI1PK').eq(pid),
                IndexName='GSI1'
            )
            try:
                g_id = response['Items'][0]['PK'] # If it is there we should only have one
            except:
                no_global.append(pid)

        # Create if we didn't find one
        if g_id is None: g_id = str(uuid.uuid4())

        # Update any local ids that weren't associated to the global
        for pid in no_global:
            response = self.table.put_item(
                Item={
                    'PK': g_id,
                    'SK': pid
                }
            )
        return g_id

    def put_successful_message(self,
                               global_id,
                               sort_key,
                               staging_key,
                               msg_id):
        self.table.put_item(
            Item={
            'PK': global_id,
            "SK": sort_key,
            's3_key': staging_key,
            'provided_id': msg_id,
            'type': 'MessageSuccessful',
            }
        )

    def put_failed_message(self,
                           error_key,
                           message_type,
                           msg_id):
        self.table.put_item(
            Item={
                'PK': error_key,
                'SK': datetime.now().isoformat(),
                'type': message_type,
                'provided_id': msg_id,
            }
        )

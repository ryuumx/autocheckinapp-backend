import boto3
import os
import logging
import json


BUCKET = os.environ['BUCKETNAME']
COLLECTION_ID = os.environ['REKOGNITIONCOLLECTION']
DYNAMODB_TABLE = os.environ['DYNAMODBTABLENAME']
LOG_LEVEL = logging.INFO

dynamodb = boto3.client('dynamodb')
s3 = boto3.client('s3')
rekognition = boto3.client('rekognition')

logger = logging.getLogger()
logger.setLevel(LOG_LEVEL)


def lambda_handler(event, context):
    """Sample pure Lambda function

    Parameters
    ----------
    event: dict, required
        API Gateway Lambda Proxy Input Format
        Event doc: https://docs.aws.amazon.com/apigateway/latest/developerguide/set-up-lambda-proxy-integrations.html#api-gateway-simple-proxy-for-lambda-input-format
    context: object, required
        Lambda Context runtime methods and attributes
        Context doc: https://docs.aws.amazon.com/lambda/latest/dg/python-context-object.html

    Returns
    ------
    API Gateway Lambda Proxy Output Format: dict
        Return doc: https://docs.aws.amazon.com/apigateway/latest/developerguide/set-up-lambda-proxy-integrations.html
    """
    logger.info("Parsing request data.")
    data = json.loads(event['body'])
    
    image = data['image']
    firstname = data['firstname']
    lastname = data['lastname']
    email = data['email']
    if 'company' in data:
        company = data['company']
    else:
        company = ''
    
    try:
        logger.info("Indexing faces.")
        response = rekognition.index_faces(
            Image={
                "S3Object": {
                    "Bucket": BUCKET,
                    "Name": image
                }
            },
            CollectionId=COLLECTION_ID
        )
    
        logger.info("Reading results.")
        if response['ResponseMetadata']['HTTPStatusCode'] != 200 or len(response['FaceRecords']) == 0:
            raise Exception("Fail to register a face to Rekognition.")
        
        faceId = response['FaceRecords'][0]['Face']['FaceId']
        logger.info("Recorded faceId: {}".format(faceId))
            
    except Exception as e:
        logger.exception(e)
        return {
                "statusCode": 500,
                "headers": {
                    "Access-Control-Allow-Headers": "*",
                    "Access-Control-Allow-Methods": "POST",
                    "Access-Control-Allow-Origin": "*",
                    "Content-Type": "application/json"
                },
                "body": json.dumps({
                    "message": "Error: {}".format(e),
                }),
            }
    
    try:
        logger.info("Putting information to DynamoDB table.")
        response = dynamodb.put_item(
            TableName=DYNAMODB_TABLE,
            Item={
                'FaceId': {'S': faceId},
                'FirstName': {'S': firstname},
                'LastName': {'S': lastname},
                'Company': {'S': company},
                'Email': {'S': email}
            }
        )
        
        logger.info("Reading results.")
        if response['ResponseMetadata']['HTTPStatusCode'] != 200:
            raise Exception("Fail to put information to DynamoDB table.")
    
    except Exception as e:
        logger.exception(e)
        rekognition.delete_faces(
                CollectionId=COLLECTION_ID,
                FaceIds=[faceId]
            )
        return {
                "statusCode": 500,
                "headers": {
                    "Access-Control-Allow-Headers": "*",
                    "Access-Control-Allow-Methods": "POST",
                    "Access-Control-Allow-Origin": "*",
                    "Content-Type": "application/json"
                },
                "body": json.dumps({
                    "message": "Error: {}".format(e),
                }),
            }
    
    logger.info("All information recorded.")

    return {
        "statusCode": 200,
        "headers": {
            "Access-Control-Allow-Headers": "*",
            "Access-Control-Allow-Methods": "POST",
            "Access-Control-Allow-Origin": "*",
            "Content-Type": "application/json"
        },
        "body": json.dumps({
            "message": "Success. Information recorded",
        }),
    }

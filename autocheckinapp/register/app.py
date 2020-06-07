from botocore.exceptions import ClientError
import boto3
import os
import logging
import json


BUCKET = os.environ['BUCKETNAME']
COLLECTION_ID = os.environ['REKOGNITIONCOLLECTION']
LOG_LEVEL = logging.INFO

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
    
    logger.info("Getting results.")
    if response['ResponseMetadata']['HTTPStatusCode'] != 200 or len(response['FaceRecords']) == 0:
        return {
            "statusCode": 500,
            "body": json.dumps({
                "message": "Fail to register a face to Rekognition.",
            }),
        }
    
    faceId = response['FaceRecords'][0]['Face']['FaceId']
    logger.info("Recorded faceId: {}".format(faceId))

    return {
        "statusCode": 200,
        "body": json.dumps({
            "message": "Success. Face recorded",
        }),
    }

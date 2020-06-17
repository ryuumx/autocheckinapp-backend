from botocore.exceptions import ClientError
import boto3
import os
import logging
import json


BUCKET = os.environ['BUCKETNAME']
COLLECTION_ID = os.environ['REKOGNITIONCOLLECTION']
DYNAMODB_TABLE = os.environ['DYNAMODBTABLENAME']
FACE_MATCH_THRESHOLD = int(os.environ['REKOGNITIONFACEMATCHTHRESHOLD'])
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
    
    try:
        logger.info("Searching faces.")
        response = rekognition.search_faces_by_image(
            Image={
                "S3Object": {
                    "Bucket": BUCKET,
                    "Name": image
                }
            },
            CollectionId=COLLECTION_ID,
            FaceMatchThreshold=FACE_MATCH_THRESHOLD,
            MaxFaces=1
        )
    
        logger.info("Reading results.")
        if response['ResponseMetadata']['HTTPStatusCode'] != 200 or len(response['FaceMatches']) == 0:
            raise Exception("Fail to find similar face.")
        
        faceFound = response['FaceMatches'][0]['Face']
        faceId = faceFound['FaceId']
        confidence = faceFound['Confidence']
        logger.info("Found faceId: {}. Confidence level: {}".format(faceId, confidence))
            
    except Exception as e:
        return {
                "statusCode": 500,
                "body": json.dumps({
                    "message": "Error: {}".format(e),
                }),
            }
    
    try:
        logger.info("Getting information from DynamoDB")
        response = dynamodb.get_item(
            TableName=DYNAMODB_TABLE,
            Key={'FaceId': {'S': faceId}}
        )
        
        logger.info("Reading results.")
        if response['ResponseMetadata']['HTTPStatusCode'] != 200:
            raise Exception("Fail to find information from DynamoDB table.")
        
        firstname = response['Item']['FirstName']['S']
        lastname = response['Item']['LastName']['S']
        company = response['Item']['Company']['S']
        email = response['Item']['Email']['S']
            
    except Exception as e:
        return {
                "statusCode": 500,
                "body": json.dumps({
                    "message": "Error: {}".format(e),
                }),
            }

    return {
        "statusCode": 200,
        "body": json.dumps({
            "message": "Succeed to find similar face.",
            "faceId": faceId,
            "confidence": confidence,
            "firstname": firstname,
            "lastname": lastname,
            "company": company,
            "email": email
        }),
    }

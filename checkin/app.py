import boto3
import os
import logging
import json


# Delaring global variables
BUCKET = os.environ['BUCKETNAME']
COLLECTION_ID = os.environ['REKOGNITIONCOLLECTION']
DYNAMODB_TABLE = os.environ['DYNAMODBTABLENAME']
FACE_MATCH_THRESHOLD = int(os.environ['REKOGNITIONFACEMATCHTHRESHOLD'])
LOG_LEVEL = logging.INFO

# Initiating services clients
dynamodb = boto3.client('dynamodb')
s3 = boto3.client('s3')
rekognition = boto3.client('rekognition')

# Initiating logger
logger = logging.getLogger()
logger.setLevel(LOG_LEVEL)

# Main function
def lambda_handler(event, context):

    try:
        # Getting data from request
        logger.info("Parsing request data.")
        data = json.loads(event['body'])
        image = data['image']
    
        # Matching face from Rekognition
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
        # Handling Rekognition errors
        logger.info("Reading results.")
        if response['ResponseMetadata']['HTTPStatusCode'] != 200 or len(response['FaceMatches']) == 0:
            raise Exception("Fail to find similar face.")
        
        # Storing face info
        faceFound = response['FaceMatches'][0]
        faceId = faceFound['Face']['FaceId']
        confidence = faceFound['Similarity']
        logger.info("Found faceId: {}. Confidence level: {}".format(faceId, confidence))
        
        # Mapping info from Dynamo
        logger.info("Getting information from DynamoDB")
        response = dynamodb.get_item(
            TableName=DYNAMODB_TABLE,
            Key={'faceId': {'S': faceId}}
        )
        # Handling Dynamo errors
        logger.info("Reading results.")
        if response['ResponseMetadata']['HTTPStatusCode'] != 200:
            raise Exception("Fail to find information from DynamoDB table.")
        
        # Storing user info
        name = response['Item']['name']['S']
        email = response['Item']['email']['S']
        
        # Returing info
        logger.info("Finish recording all information")
        return {
            "statusCode": 200,
            "headers": {
                "Access-Control-Allow-Origin": "*",
                "Content-Type": "application/json"
            },
            "body": json.dumps({
                "message": "Succeed to find similar face.",
                "faceId": faceId,
                "confidence": confidence,
                "name": name,
                "email": email
            }),
        }
            
    except Exception as e:
        logger.exception(e)
        # Returning error message
        return {
                "statusCode": 500,
                "headers": {
                    "Access-Control-Allow-Origin": "*",
                    "Content-Type": "application/json"
                },
                "body": json.dumps({
                    "message": "Error: {}".format(e),
                }),
            }
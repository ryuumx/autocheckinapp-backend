import boto3
import os
import logging
import json

# Delaring global variables
BUCKET = os.environ['BUCKETNAME']
COLLECTION_ID = os.environ['REKOGNITIONCOLLECTION']
DYNAMODB_TABLE = os.environ['DYNAMODBTABLENAME']
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
    # Initiating recorded info keepers
    recordedFaces = []
    recordedItems = []
    
    try:
        # Getting data from request
        logger.info("Parsing request data.")
        data = json.loads(event['body'])
        images = data['images']
        name = data['name']
        email = data['email']
    
        # Looping images - adding info
        logger.info("Indexing faces.")
        for eachImage in images:
            # Adding face to Rekognition
            logger.info("Image: {}".format(eachImage))
            response = rekognition.index_faces(
                Image={
                    "S3Object": {
                        "Bucket": BUCKET,
                        "Name": eachImage
                    }
                },
                CollectionId=COLLECTION_ID
            )
            # Handling Rekognition errors
            if response['ResponseMetadata']['HTTPStatusCode'] != 200 or len(response['FaceRecords']) == 0:
                raise Exception("Fail to register a face to Rekognition.")
        
            # Storing face info
            faceId = response['FaceRecords'][0]['Face']['FaceId']
            recordedFaces.append(faceId)
            logger.info("Recorded faceId: {}".format(faceId))
            
            # Adding info to Dynamo
            response2 = dynamodb.put_item(
                TableName=DYNAMODB_TABLE,
                Item={
                    'faceId': {'S': faceId},
                    'name': {'S': name},
                    'email': {'S': email}
                }
            )
            # Handling Dynamo errors
            if response2['ResponseMetadata']['HTTPStatusCode'] != 200:
                raise Exception("Fail to put record to DynamoDB.")
            
            # Storing record info
            recordedItems.append(faceId)
            
        # Returning success message
        logger.info("Finish recording all information")
        return {
            "statusCode": 200,
            "headers": {
                "Access-Control-Allow-Origin": "*",
                "Content-Type": "application/json"
            },
            "body": json.dumps({
                "message": "Success. Information recorded",
            }),
        }
            
    except Exception as e:
        logger.exception(e)
        
        # Rolling back faces in Rekognition
        if len(recordedFaces) != 0:
            logger.info("Rolling back recorded faces.")
            rekognition.delete_faces(
                CollectionId=COLLECTION_ID,
                FaceIds=recordedFaces
            )
        
        # Rolling back info in Dynamo
        if len(recordedItems) != 0:
            logger.info("Rolling back recorded items.")
            for eachItem in recordedItems:
                dynamodb.delete_item(
                    TableName=DYNAMODB_TABLE,
                    Key={
                        'faceId': {'S': eachItem}
                    }
                )
        
        # Returning error
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
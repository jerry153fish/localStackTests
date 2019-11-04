import sys, os, random, string
from troposphere import Base64, FindInMap, GetAtt, Join, Output, Select, GetAZs
from  troposphere.kinesis import Stream
from troposphere.s3 import Bucket, PublicRead
from troposphere.iam import Policy, Role

from argparse import ArgumentParser
import boto3

project_name = "task1-kinsis"

def create_kinesis_stream_resource( name ):
    """Create Kinsis Stream resource
    
    Arguments:
        name {[String]} -- [ Name ]
    
    Returns:
        [troposphere.resource] -- [ Steam resource ]
    """
    return Stream(
        name,
        ShardCount=1,
        Tags=Tags(
            Application=ref_stack_id,
            Name=Join("", [ref_stack_name, "-Kinsis-Stream"])
        )
    )

def create_s3_bucket_resource( name ):
    """Create S3 Bucket resource
    
    Arguments:
        name {[String]} -- [ Name ]
    
    Returns:
        [troposphere.resource] -- [ S3 bucket resource ]
    """
    return Bucket(
        name,
        AccessControl=PublicRead,
        Tags=Tags(
            Application=ref_stack_id,
            Name=Join("", [ref_stack_name, "-s3-bucket"])
        )
    )

def create_delivery_role( name ):
    return Role(
        name,
        AssumeRolePolicyDocument={
            "Version": "2012-10-17",
            "Statement": [{
                "Sid": "",
                "Effect": "Allow",
                "Principal": {
                    "Service": "localhost:4573"
                },
                "Action": "sts:AssumeRole",
                "Condition": {
                    "StringEquals": {
                        "sts:ExternalId": {"Ref":"AWS::AccountId"}
                    }
                }
            }]
        }
    )

def create_delivery_Policy( name ):
    return Role(
        name,
        AssumeRolePolicyDocument={
            "Version": "2012-10-17",
            "Statement": [{
                "Sid": "",
                "Effect": "Allow",
                "Principal": {
                    "Service": "localhost:4573"
                },
                "Action": "sts:AssumeRole",
                "Condition": {
                    "StringEquals": {
                        "sts:ExternalId": {"Ref":"AWS::AccountId"}
                    }
                }
            }]
        }
    )

def create_kinesis_stack( project_name ):
    return 




s3client = boto3.client('s3', endpoint_url='http://localhost:4572')

# s3client.create_bucket(Bucket='mybucket', CreateBucketConfiguration={
#     'LocationConstraint': 'us-west-1'})

print( s3client.list_buckets() )
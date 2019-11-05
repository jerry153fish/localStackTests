import sys, os, random, string
from troposphere import Base64, FindInMap, GetAtt, Join, Output, Select, GetAZs
from troposphere import Parameter, Ref, Tags, Template
import troposphere.kinesis as kinesis
from troposphere.s3 import Bucket, PublicRead
from troposphere.iam import PolicyType, Role
from troposphere.firehose import (
    BufferingHints,
    KinesisStreamSourceConfiguration,
    CopyCommand,
    DeliveryStream,
    S3DestinationConfiguration
)

from argparse import ArgumentParser
import boto3
import time

project_name = "task1Kinsis"

ref_stack_id = Ref('AWS::StackId')
ref_stack_name = Ref('AWS::StackName')

def wait_until(predicate, timeout, period=0.25, *args, **kwargs):
  mustend = time.time() + timeout
  while time.time() < mustend:
    if predicate(*args, **kwargs): return True
    time.sleep(period)
  return False

def create_kinesis_stream_resource( name ):
    """Create Kinsis Stream resource
    
    Arguments:
        name {[String]} -- [ Name ]
    
    Returns:
        [troposphere.resource] -- [ Steam resource ]
    """
    return kinesis.Stream(
        name,
        ShardCount=1
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

def create_role_resource( name ):
    return Role(
        name,
        AssumeRolePolicyDocument={
            "Version": "2012-10-17",
            "Statement": [{
                "Sid": "",
                "Effect": "Allow",
                "Principal": "*", # TODO: Do not use wildcard
                "Action": "sts:AssumeRole",
                "Condition": {
                    "StringEquals": {
                        "sts:ExternalId": Ref("AWS::AccountId")
                    }
                }
            }]
        },
        Tags=Tags(
            Application=ref_stack_id,
            Name=Join("", [ref_stack_name, "-Kinsis-Stream"])
        )
    )

def create_root_Policy( name, roles ):
    return PolicyType(
        name,
        PolicyName=name+"RootPolicy",
        PolicyDocument={
            "Version": "2012-10-17",
            "Statement": [{
                "Effect": "Allow",
                "Action": "*",
                 "Resource": "*"
            }],
        },
        Roles=roles
    )

# def create_firehose_delivery_stream_resource( name, depends, kinesisStream, s3bucket, role ):
#     return DeliveryStream(
#         name,
#         DeliveryStreamName=name+'DeliveryStream',
#         S3DestinationConfiguration=S3DestinationConfiguration(
#             BucketARN="aa"
#             BufferingHints=BufferingHints(

#             ),
#             CompressionFormat="UNCOMPRESSED",
#             Prefix="firehose/",
#             RoleARN=GetAtt(role, "Arn"),
#         ),
#         KinesisStreamSourceConfiguration=KinesisStreamSourceConfiguration(

#         )
#     )

def create_kinesis_stack( project_name ):
    t = Template()

    t.add_version('2010-09-09')

    t.set_description("LocalStackTests Task one cloud formation template of S3 - kinesisStream and firehose")

    kinesisStream = create_kinesis_stream_resource( project_name + "kinesisStream" )

    bucketName=project_name + "s3bucketStream"
    s3bucket = create_s3_bucket_resource( project_name + "s3bucketStream")
    deliveryRole = create_role_resource( project_name+"deliveryRole")
    rootPolicy = create_root_Policy( project_name + "rootPolicy", [ Ref(deliveryRole)] )

    t.add_resource( s3bucket )
    t.add_resource( rootPolicy )
    t.add_resource( deliveryRole )
    # t.add_resource( kinesisStream )

    print( t.to_yaml() )

    return t

def wait_list_resource( listResource, timeout, period=1, *args, **kwargs ):
    mustend = time.time() + timeout
    while time.time() < mustend:
        try:
            listResource( *args, **kwargs )
            return True
        except Exception as e:
            # TODO: dig into message to improve wait check
            pass
        time.sleep(period)
    return False


s3Client = boto3.client('s3', endpoint_url='http://localhost:4572')
cloudformationClient=boto3.client('cloudformation', endpoint_url='http://localhost:4581')
kinesisClient = boto3.client('kinesis', endpoint_url='http://localhost:4568')

# s3client.create_bucket(Bucket='mybucket', CreateBucketConfiguration={
#     'LocationConstraint': 'us-west-1'})
# kinesisClient.delete_stream(  StreamName='testStream' )
# kinesisClient.create_stream(
#     StreamName='testStream',
#     ShardCount=1
# )

# print( s3Client.list_buckets() )


# test( kinesisClient.describe_stream, StreamName='testStream' )

kinesisReady=wait_list_resource( kinesisClient.describe_stream, 5, StreamName='testStream' )

# print( kinesisRes )
# task1_template = create_kinesis_stack( project_name )

# # task1_stack=cloudformationclient.create_stack(
# #         StackName=project_name,
# #         TemplateBody=task1_template.to_yaml()
# #     )

# deleteRes = cloudformationClient.delete_stack( StackName=project_name )
# # print( task1_stack["StackId"] )

# print( deleteRes )

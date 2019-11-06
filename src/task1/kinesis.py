import sys, os, random, string
from troposphere import Base64, FindInMap, GetAtt, Join, Output, Select, GetAZs
from troposphere import Parameter, Ref, Tags, Template
from troposphere.kinesis import Stream
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
from src.task1.kinesisProducer import KinesisProducer
from src.utils import (
    create_kinesis_stream_resource,
    create_s3_bucket_resource,
    create_role_resource,
    create_root_Policy,
    create_firehose_delivery_stream_resource,
    wait_resource,
    check_s3_bucket_has_content,
    wait_for_s3_bucket_has_content
)

def create_kinesis_cloudformation_stack( projectName, kinesisStreamArn ):
    """[create or get the cloudformation stack based on the project name 
        TODO: for somehow kinesisStream cloudformation snippet fails on xml parse
        have to create it outside of stack
    ]
    
    Arguments:
        projectName {[String]} -- [ project name ]
        kinesisStreamArn {[String]} -- [ kinesisStream Arn ]
    
    Raises:
        Exception: [ timeout or unexpected exception ]
    
    Returns:
        [ dict ] -- [ describe stack information ]
    """

    cloudformationClient=boto3.client('cloudformation', endpoint_url='http://localhost:4581')

    t = Template()

    t.set_version('2010-09-09')

    t.set_description("LocalStackTests Task one cloud formation template of S3 - kinesisStream and firehose")

    # kinesisStream = create_kinesis_stream_resource( projectName + "kinesisStream" )

    bucketName=projectName + "s3bucketStream"
    s3bucket = create_s3_bucket_resource( projectName + "s3bucketStream")
    deliveryRole = create_role_resource( projectName+"deliveryRole")
    rootPolicy = create_root_Policy( projectName + "rootPolicy", [ Ref(deliveryRole)] )
    fireHoseDelivery = create_firehose_delivery_stream_resource( projectName + "fireHoseDelivery", rootPolicy, kinesisStreamArn, s3bucket, deliveryRole )

    t.add_resource( s3bucket )
    t.add_resource( rootPolicy )
    t.add_resource( deliveryRole )
    # t.add_resource( kinesisStream )
    t.add_resource( fireHoseDelivery )

    # print( t.to_yaml() )
    t.add_output(Output(
        "BucketName",
        Value=Ref(s3bucket),
        Description="Name of S3 bucket"
    ))

    # t.add_output(Output(
    #     "StreamName",
    #     Value=Ref(kinesisStream),
    #     Description="Name of kinesis Stream"
    # ))

    stackName=projectName+'Task1'

    try:
        task1_stack=cloudformationClient.create_stack(
            StackName=stackName,
            TemplateBody=t.to_yaml()
        )
    except Exception as e:
        # TODO: check other exceptions
        pass

    stackReady=wait_resource( cloudformationClient.describe_stacks, check_cloudformation_stack_complete, 10, StackName=stackName )

    if stackReady:
        res = cloudformationClient.describe_stacks( StackName=stackName )
        return res['Stacks'][0]
    else:
        raise Exception("Fails to get recently created stream, try to wait for more time")

def check_kinesis_stream_ready( kinesisResponse ):
    """[ helper function for checking kinesis resource activate ]
    
    Arguments:
        kinesisResponse {[kinesis Response]} -- [ Response of aws describe_stream ]
    
    Returns:
        [ Boolean ] -- [ is kinesis ready ]
    """
    description = kinesisResponse.get('StreamDescription')
    status = description.get('StreamStatus')

    return status == "ACTIVE"

def check_cloudformation_stack_complete( cloudformationRespose ):
    """[ cloudformation stack complete checker ]
    
    Arguments:
        cloudformationRespose {[ dict ]} -- [ cloudformation describe stack response ]
    
    Returns:
        [Boolean] -- [ is cloudformation complete ]
    """

    stacks = cloudformationRespose.get('Stacks')
    status = stacks[0].get('StackStatus')
    return status == "CREATE_COMPLETE"

def create_kinesis_stream( name ):
    """[ create or get kinesis stream using boto3 by name ]
    
    Arguments:
        name {[ String ]} -- [ name ]
    
    Raises:
        Exception: [ timeout or unexpected exception ]
    
    Returns:
        [ dict ] -- [ StreamDescription ]
    """
    kinesisClient = boto3.client('kinesis', endpoint_url='http://localhost:4568')

    streamName = name+"KinesisStream"
    try:
        kinesisClient.create_stream(
            StreamName=streamName,
            ShardCount=1
        )
    except Exception as e:
        # TODO: check other exceptions
        pass

    kinesisReady=wait_resource( kinesisClient.describe_stream, check_kinesis_stream_ready, 10, StreamName=streamName )

    if kinesisReady:
        res = kinesisClient.describe_stream( StreamName=streamName )
        return res['StreamDescription']
    else:
        raise Exception("Fails to get recently created stream, try to wait for more time")

def task1_kinesis( projectName , totalTimes=10 ):
    """[ 
            tesk1 scripts 1. provision kinesis 2. put random data to it 
            TODO: firehose seems not working, as s3 have no content
    ]

    Arguments:
        projectName {[type]} -- [description]
    """

    kinesis = create_kinesis_stream( projectName )
    task1_stack=create_kinesis_cloudformation_stack( projectName, kinesis['StreamARN'])
    # print( task1_stack )
    outputs = task1_stack.get("Outputs")
    bucketName = outputs[0].get("OutputValue")
    producer = KinesisProducer(kinesis['StreamName'], 0.2, totalTimes=totalTimes )
    producer.run()

    # wait_for_s3_bucket_has_content( bucketName ) # FIXME: #4 fireHoseDelivery not working

def clean_up_kinesis( name ):
    """[ Clean up kinesis stream resource ]
    
    Arguments:
        name {[type]} -- [description]
    """
    kinesisClient = boto3.client('kinesis', endpoint_url='http://localhost:4568')

    streamName = name+"KinesisStream"
    try:
        kinesisClient.delete_stream(
            StreamName=streamName,
            ShardCount=1
        )
    except Exception as e:
        # TODO: check other exceptions
        pass



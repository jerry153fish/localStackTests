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
from KinesisProducer import KinesisProducer

project_name = "task1Kinsis"
ref_stack_id = Ref('AWS::StackId')
ref_stack_name = Ref('AWS::StackName')

def create_kinesis_stream_resource( name ):
    """Create Kinsis Stream resource
    
    Arguments:
        name {[String]} -- [ Name ]
    
    Returns:
        [troposphere.resource] -- [ Steam resource ]
    """
    return Stream(
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
    """[ create role resource TODO: should not use super root in production environment ]
    
    Arguments:
        name {[String]} -- [name of resource]
    
    Returns:
        [troposphere.resource] -- [ Role resource ]
    """
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
    """[ create policy resource TODO: should not use super root in production environment ]
    
    Arguments:
        name {[String]} -- [name of resource]
        roles {[String]} -- [Ref(role1), ...]
    
    Returns:
        [troposphere.resource] -- [ Policy resource ]
    """
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

def create_firehose_delivery_stream_resource( name, depends, kinesisStreamARN, s3bucket, role ):
    """[create firehose delievery stream resource which use s3 bucket as destination and kinesis stream as producer ]
    
    Arguments:
        name {[String]} -- [ name ]
        depends {[troposphere.resource]} -- [ depend resource ]
        kinesisStreamARN {[String]} -- [ arn of kinesisStream ]
        s3bucket {[troposphere.resource]} -- [ s3 bucket resource ]
        role {[troposphere.resource]} -- [ role resource ]
    
    Returns:
        [troposphere.resource] -- [ Firehose delivery resource ]
    """
    return DeliveryStream(
        name,
        DependsOn=depends,
        DeliveryStreamName=name+'DeliveryStream',
        S3DestinationConfiguration=S3DestinationConfiguration(
            BucketARN=GetAtt(s3bucket, "Arn"),
            BufferingHints=BufferingHints(
                IntervalInSeconds=60,
                SizeInMBs=50
            ),
            CompressionFormat="UNCOMPRESSED",
            Prefix="firehose/",
            RoleARN=GetAtt(role, "Arn"),
        ),
        KinesisStreamSourceConfiguration=KinesisStreamSourceConfiguration(
            KinesisStreamARN=kinesisStreamARN,
            RoleARN=GetAtt(role, "Arn")
        )
    )

def create_kinesis_cloudformation_stack( project_name, kinesisStreamArn ):
    """[create or get the cloudformation stack based on the project name 
        TODO: for somehow kinesisStream cloudformation snippet fails on xml parse
        have to create it outside of stack
    ]
    
    Arguments:
        project_name {[String]} -- [ project name ]
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

    # kinesisStream = create_kinesis_stream_resource( project_name + "kinesisStream" )

    bucketName=project_name + "s3bucketStream"
    s3bucket = create_s3_bucket_resource( project_name + "s3bucketStream")
    deliveryRole = create_role_resource( project_name+"deliveryRole")
    rootPolicy = create_root_Policy( project_name + "rootPolicy", [ Ref(deliveryRole)] )
    fireHoseDelivery = create_firehose_delivery_stream_resource( project_name + "fireHoseDelivery", rootPolicy, kinesisStreamArn, s3bucket, deliveryRole )

    t.add_resource( s3bucket )
    t.add_resource( rootPolicy )
    t.add_resource( deliveryRole )
    # t.add_resource( kinesisStream )
    t.add_resource( fireHoseDelivery )

    # print( t.to_yaml() )

    try:
        task1_stack=cloudformationClient.create_stack(
            StackName=project_name,
            TemplateBody=t.to_yaml()
        )
    except Exception as e:
        # TODO: check other exceptions
        pass

    stackReady=wait_list_resource( cloudformationClient.describe_stacks, check_cloudformation_stack_complete, 10, StackName=project_name )

    if stackReady:
        res = cloudformationClient.describe_stacks( StackName=project_name )
        return res['Stacks'][0]
    else:
        raise Exception("Fails to get recently created stream, try to wait for more time")

def wait_list_resource( listResource, checkcallback, timeout, period=1, *args, **kwargs ):
    """[ wait function for list or describe boto3 functions]
    
    Arguments:
        listResource {[ function ]} -- [ list or describe function ]
        checkcallback {[ function ]} -- [ status check function ]
        timeout {[ int ]} -- [ seconds of wait time ]
    
    Keyword Arguments:
        period {int} -- [ wait period in seconds] (default: {1})
    
    Returns:
        [Boolean -- [ is ready ? ]
    """
    mustend = time.time() + timeout
    while time.time() < mustend:
        try:
            res = listResource( *args, **kwargs )
            if checkcallback( res ) : return True
        except Exception as e:
            # TODO: dig into message to improve wait check
            # print( e )
            pass
        time.sleep(period)
    return False

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

    try:
        kinesisClient.create_stream(
            StreamName=name,
            ShardCount=1
        )
    except Exception as e:
        # TODO: check other exceptions
        pass

    kinesisReady=wait_list_resource( kinesisClient.describe_stream, check_kinesis_stream_ready, 10, StreamName=name )

    if kinesisReady:
        res = kinesisClient.describe_stream( StreamName=name )
        return res['StreamDescription']
    else:
        raise Exception("Fails to get recently created stream, try to wait for more time")

def task1_kinesis():
    pass
# def 
# s3Client = boto3.client('s3', endpoint_url='http://localhost:4572')
# cloudformationClient=boto3.client('cloudformation', endpoint_url='http://localhost:4581')
# kinesisClient = boto3.client('kinesis', endpoint_url='http://localhost:4568')

# s3client.create_bucket(Bucket='mybucket', CreateBucketConfiguration={
#     'LocationConstraint': 'us-west-1'})
# kinesisClient.delete_stream(  StreamName='testStream1' )
# kinesisClient.create_stream(
#     StreamName='testStream',
#     ShardCount=1
# )


# kinesis = create_kinesis_stream( "testStream1" )



# print( kinesis )


# task1_stack=create_kinesis_cloudformation_stack( project_name, kinesis['StreamARN'])

# print(task1_stack)



# deleteRes = cloudformationClient.delete_stack( StackName=project_name )
# # print( task1_stack["StackId"] )

# print( deleteRes )

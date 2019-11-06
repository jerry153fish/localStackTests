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

def random_alphanumeric(len):
    """Generate random alphanumeric string based on len
    
    Arguments:
        pass_len {[number]} -- [length of string]
    
    Returns:
        [string] -- [ fix length random alphanumeric ]
    """
    symbols = string.printable.strip()
    return ''.join(random.choice(string.ascii_uppercase + string.ascii_lowercase + string.digits) for _ in range(len))

def get_or_create_kinesis_stream_resource( name ):
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
            Application=Ref('AWS::StackId'),
            Name=Join("", [Ref('AWS::StackName'), "-s3-bucket"])
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
            Application=Ref('AWS::StackId'),
            Name=Join("", [Ref('AWS::StackName'), "-supper-role"])
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

def create_security_group_rule( ipProtocol, fromPort, toPort, cidrIp ):
    """[ create security group rule ]
    
    Arguments:
        ipProtocol {[String]} -- [ ip protocol ]
        fromPort {[Number]} -- [ start port]
        toPort {[ Number]} -- [ end port ]
        cidrIp {[ String ]} -- [ allow IP cidr ]
    
    Returns:
        [ troposphere.Object ] -- [ SecurityGroupRule ]
    """
    return SecurityGroupRule(
        IpProtocol=ipProtocol,
        FromPort=fromPort,
        ToPort=toPort,
        CidrIp=cidrIp,
    )

def create_security_group_resource( name, securityGroupIngress, description ):
    """[ create simple security group resource ]
    
    Arguments:
        name {[String]} -- [ name ]
        securityGroupIngress {[List<SecurityGroupRule>]} -- [ list of security group rules ]
        description {[String]} -- [description]
    
    Returns:
        [troposphere.resource] -- [ security group resource ]
    """
    return SecurityGroup(
    name,
    SecurityGroupIngress=securityGroupIngress, # must be array of security rules
    GroupDescription=description,
    Tags=Tags(
        Application=Ref('AWS::StackId'),
        Name=Join("", [Ref('AWS::StackName'), name])
    )   
)

def wait_resource( listResource, checkcallback, timeout, period=1, *args, **kwargs ):
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

def check_s3_bucket_has_content( response ):
    """ check s3 bucket has content
    
    Returns:
        [Boolean] -- [ has content ? ]
    """
    return response.get('KeyCount') > 0

def wait_for_s3_bucket_has_content( bucket ):
    """[ wait for s3 bucket has content]
    
    Raises:
        Exception: [ Stack setup error ]
    """
    s3Client = boto3.client('s3', endpoint_url='http://localhost:4572', region_name='us-west-2')
    res = s3Client.list_objects_v2(
        Bucket=bucket
    )

    hasContent=wait_resource( s3Client.list_objects_v2, check_s3_bucket_has_content, 10, Bucket=bucket )

    if hasContent:
        print("Stack works")
    else:
        raise Exception("Stack fails, extend time or errors existed in the stack")

def clean_up_cloudformation_stack( stackName ):
    """[ clean up cloudformation stack ]
    
    Arguments:
        stackName {[String]} -- [ stack name ]
    """
    try:
        task1_stack=cloudformationClient.delete_stack(
            StackName=stackName
        )
    except Exception as e:
        # TODO: check other exceptions
        pass
import sys, os, random, string, boto3
from troposphere import Base64, FindInMap, GetAtt, Join, Output, Select, GetAZs
from troposphere import Parameter, Ref, Tags, Template
from troposphere.autoscaling import ( 
    LaunchConfiguration,
    AutoScalingGroup
)
from troposphere.policies import (
    AutoScalingReplacingUpdate, AutoScalingRollingUpdate, UpdatePolicy
)

from src.utils import (
    wait_resource,
    create_security_group_rule,
    create_security_group_resource
) 

MOCK_KEY_PAIR_NAME="MOCK_KEY_PAIR_NAME" # assume we key pair 
MOCK_IMAGE_ID="MOCK_IMAGE_ID" # assume we already create an image from existing instance and have init scipts run on reboot

zone1 = Select( 0, GetAZs( Ref('AWS::Region')) )
zone2 = Select( 1, GetAZs( Ref('AWS::Region')) )

def create_launch_configuration_resource( name, securityGroups ):
    """[create simple]
    
    Arguments:
        name {[type]} -- [description]
        securityGroups {[List<String>]} -- [ list of security refs ]
    
    Returns:
        [ troposphere.resource ] -- [ LaunchConfiguration ]
    """
    return LaunchConfiguration(
        name,
        ImageId=MOCK_IMAGE_ID,
        KeyName=MOCK_KEY_PAIR_NAME,
        InstanceType="m1.small",
        SecurityGroups=securityGroups,
        Tags=Tags(
            Application=Ref('AWS::StackId'),
            Name=Join("", [Ref('AWS::StackName'), "-LaunchConfiguration"])
        )
    )

def create_autoscaling_resource( name, launchConfig ):
    """[ create simple autoscaling resource ]
    
    Arguments:
        name {[String]} -- [ name ]
        launchConfig {[LaunchConfiguration]} -- [description]
    
    Returns:
        [ troposphere.resource ] -- [ AutoScalingGroup ]
    """
    return AutoScalingGroup(
        name+"AutoScalingGroup",
        DesiredCapacity=10,
        AutoScalingGroupName=name,
        LaunchConfigurationName=Ref(launchConfig),
        MinSize=9,
        MaxSize=10,
        AvailabilityZones=[Ref(zone1), Ref(zone2)],
        HealthCheckType="EC2",
        UpdatePolicy=UpdatePolicy(
            AutoScalingReplacingUpdate=AutoScalingReplacingUpdate(
                WillReplace=True,
            ),
            AutoScalingRollingUpdate=AutoScalingRollingUpdate(
                PauseTime='PT5M',
                MinInstancesInService="1",
                MaxBatchSize='1',
                WaitOnResourceSignals=True
            )
        ),
        Tags=Tags(
            Application=Ref('AWS::StackId')
        )
    )

def create_autoscaling_stack( projectName ):

    cloudformationClient=boto3.client('cloudformation', endpoint_url='http://localhost:4581', region_name='us-west-2' )

    t = Template()

    t.set_version('2010-09-09')

    t.set_description("LocalStackTests Task two cloud formation template of AutoScalingGroup ")

    ssh_rule = create_security_group_rule( "tcp", "22", "22", "0.0.0.0/0" )
    http_rule = create_security_group_rule( "tcp", "80", "80", "0.0.0.0/0" ) # assume we are ruing on 80 port 80
    ec2SecurityGroup = create_security_group_resource( projectName+"EC2SecurityGroup", [ ssh_rule, http_rule ], "EC2 Security Group" )

    launchConfigName=projectName + "LaunchConfiguration"

    launchConfig = create_launch_configuration_resource( launchConfigName, [ Ref(ec2SecurityGroup) ] )

    autoscaling = create_autoscaling_resource( projectName, launchConfig )
 
    t.add_resource( ec2SecurityGroup )
    t.add_resource( launchConfig )
    t.add_resource( autoscaling )

    stackName=projectName+'Task2'

    try:
        task2_stack=cloudformationClient.create_stack(
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
        raise Exception("Fails to get recently created stack, try to wait for more time")

def check_autoscaling_instance_health( response ):
    instances = response.get("AutoScalingInstances")
    if len( instances ) == 0:
        raise Exception("unexpected response from describe autoscaling instances expect at least one instance") 
    instance = instances[0]

    return instance.get(HealthStatus) == "HEALTHY"

def rebuild_instance_from_auto_scaling_group( instanceId, autoScalingGroupName ):
    """[rebuild one instance from auto scaling group ]
    1. detach_instances from auto scaling group
    2. reboot the instance -- the rebuild script should run on reboot eg: when first create ec2 
        2.1 make a executable script
        2.2 add it to /etc/rc.local and make it executable as well
        2.3 in the script get parameter from outside where we can set eg API server and based on the flag reboot or upgrade
    3. re-attach_instances
    4. wait for the instance to be health
    
    Arguments:
        instanceId {[type]} -- [description]
        autoScalingGroupName {[type]} -- [description]
    
    Returns:
        [type] -- [description]
    """
    autoscalingClient = boto3.client('autoscaling')
    ec2Client = boto3.client('ec2')

    # 1. detach instances
    autoscalingClient.detach_instances(
        InstanceIds=[
            instanceId
        ]
    )

    # 2. reboot instance
    ec2Client.reboot_instances(
        InstanceIds=[
            instanceId
        ]
    )

    # 3. re-attach instance
    autoscalingClient.attach_instances(
        InstanceIds=[
            instanceId
        ],
        AutoScalingGroupName=autoScalingGroupName
    )

    # 4. wait for instance become health
    instanceHealth=wait_resource( autoscalingClient.describe_auto_scaling_instances, check_autoscaling_instance_health, 10, InstanceIds=[ instanceId ] )

    if instanceHealth:
        return True
    else:
        raise Exception("Fails to wait for instance to become healthy, try to wait for more time")

def reboot_instances_in_autoscaling_group_one_by_one( autoScalingGroupName ):
    """ reboot all the instances inside autoscaling one by one
    
    Arguments:
        autoScalingGroupName {[String]} -- [ autoScalingGroupName ]
    """
    autoscalingClient = boto3.client('autoscaling')
    res = autoscalingClient.describe_auto_scaling_groups(
        AutoScalingGroupNames=[
            autoScalingGroupName
        ]
    )

    autoscalings = res.get('AutoScalingGroups')

    if len(autoscalings) == 0:
        print("There is no autoscaling group name as {} no need to reboot".format( autoScalingGroupName ) )
        return
    
    autoscaling = autoscalings[0]

    instances = autoscaling.get("Instances")

    for instance in instances:
        rebuild_instance_from_auto_scaling_group( instance.get("InstanceId"), autoScalingGroupName )

def task2_autoscaling( projectName ):
    print( "LocalStack have not API point of Autoscaling, will use the real environment" )
    print( "Make sure passing fake autoscaling group name or it will reboot all the instances" )
    reboot_instances_in_autoscaling_group_one_by_one( projectName )
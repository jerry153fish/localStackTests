import unittest
import warnings
warnings.filterwarnings(action="ignore", message="unclosed", 
                         category=ResourceWarning)

from src.utils import (
    clean_up_cloudformation_stack,
    wait_resource
)

from src.task1.kinesis import (
    get_or_create_kinesis_stream,
    get_or_create_kinesis_cloudformation_stack,
    clean_up_kinesis,
    task1_kinesis

)

class TestTask1(unittest.TestCase):

    def setUp(self):
        self.projectName="unitTestTask1"

    def tearDown(self):
        clean_up_kinesis( self.projectName )
        clean_up_cloudformation_stack( self.projectName + 'Task1')
        
    def test_kinesis_stream_created_by_boto3(self):
        kinesis = get_or_create_kinesis_stream( self.projectName )

        assert kinesis.get('StreamStatus') == 'ACTIVE', "Expected to be ACTIVE"
        assert kinesis.get('StreamName') == self.projectName+"KinesisStream", "Expected name to be same"

    def test_firehose_s3_cloudformation_stack(self):
        stackName = self.projectName + "Task1"
        kinesis = get_or_create_kinesis_stream( self.projectName )
        task1_stack = get_or_create_kinesis_cloudformation_stack( self.projectName, kinesis['StreamARN'] )

        assert task1_stack.get('StackStatus') == 'CREATE_COMPLETE', "Expected status to be CREATE_COMPLETE"
        assert task1_stack.get('StackName') == stackName, "Expected name to be same"
    
    
    def test_whole_stack_setup_ok_and_can_upload_random_data( self ):
        task1_kinesis( self.projectName )
    
    
    def test_whole_stack_works_as_expected( self ):
        # FIXME: firehose process fails
        pass

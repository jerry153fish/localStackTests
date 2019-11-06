import datetime
import time
import threading
import boto3
from src.utils import random_alphanumeric

class KinesisProducer(threading.Thread):
    """Producer class for AWS Kinesis streams

    This class will emit records with the IP addresses as partition key and
    the emission timestamps as data"""

    def __init__(self, streamName, sleepInterval=None, ipAddr='8.8.8.8', totalTimes=100 ):
        self.streamName = streamName
        self.sleepInterval = sleepInterval
        self.ipAddr = ipAddr
        self.totalTimes = totalTimes
        self.kinesisClient = boto3.client('kinesis', endpoint_url='http://localhost:4568')
        super().__init__()

    def put_record(self):
        """put a single record to the stream"""
        timestamp = datetime.datetime.utcnow()
        part_key = self.ipAddr
        data = random_alphanumeric(10)
        print( "put {} to kinesisStrem {}".format( data, self.streamName ) )
        self.kinesisClient.put_record(
            StreamName=self.streamName, 
            Data=data, 
            PartitionKey=part_key
        )

    def run_continously(self):
        """put a record at regular intervals"""
        while self.totalTimes > 0:
            self.put_record()
            time.sleep(self.sleepInterval)
            self.totalTimes = self.totalTimes - 1

    def run(self):
        """run the producer"""
        try:
            if self.sleepInterval:
                self.run_continously()
            else:
                self.put_record()
        except Exception as e:
            print( e )
            print('Unexpected stream {} exception. Exiting'.format(self.streamName))
    def stop( self ):
        """ Stop producer """
        self.totalTimes = 0
    
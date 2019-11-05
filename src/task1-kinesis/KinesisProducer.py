import datetime
import time
import threading

class KinesisProducer(threading.Thread):
    """Producer class for AWS Kinesis streams

    This class will emit records with the IP addresses as partition key and
    the emission timestamps as data"""

    def __init__(self, stream_name, sleep_interval=None, ip_addr='8.8.8.8'):
        self.stream_name = stream_name
        self.sleep_interval = sleep_interval
        self.ip_addr = ip_addr
        super().__init__()

    def put_record(self):
        """put a single record to the stream"""
        timestamp = datetime.datetime.utcnow()
        part_key = self.ip_addr
        data = timestamp.isoformat()

        kinesis.put_record(self.stream_name, data, part_key)

    def run_continously(self):
        """put a record at regular intervals"""
        while True:
            self.put_record()
            time.sleep(self.sleep_interval)

    def run(self):
        """run the producer"""
        try:
            if self.sleep_interval:
                self.run_continously()
            else:
                self.put_record()
        except Exception as e:
            print('Unexpected stream {} exception. Exiting'.format(self.stream_name))
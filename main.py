from src.utils import random_alphanumeric
from src.task1.kinesis import task1_kinesis

from argparse import ArgumentParser

parser = ArgumentParser()
parser.add_argument("--name", action="store", required=True,
                    help="Project name")

parser.add_argument("--task", action="store",
                    help="Task to run")

args = parser.parse_args()

if __name__ == '__main__':
    if args.task is None:
        print("run both tasks")
        task1_kinesis( args.name + "Task1" , 10 )
    elif args.task == "task1":
        task1_kinesis( args.name + "Task1" , 10 )
    elif args.task == "task2":
        # TODO: task2
        pass
    else:
        print("Unknown task: {}".format(args.task))
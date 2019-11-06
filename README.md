### LocalstackTest

Simple localstack devops tests which include three main sections

1. localstack section 
2. task 1 kinesis scripts
3. task 2 autoscaling

### Dependencies

1. `git`
2. Mac user need to manually install [Docker](docker.io)

### Quick Start


#### init environment and start localstack

```bash
./setup.sh
```

![Mac screenshot](screenshots/setup&#32;on&#32;mac.png)

Will install all the dependencies, then setup virtual environment for `python 3.7` ( include `boto3` `troposphere`) and startup localstack server

1. for linux user will install `docker` `docker-compose` `pipenv` 
2. for mac user will install `pipenv` 
   

#### run tasks

```bash
    pipenv run python main.py --name=xxx --task=(task1|task2)
```

or

```bash
    pipenv shell # start pipenv shell
    python main.py --name=xxx --task=(task1|task2)
```

1. `--name` is required which will be use prefix for all resources
2. `--task` optional with ( task1 | task2 )


> Note: as there is no APIs for autoscaling in localstack, task2 runs on real environment if you have configure aws. Be careful run `--task=task2` and ensure passing in name is the test one

### Test

```bash
pipenv run python -m unittest discover tests # only for task1
```

### Structure

```
├── Pipfile
├── Pipfile.lock
├── README.md
├── __init__.py
├── docs
│   ├── KinesisProducer.html
│   ├── __init__.html
│   └── kinesis.html
├── main.py
├── screenshots
│   └── setup\ on\ mac.png
├── setup.sh
├── src
│   ├── __init__.py
│   ├── localstack
│   │   └── docker-compose.yml
│   ├── task1
│   │   ├── __init__.py
│   │   ├── kinesis.py
│   │   ├── kinesisProducer.py
│   │   └── randomStream.sh
│   ├── task2
│   │   ├── __init__.py
│   │   └── autoscaling.py
│   └── utils.py
└── tests
    ├── __init.py
    ├── test_task1.py
    └── test_task2.py

```

1. docs contains all documents all python files are
2. src localstack docker-compose file and task1 and task2 python files
3. tests unittest files
4. main.py main entry
5. setup.sh executable init file


### TODOS

#### Task1

1. [#10] could not verify firehose delievery works or not. As the target s3 bucket is empty 
2. Boto3 session need to be close in tearDown - which requires refactor the getClient method
3. Maybe use `opencv` for random stream mock

### Task2

1. localstack has no autoscaling mock APIs, so need to use another mock eg `moto` for unittest
2. the code was never tested
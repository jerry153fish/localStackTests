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

1. for linux user will install `docker` `docker-compose` `pipenv` `ffmpeg` 
2. for mac user will install `pipenv` `ffmpeg`
   

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


### Test

### TODO List


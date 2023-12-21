# Evaluations around serlo.org

This repository contains evaluations and data analysis reports about serlo.org.

## Setup

1. Clone this repository.
2. Install `python` version 3.x, `docker` and `docker-compose`.
3. Install dependencies from [`requirements.txt`](./requirements.txt), e.g. via
   `pip install -r requirements.txt`
4. Run [`jupyter_notebook.sh`](./jupyter_notebook.sh) to start a local database
   with anonymous data from serlo.org and a jupyter notebook.

## Others

Run `./mysql.sh` to connect to the mysql database  
Run `./postgres.sh` to connect to the postgres database

## Common issues

### gsutil

If you have installed `gsutil` in your machine before, after cloning and setting
up this repo, you may get the error

> ServiceException: 401 Anonymous caller does not have storage.objects.list
> access to the Google Cloud Storage bucket. Permission 'storage.objects.list'
> denied on resource (or it may not exist)

For that, do `pip uninstall gsutil` to continue using your usual, authenticated
`gsutil`.

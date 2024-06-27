#!/bin/bash

source scripts/utils.sh

function init {
	set -e
	trap tear_down EXIT

	start_mysql
#	./scripts/import_anonymous_data.sh
}

function main {
	jupyter notebook
}

function tear_down {
	docker compose down
}

function start_mysql {
	docker compose up --detach
}


init
main
tear_down

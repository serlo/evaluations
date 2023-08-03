#!/bin/bash

set -e

source scripts/utils.sh

TMP_DIR=$(mktemp -d -t serlo-anonymous-dataXXXXXX)
TMP_DUMP="${TMP_DIR}/dump.zip"
LATEST_DUMP=$(gsutil ls -l gs://anonymous-data \
	| grep dump \
	| sort -rk 2 \
	| head -n 1 \
	| awk '{ print $3 }')

gsutil cp "${LATEST_DUMP}" "${TMP_DUMP}"
unzip -d "${TMP_DIR}" "${TMP_DUMP}"

echo "Let's wait for the mysql database to be ready"
sleep 30
exec_mysql serlo < "${TMP_DIR}/mysql.sql"
docker cp "${TMP_DIR}/user.csv" $(docker-compose ps -q mysql):/
exec_mysql -e "LOAD DATA LOCAL INFILE 'user.csv' INTO TABLE user \
				FIELDS TERMINATED BY '\t' LINES TERMINATED BY '\n' \
				IGNORE 1 ROWS;" serlo
echo "Let's wait for the postgres database to be ready"
sleep 30
docker compose exec -T postgres psql --user serlo kratos < "${TMP_DIR}/kratos.sql"
rm -r ${TMP_DIR}

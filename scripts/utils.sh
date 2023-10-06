function exec_mysql {
	docker compose exec -T mysql mysql --user=root --password=secret --local-infile=1 "$@"
}

mysqldump --protocol=tcp --port=7777 --user=serlo --password --lock-all-tables --set-gtid-purged=OFF serlo > /tmp/dump-before-migration-0.3.1.sql
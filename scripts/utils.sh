function exec_mysql {
	docker compose exec -T mysql mysql --user=root --password=secret "$@"
}
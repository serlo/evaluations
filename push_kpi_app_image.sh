version=0.1

image=eu.gcr.io/serlo-shared/kpi-dashboard:$version

docker build ./src/KPI_App/ -t $image

docker push $image

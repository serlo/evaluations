version=0.3

image=eu.gcr.io/serlo-shared/kpi-dashboard:$version

docker build ./src/kpi_app/ -t $image

docker push $image

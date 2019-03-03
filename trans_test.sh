#!/bin/bash

container_a=`docker run -d -p 5001:5000 pczubows/bogchain`
container_b=`docker run -d -p 5002:5000 pczubows/bogchain`

a_url=http://localhost:5001
b_url=http://localhost:5002

echo "mining"
for i in  $(seq 4) 
do
	curl $a_url/mine > /dev/null
	curl $b_url/mine > /dev/null
done

b_id=`curl $b_url/node_id | \
	python3 -c "import sys, json; print(json.load(sys.stdin)['node_id'])"`

echo $b_id



curl --header "Content-Type: application/json" \
	--request POST \
	--data "{\"recipient\": \"$b_id\", \"amount\": 1}" \
	$a_url/send 

echo "mining"
for i in $(seq 4)
do
	curl $a_url/mine > /dev/null
	curl $b_url/mine > /dev/null
done



echo "a balance:"
curl $a_url/balance | json_pp

echo "b balance:"
curl $b_url/balance | json_pp

docker stop $container_a $container_b 

#!/bin/bash

# test network with all nodes mining at same speed
# no one attempts to forge blockchain
# needs to be run from project root directory

if [[ "$VIRTUAL_ENV" == "" ]]
then
  echo "Not in virtualenv exiting"
  exit 1 
fi

python app.py -p 5001 -G -s "test_scenarios/normal/test_schedule_a.txt" &
python app.py -p 5002 -s "test_scenarios/normal/test_schedule_b.txt" &
python app.py -p 5003 -s "test_scenarios/normal/test_schedule_c.txt" & 

sleep 10

test_scenarios/get_chains.sh 3
pkill -P $$




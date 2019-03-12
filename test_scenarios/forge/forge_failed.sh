#!/bin/bash

# test network with all nodes mining at same speed
# one node attempts to forge blockchain
# needs to be run from project root directory

if [[ "$VIRTUAL_ENV" == "" ]]
then
  echo "Not in virtualenv exiting"
  exit 1 
fi

python app.py -p 5001 -G -v -s "test_scenarios/forge/test_schedule_a.txt" &> a_logs.txt &
python app.py -p 5002  -v -s "test_scenarios/forge/test_schedule_b.txt" &> b_logs.txt &
python app.py -p 5003  -v -s "test_scenarios/forge/test_schedule_c.txt" &> c_logs.txt &
python app.py -p 5004  -v -s "test_scenarios/forge/test_schedule_e.txt" &> e_logs.txt &

sleep 15

test_scenarios/get_chains.sh 4
pkill -P $$




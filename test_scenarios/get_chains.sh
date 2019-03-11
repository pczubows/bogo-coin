#!/bin/bash

# simple script for looking up blockchain state of all apps in the network 
# * param1 - number of nodes in the network (assumes port numbers going from 5001 up) 
{
    for i in $(seq $1) 
        do
        curl localhost:500$i/node_id | json_pp
        printf "\n"
        curl localhost:500$i/balance | json_pp
        printf "\n"
    done;

    for i in $(seq $1)
        do
        curl localhost:500$i/node_id | json_pp
        printf "\n"
        curl localhost:500$i/chain | json_pp
        printf "\n"
    done

    for i in $(seq $1)
        do
        curl localhost:500$i/node_id | json_pp
        printf "\n"
        curl localhost:500$i/peers | json_pp
        printf "\n"
    done
} > dump.json
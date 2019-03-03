#!/bin/bash

{
    for i in $(seq 3)
        do
        curl localhost:500$i/node_id | json_pp
        printf "\n"
        curl localhost:500$i/chain | json_pp
        printf "\n"
    done

    for i in $(seq 3) 
        do
        curl localhost:500$i/node_id | json_pp
        printf "\n"
        curl localhost:500$i/balance | json_pp
        printf "\n"
    done;
} > dump.json
#!/bin/bash
lsof -i :7777 |  grep "localhost:7777" | awk '{print $2}' | xargs -I {} bash -c 'kill -9 {}'
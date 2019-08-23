#!/bin/bash
# Our custom function
cust_func(){
  echo "Connect to the server $1 times..."
  #python3 elasticurl.py -v ERROR -G http://127.0.0.2:8127/
  python3 local_client_test.py
  sleep 1
}
# For loop 100 times
for i in {1..100}
do
	cust_func $i & # Put a function in the background
done
 
## Put all cust_func in the background and bash 
## would wait until those are completed 
## before displaying all done message
wait 
echo "All done"
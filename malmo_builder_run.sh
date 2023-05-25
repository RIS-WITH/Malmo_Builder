# malmo_builder launch file for 
# arguments is the number of clients to launch
# example: ./malmo_builder_run_local.sh 3
# this will launch 3 clients and run the python script
# default is 1 client

# get the argument
if [ $# -eq 0 ]
  then
    echo "No arguments supplied, defaulting to 1 client"
    num_clients=1
else
    echo "Number of clients to launch: $1"
    num_clients=$1
fi
# in a new terminal ./launchClient.sh
# open a new instance of terminal and save the pid
echo "Launching server"
xterm -hold -e "cd ../Minecraft; ./launchClient.sh " &
# save the pid
lastpid=$!
# wait for the client to start
sleep 50

echo "Launching client(s)"
# launch the rest of the clients
for (( i=1; i<$num_clients; i++ ))
do
    # open a new instance of terminal
    xterm -hold -e "cd ../Minecraft; ./launchClient.sh " &
    # wait for the client to start
    sleep 50
done
sleep 150
# if more than one client then rerun the first one so the latest.log is updated with the server info
if [ $num_clients -gt 1 ]
then
    sleep 110
    echo "Relaunching first client fir log update"
    # kill the first client
    kill $lastpid
    # open a new instance of terminal
    xterm -hold -e "cd ../Minecraft; ./launchClient.sh " &
    # wait for the client to start
    sleep 50
fi

# run the python script
python3 main.py
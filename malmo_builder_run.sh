# in a new terminal ./launchClient.sh -port 10001
# open a new instance of terminal and save the pid
xterm -hold -e "cd ../Minecraft; ./launchClient.sh " &
# save the pid
$pid = $!
# wait for the client to start
sleep 50
# open a new instance of terminal
xterm -hold -e "cd ../Minecraft; ./launchClient.sh " &
# wait for the client to start
sleep 50
# open a new instance of terminal
xterm -hold -e "cd ../Minecraft; ./launchClient.sh " &
# wait for the client to start
sleep 300

# kill the process
kill -9 $pid

# open a new instance of terminal
xterm -hold -e "cd ../Minecraft; ./launchClient.sh " &

# wait for the client to start
sleep 200

# run the python script
python3 main.py
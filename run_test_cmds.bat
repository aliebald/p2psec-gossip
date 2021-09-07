:: This script starts multiple instances of gossip with different configs.
:: Each instance gets its own terminal. 

echo "Starting 4 delayed instances of Gossip in new terminals and exiting afterwards"

start cmd.exe /k main.py -p "./test_configs/config_1.ini" -v

:: wait for 8 seconds
timeout 8 > nul
start cmd.exe /k main.py -p "./test_configs/config_2.ini" -v

:: wait for 8 seconds
timeout 8 > nul
start cmd.exe /k main.py -p "./test_configs/config_3.ini" -v

:: wait for 8 seconds
timeout 8 > nul
start cmd.exe /k main.py -p "./test_configs/config_4.ini" -v

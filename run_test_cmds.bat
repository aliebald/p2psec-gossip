:: This script starts multiple instances of gossip with different configs.
:: Each instance gets its own terminal. 

echo "This terminal will be closed after all test instances are opened."

start cmd.exe /k main.py -p "./test_configs/config_1.ini"

:: wait for 2 seconds
timeout 2 > nul
start cmd.exe /k main.py -p "./test_configs/config_2.ini"

:: wait for 5 seconds
timeout 5 > nul
start cmd.exe /k main.py -p "./test_configs/config_3.ini"

:: wait for 5 seconds
timeout 5 > nul
start cmd.exe /k main.py -p "./test_configs/config_4.ini"

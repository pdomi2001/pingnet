# ping_iot
pinging project in python using threads and multiplatform
the main file, written in english is [/en/ping_iot.py](/en/ping_iot.py)

## Avaiability
the project is avaiable in 2 formats:
- italian (in the [it/](/it/) folder)
- english (in the [en/](/en/) folder)

WARNING: also the settings of the 2 are different.


## project's steps

1. importing modules and the parsing the arguments
2. getting the configuration desired in line 54
3. getting the number of pcs to analyze in line 93
4. define addresses,desc_pc,scan_results,pc_type with the numbers from 0 to the number of pcs
5. looping over the networks and filling the lists previously mentioned.
6. initalizing and joining the threads to ping.
7. if the argument webmode is inserted, it'll skip much visualization as possible to build the webfile
8. if the argument '--save-time-dataframe' is inserted it'll save the times in different formats using pandas.



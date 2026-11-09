Readme for the measurement files of the Munich Bell Experiment

Content of the zip file:
*_lab_1.csv
*_lab_2.csv
*_pairs.csv


*_lab_1.csv and *_lab_2.csv contain all performed measurement attempts for each side.
Some of those attempts are invalid and thus excluded from evaluation with reason being stated in the comment field.
Common reasons for exclusion are e.g. measurement triggered during maintenance as well as malfunction of the CEM-detectors or the laser system.

*_pairs.csv contains data of valid atom-atom events 


description of the columns in the .csv files:

time (Unix time in ms) 
time and date of the event
Can be used to pair events from lab 1 and 2 within a time window of +-100ms. This time window is necessary due to jitter of computer clocks.

setting
random number input to select the measurement basis

result
measurement result

local timestamp
High precision timestamp allowing to identify the used random number within the complete set of random numbers.

Bell-state (only in lab 1 and pair files)
gives the heralded state

excluded from evaluation
if event is excluded from evaluation

comment
comment to the event e.g. reason for exclusion

line in lab 1/2 file (only in pair files)
corresponding line in the *_lab_1/2.csv file (line number starts after the header line)
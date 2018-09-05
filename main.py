import csv
import math
from itertools import repeat
import timeit
from flask import Flask, request, render_template, redirect, Response, url_for
import json

app = Flask(__name__)

@app.route('/', methods = ['GET'])
def index():
    return render_template(('index.html'), val=2)

@app.route('/check', methods = ['GET', 'POST'])
def checkpid():
    global piddata
    piddata = str(request.get_data())
    f = open('codes.txt', 'r')
    keys = []
    rows = {}
    for row in f:
        jsonrow = json.loads(row)
        key = jsonrow.keys()[0]
        keys.append(key)
        rows[key] = jsonrow[key]
    if piddata in keys:
        samplecode = rows[piddata]
        return json.dumps(samplecode)
    return '0'

@app.route('/sendto', methods = ['GET', 'POST'])
def suu():
    data = request.get_json(force=True)
    global timeseq
    timeseq = {}
    convert(data)
    timeseq = json.dumps(timeseq)
    return timeseq

if __name__ == '__main__':
    app.run()

## CONVERT WORKER ENTRIES
def convert(d):
    global codes
    codes = {}
    for row in d:
        mach = str(row['m'])
        if (mach not in codes.keys()):
            codes[mach] = []
        code = []
        t = int(row['t'])/1000.0 - 1
        t = int(5 * round(float(t)/5))
        code = [t] + [row['c']] + code
        codes[mach].append(code)
    for c in codes.keys():
        codes[c] = [[0.0, 'LOAD']] + codes[c]
    gen()
    
## READ CODES FROM FILE
def readcodes():
    global codes
    codes = {} # machinenum:codes
    with open('samplecodes/code1.csv', 'rb') as codefile:
        rd = csv.reader(codefile)
        for row in rd:
            if row[2] in codes.keys():
                codes[row[2]].append([float(row[0]), row[1]])
            else:
                codes[row[2]] = [[float(row[0]), row[1]]]
    for c in codes.keys():
        codes[c] = [[0.0, 'LOAD']] + codes[c]
    gen()

def gen():
    global TIMESTEP, PRES, SEQ
    global priority, mtimes, FLOW
    global loadtime, optime
    ## MAINTAINER CAN CHANGE
    TIMESTEP = 5    # seconds per step
    PRES = 60       # seconds to round to
    SEQ = False     # sequence machines. !! ONLY FOR 1-4 MACHINES !!
    
    ## OPERATOR CAN CHANGE
    loadtime = 20   # seconds to load machine
    optime = 15     # seconds per operation
    
    ## FIND MACHINE TIMES
    priority = {} # time:machinenum
    for machine in codes:
        mtime = 0
        for op in codes[machine]:
            mtime += op[0]
        priority[mtime] = machine
    
    ## GET TIME OF CYCLE
    mtimes = priority.keys()
    bntime = max(mtimes)
    totaltime = int(math.ceil(bntime/PRES)*PRES)
    if totaltime < 60:
        totaltime = 60
    FLOW = [0] * ((totaltime/TIMESTEP) * 2) # add extra time
    addseq()
    addcodes(FLOW, priority, len(mtimes))
    trim(FLOW)
    timingseq()
    return timeseq

## ADD CODES TO FLOW
def addcodes(FLOW, priority, mtimes):
    for m in range(0, mtimes):
        maxval = max(priority.keys())
        machine = priority[maxval]
        flowpos = 0
        for code in codes[str(machine)]:
            flowpos += int(code[0]/TIMESTEP)
            while FLOW[flowpos] != 0:
                flowpos += 1
            FLOW[flowpos] = code[1] + " - " + str(machine)
            end = int(optime/TIMESTEP)
            if code[1] == 'LOAD':
                end = int(loadtime/TIMESTEP)
            for i in range(1, end): # add buffer time
                try:
                    FLOW[flowpos + i] = 1
                except IndexError:
                    FLOW.append(1)
                if code[1] != 'LOAD':
                    FLOW[flowpos - i] = 1
        del priority[maxval]


## TRIM EXCESS MINUTES
def trim(FLOW):
    global target
    target = 0
    while FLOW[-1] == 0 or FLOW[-1] == 1:
        del FLOW[-1]
    newlen = len(FLOW)
    target = int(math.ceil(float(newlen)/float(PRES))*PRES)
    for i in range(0, target - newlen):
        FLOW.append(0)

## OPTIONS FOR DISPLAYING FLOW
def printheader():
    print "#########################"
    print "Target per hour: " + str(target*TIMESTEP/60)
    print "#########################"
def printcodes(FLOW):
    for code in FLOW:
        if code != 0 and code != 1:
            print code
        else:
            print ""

## CONVERT TO TIMING SEQUENCE
def timingseq():
    t = 0
    for code in FLOW:
        if code != 0 and code != 1:
            timeseq[t] = code
        t += TIMESTEP
    f = open('codes.txt', 'a')
    pidfull = {}
    pidfull[piddata] = timeseq
    f.write(json.dumps(pidfull))
    f.write('\n')
    f.close()


## ADD INITIAL SEQUENCE OF PARTS
def addseq():
    if SEQ:
        nm = len(mtimes)
        if nm == 2:
            PREFLOW = [0] * ((totaltime/TIMESTEP) * 2)
            priority1 = { t:m for t,m in priority.items() if m == '1' }
            addcodes(PREFLOW, priority1, 1)
            trim(PREFLOW)
            printcodes(PREFLOW)
        if nm == 3:
            PREFLOW = [0] * ((totaltime/TIMESTEP) * 2)
            priority1 = { t:m for t,m in priority.items() if m == '1' }
            addcodes(PREFLOW, priority1, 1)
            trim(PREFLOW)
            printcodes(PREFLOW)
            PREFLOW = [0] * ((totaltime/TIMESTEP) * 2)
            priority1 = { t:m for t,m in priority.items() if m != '3'}
            addcodes(PREFLOW, priority1, 2)
            trim(PREFLOW)
            printcodes(PREFLOW)
        if nm == 4:
            PREFLOW = [0] * ((totaltime/TIMESTEP) * 2)
            priority1 = { t:m for t,m in priority.items() if m == '1' or m == '3' }
            addcodes(PREFLOW, priority1, 2)
            trim(PREFLOW)
            printcodes(PREFLOW)
    

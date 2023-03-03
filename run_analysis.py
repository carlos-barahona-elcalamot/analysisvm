#!/bin/python3

import argparse
from analisisvmlib import *
import csv
import os
from pathlib import Path
import subprocess as sh
import json
import re
import vboxapi
import time

submissionsFolder = "data/submissions/"
studentsFile = "data/students.csv"
recordsFile = "data/records.json"
importFolder = os.getcwd() + "/data/imported/"
importGroup = "/AnalysisVM"
importPrefix = "Ana_"
importKeepName = False
sshPort = 2200
sshKey = "analysisVM/analysisvm"
vmAnalysis = "AnalisisVMs"
vboxmanage="vboxmanage"
vmSerialOut="/tmp/vmout"
headlessVM=True



def readStudentsFile(csvFilePath):
    csvReader = csv.reader(open(csvFilePath, 'r', newline=''))
    studentsMap = {}
    line = 0
    fNamePos = -1
    sNamePos = -1
    eMailPos = -1
    for fila in csvReader:
        if line == 0:
            fNamePos = fila.index("First name")
            sNamePos = fila.index("Surname")
            eMailPos = fila.index("Email address")
            line += 1
        else:
            email = fila[eMailPos]
            name = fila[fNamePos]
            surname = fila[sNamePos]
            studentsMap[email.split('@')[0].lower()
                        ] = Student(name, surname, email)
    return studentsMap


def saveStudentRecords(students, recordsFile):
    json.dump({id: student.toJSON() for id, student in students.items()}, open(
        recordsFile, 'w'), indent=3, ensure_ascii=False)


def selectStudent(studentsList, ovafile: str) -> str:
    print("-"*30)
    print("List of students: ")
    studentsWithoutOva = []
    n = 0
    for studentKey, student in studentsList.items():
        if student.ovafile == None or student.ovafile == "":
            print("["+str(n)+"]: "+str(student))
            studentsWithoutOva.append(studentKey)
            n += 1
    print("ova file: "+ovafile)
    try:
        selected = studentsWithoutOva[int(
            input("Select student author of ova: "))]
    except:
        selected = None
    return selected


def assign(submissionsFolder, studentsFile):
    students = readStudentsFile(studentsFile)
    studentsList = [str(x)+" ("+x.email+") " for x in students.values()]
    unassignedOvas = []
    for ovafile in os.listdir(submissionsFolder):
        ovaName = Path(ovafile).stem.lower()
        if ovaName in students:
            students[ovaName].ovafile = submissionsFolder + ovafile
        else:
            print("Debug: not match for ovaname="+ovaName)
            print("Debug: students list: "+str(students.keys()))
            unassignedOvas.append(ovafile)
    for ovafile in unassignedOvas:
        selectedStudent = selectStudent(students, ovafile)
        if selectedStudent != None and selectedStudent != "":
            students[selectedStudent].ovafile = submissionsFolder + ovafile

    return students


def importOvas(students: {str: Student}, importFolder="", importGroup="", importPrefix="", keepName=False):
    print()
    print('-'*20)
    print("Importing ova to "+importFolder)
    print()
    studentId: str
    student: Student
    if importFolder != None and importFolder != "":
        importFolder = "--basefolder="+importFolder
    if importGroup != None and importGroup != "":
        importGroup = "--group="+importGroup+""
    totalStudents = len(students)
    importedOvas = 0
    for studentId, student in students.items():
        importedOvas += 1
        if student.ovafile == None or student.ovafile == "":
            print("("+str(importedOvas)+"/"+str(totalStudents) +
                  ") No ova file for "+str(student))
            continue
        vmNameOption = ""
        if not keepName:
            vmNameOption = "--vmname="+importPrefix+studentId
        print("("+str(importedOvas)+"/"+str(totalStudents) +
              ") Importing "+student.ovafile, end=" -> ", flush=True)
        processOut = sh.run(["vboxmanage", "import", "--vsys=0", student.ovafile, importFolder,
                            importGroup, vmNameOption], shell=False, text=True, capture_output=True)
        if processOut.returncode != 0:
            print("ERROR")
            print(processOut.stderr)
        else:
            reExpr = re.compile(
                r"[\w\W]*VM name specified .* \"([^\"]*)\"[\w\W]*")
            matches = reExpr.match(processOut.stdout)
            student.vmName = matches.group(1)
            print("OK. Imported to "+matches.group(1))
            # print(processOut.stdout)


def analyzeHdd(vmName, sshKey, vbox, sshPort=8022, vmAnalysis="AnalisisVMs"):
    vmAnalysisOrig = vbox.findMachine(vmAnalysis)
    print("About to ckeck "+vmName+" hard disk")
    machine = vbox.findMachine(vmName)
    results = []
    for medi in machine.getMediumAttachments():
        # print("Medi: "+str(medi.medium)+"  Type: "+str(medi.type))
        if medi.type == 3:
            vmAnalysisSess = vboxMgr.openMachineSession(vmAnalysisOrig)
            vmAnalysis = vmAnalysisSess.machine
            try:
                vmAnalysis.detachDevice("SATA", 1, 0)
            except:
                pass
            vmAnalysis.attachDevice("SATA", 1, 0, 3, medi.medium)
            vmAnalysis.saveSettings()
            vboxMgr.closeMachineSession(vmAnalysisSess)

            vmAnalysisSess = vboxMgr.getSessionObject(vbox)
            progress = vmAnalysisOrig.launchVMProcess(
                vmAnalysisSess, "headless" if headlessVM else "gui", [])
            progress.waitForCompletion(5000)
            # time.sleep(5)
            # print(progress.description)
            # time.sleep(5)

            sortida_cmd = sh.run("echo './analysis-partitions' | ssh -p "+str(sshPort)+" -i "+sshKey+" root@localhost ",
                                 shell=True, text=True, capture_output=True)
            print("------ SSH stdout--------------")
            print(sortida_cmd.stdout)
            print("------- SSH END ---------")
            print("------ SSH stderr--------------")
            print(sortida_cmd.stderr)
            print("------- SSH END ---------")

            # Extraem el json de la sortida del ssh
            match = re.search("\{[\w\W]*\}", sortida_cmd.stdout)
            if (match):
                resultat_test = match.string[match.start():match.end()]

            print("---- resultat -------")
            # print("Resultat per l'alumne ",alumne)
            print(resultat_test)
            print("----------------------")
            # vmData[alumne]["discos"]=json.loads(resultat_test)["blockdevices"]
            results=json.loads(resultat_test)["blockdevices"]

            # time.sleep(5)
            progress = vmAnalysisSess.console.powerDown()
            progress.waitForCompletion(5000)
            vmAnalysisSess.unlockMachine()
            time.sleep(5)

            # vboxMgr.closeMachineSession(vmAnalysisSess)

            vmAnalysisSess = vboxMgr.openMachineSession(vmAnalysisOrig)
            vmAnalysis = vmAnalysisSess.machine
            vmAnalysis.detachDevice("SATA", 1, 0)
            vmAnalysis.saveSettings()
            vboxMgr.closeMachineSession(vmAnalysisSess)
    return results

def runSystemTests(vmName:str):

    # root
    out=sh.run(vboxmanage+" controlvm "+vmName+" keyboardputscancode "+"13 93 18 98 18 98 14 94 "+" 1c 9c",
                            shell=True, text=True, capture_output=True)

    # Asdqwe!23
    out=sh.run(vboxmanage+" controlvm "+vmName+" keyboardputscancode "+" 36 1e 9e b6 1f 9f 20 a0 10 90 11 91 12 92 36 02 82 b6 03 83 04 84 "+" 1c 9c",
                            shell=True, text=True, capture_output=True)

    time.sleep(5)
    # Si es tiny matamos GUI
    out=sh.run(vboxmanage+" controlvm "+vmName+" keyboardputscancode "+" 1d 38 0e 8e b8 9d",
                            shell=True, text=True, capture_output=True)
    time.sleep(1)

    # ./tests.sh
    out=sh.run(vboxmanage+" controlvm "+vmName+" keyboardputscancode "+"34 b4 36 36 08 88 b6 14 94 12 92 1f 9f 14 94 1f 9f 34 b4 1f 9f 23 a3  "+" 1c 9c",
                            shell=True, text=True, capture_output=True)

    time.sleep(5)

    resultat_test={}
    if Path(vmSerialOut).is_file():
        match = re.search("\{[\w\W]*\}", open(vmSerialOut).read())
        if (match):
            resultat_test = json.loads(match.string[match.start():match.end()])

    else:
        print("Could not run tests "+vmName+" machine.")
        resultat_test={"error": "Error running tests."}

    return resultat_test    

def bootStudentVM(vmName, nSystem):

    print("Trying to boot "+vmName+" sytem "+str(nSystem))
    # Configure serial port to capture VM output
    out=sh.run(vboxmanage+" modifyvm "+vmName+" --uart1 0x3F8 4 --uartmode1 file "+vmSerialOut,
                                 shell=True, text=True, capture_output=True)
    
    if Path(vmSerialOut).is_file():
        os.remove(vmSerialOut)
    
    out=sh.run(vboxmanage+" startvm "+vmName+(" --type headless" if headlessVM else ""),
                                 shell=True, text=True, capture_output=True)

    
    booting=True
    menuOptionSelected=False
    t=0
    tStep=0.4
    maxTime=10
    resultat={"error":"Couldn't boot."}
    while booting:
        if Path(vmSerialOut).is_file():
            out=open(vmSerialOut,"r").read()
            if ("or any other key to continue" in out) and ("startup.nsh" in out) and ("Welcome to GRUB" not in out): 
                # Probably couldn't boot GRUB and EFI Shell is waiting for a key press to exec startup.nsh. We send "ENTER" 
                # to skip waiting and continue booting process
                print("EFI shell detected")
                out=sh.run(vboxmanage+" controlvm "+vmName+" keyboardputscancode 1c 9c",
                                    shell=True, text=True, capture_output=True)
                time.sleep(1)
            elif ("Welcome to GRUB" in out) and ("Select Language" in out): # and ("Device Manager" in out) and ("Boot Manager" in out):
                # This option has made GRUB boot to EFI BIOS App
                print("Boot to Firmware")
                resultat={"GRUB Firmware option": 1}
                booting=False
            elif ("Welcome to GRUB" in out):
                # GRUB has booted, so we select the nth option
                # Boot nth system
                print("GRUB detected")
                if (not menuOptionSelected):
                    out=sh.run(vboxmanage+" controlvm "+vmName+" keyboardputscancode "+"e0 50 e0 d0 "*nSystem+" 1c 9c",
                                            shell=True, text=True, capture_output=True)
                    # Wait 2 seconds, but continue booting process in case we have selected boot to firmware
                    time.sleep(2)
                    menuOptionSelected=True
                else:
                    # Wait for OS to finish boot
                    time.sleep(20)
                    resultat=runSystemTests(vmName)
                    booting=False

        time.sleep(tStep)
        t+=tStep
        if t>maxTime:
            booting=False



    out=sh.run(vboxmanage+" controlvm "+vmName+" poweroff",
                                 shell=True, text=True, capture_output=True)

    time.sleep(5)


    return resultat

def hddsStudent(student: Student, sshKey, vbox, sshPort=8022, vmAnalysis="AnalisisVMs"):
            student.hdds=[]
            if student.vmName != None and student.vmName != "":
                student.hdds = analyzeHdd(
                    student.vmName, sshKey, vbox, sshPort, vmAnalysis)

def systemsStudent(student: Student):
    student.systems={}
    if student.vmName != None and student.vmName != "":
        for i in range(5):
            try:
                rawSystems= bootStudentVM(student.vmName,i)
                if "root_dev" in rawSystems:
                    student.systems[rawSystems["root_dev"]]=rawSystems
                else:
                    print("ERROR booting option "+str(i))
                    print(rawSystems)
                    print("-"*10)
            except Exception as e:
                    print("EXCEPTION booting option "+str(i))
                    print(str(e))
                    print("-"*10)
    else:
        student.systems={}


parser = argparse.ArgumentParser(
    formatter_class=argparse.ArgumentDefaultsHelpFormatter)

parser.add_help = True
parser.add_argument('-s', '--submissions',
                    default=submissionsFolder,
                    help='Submissions folder whith ova files to analyze.')
parser.add_argument('--students',
                    default=studentsFile,
                    help='CSV file with students list. It must contain at least the following columns: "First name", "Surname" and "Email address".')
parser.add_argument('-r', '--student-records',
                    default=recordsFile,
                    help='JSON file with students records. It is generated running the script with the --assign option.')
parser.add_argument('-a', '--assign', action='store_true',
                    help="Assigns each ova file to the student. If the ova file name corresponds to the student email (without the server part), it is assigned automatically, otherwise, you have to assign it manually, selecting the author from the presented list.")
parser.add_argument('--import-ova', action='store_true',
                    help="Import ova files to VirtualBox. It imports ova files registered in the students records file, so you before using this option, you should run the --assign option to generate the file, and include the -r option if you are not using the defaults.")
parser.add_argument('--import-folder',
                    default=importFolder,
                    help="Base folder where imported ova are stored. If you use a relative path, it will be relative to VirtualBox's VMs path.")
parser.add_argument('--import-group',
                    default=importGroup,
                    help='Name of the group where ovas are imported. It must begin with /.')
parser.add_argument('--import-prefix',
                    default=importPrefix,
                    help='Prefix to add to the imported VM name. The name of the imported VM will be this prefix plus the student id (student email without the server part).')
parser.add_argument('--import-keep-name', action='store_true',
                    help="Keeps the original VM name when importing the ova (it cancels --import-prefix option)")
parser.add_argument('-p', '--port', default=sshPort,
                    type=int, help="Port to ssh to AnalysisVM")
parser.add_argument('--ssh-key', default=sshKey,
                    help="Private key file to connect to analysis VM passwordless. It is generated by ssh-keygen")
parser.add_argument('--analysis-vm', default=vmAnalysis,
                    help="Name of the master virtual machine which will analyze students hdd.")
parser.add_argument('--hdd', action='store_true',
                    help="Analyze hdd of the students virtual machines. It adds the results to the records.json file.")
parser.add_argument('--systems', action='store_true',
                    help="Tries to boot student machine and analyze booted system. It adds the results to the records.json file.")
parser.add_argument('--student', help="Runs the option only for this student. It works with --systems and --hdd options.")
parser.add_argument('--headless', action='store_true',
                    help="Runs VMs in headless mode (without GUI).")



#parser .add_argument('-t', '--test', help="studentId: run tests for student id")
#parser.add_argument('-j', '--json', help="fitxer json de sortida amb els resultats")
#parser.add_argument('-l', '--logFile', help='/path/filename for log file. Default /var/log/daitsu/awd_controller_service.log')
#parser.add_argument('-d', '--dataFile', help='/path/filename for data file. Default /var/log/daitsu/awd_controller_service_data.json')
#parser.add_argument('-t', '--pollingSeconds', type=int, help='Time in seconds between polls. Default=60 seconds')


args = parser.parse_args()

if args.submissions != None and args.submissions != "":
    submissionsFolder = args.submissions
    if submissionsFolder[-1] != "/":
        submissionsFolder += "/"

if args.students != None and args.students != "":
    studentsFile = args.students

if args.student_records != None and args.student_records != "":
    recordsFile = args.student_records


if args.import_folder != None and args.import_folder != "":
    importFolder = args.import_folder
    if importFolder[-1] != "/":
        importFolder += "/"

if args.import_group != None and args.import_group != "":
    importGroup = args.import_group

if args.import_prefix != None and args.import_prefix != "":
    importPrefix = args.import_prefix

if args.port != None:
    sshPort = args.port

if args.ssh_key != None and args.ssh_key != "":
    sshKey = args.ssh_key

if args.analysis_vm != None and args.analysis_vm != "":
    vmAnalysis = args.analysis_vm

if args.headless:
    headlessVM=True
else:
    headlessVM=False

students = None
if args.assign:
    students = assign(submissionsFolder, studentsFile)
    saveStudentRecords(students, recordsFile)
    for clave, student in students.items():
        print('*'*10)
        print(clave)
        print("   "+str(student))
        print("   Email: "+student.email)
        print("   ovafile: "+student.ovafile)

if students == None:
    students = readStudentsJSON(recordsFile)

if args.import_ova:
    importOvas(students, importFolder, importGroup,
               importPrefix, args.import_keep_name)
    saveStudentRecords(students, recordsFile)

vboxMgr = vboxapi.VirtualBoxManager(None, None)
vbox = vboxMgr.getVirtualBox()

if args.hdd:
    student: Student
    if args.student!=None and args.student!="":
        hddsStudent(students[args.student], sshKey, vbox, sshPort, vmAnalysis)
    else:
        for student in students.values():
            hddsStudent(student, sshKey, vbox, sshPort, vmAnalysis)
    saveStudentRecords(students, recordsFile)

if args.systems:
    student: Student
    if args.student!=None and args.student!="":
        systemsStudent(students[args.student])
        saveStudentRecords(students, recordsFile)
    else:
        for student in students.values():
            systemsStudent(student)
            saveStudentRecords(students, recordsFile)

time.sleep(2)
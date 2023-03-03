#!/bin/python3

import argparse
from analisisvmlib import *

recordsFile = "data/records.json"


class ResultatTest:

    def __init__(self, nota: float, target: str, resultat: str, comentari: str):
        self.nota = nota
        self.target = target
        self.resultat = resultat
        self.comentari = comentari


class Test:

    def __init__(self, description: str, target):
        self.description = description
        self.target = target

    def run(self, student: Student) -> ResultatTest:
        pass


class CheckNumberPartitions(Test):

    noDiskErrorMsg = "No such disk."
    otherComment = "Partitions number too distinct from required."

    def __init__(self, target: int, targets: list[{}], diskName: str):
        super().__init__("Number of partitions", target)
        self.targets = targets
        self.target=target
        self.diskName=diskName

    def run(self, student:Student) -> ResultatTest:
        numPartitions=-1
        hdds=student.hdds
        try:
            for disk in hdds:
                if disk["name"] == self.diskName:
                    numPartitions = len(disk["children"])
                    break
        except:
            return ResultatTest(0, self.target, "No disc", self.noDiskErrorMsg)

        for aTarget in self.targets:
            if aTarget["target"] == numPartitions:
                return ResultatTest(aTarget["grade"], self.target, numPartitions, aTarget["comment"])

        return ResultatTest(0, self.target, numPartitions, self.otherComment)

class CheckHDDPtTableType(Test):

    noDiskErrorMsg = "No such disk."
    otherComment="Partition table type is not as expected."
    okComment="Ok"

    def __init__(self, target: str, diskName: str):
        super().__init__("Disk partition table type", target)
        self.diskName=diskName

    def run(self, student: Student) -> ResultatTest:
        pttype=""
        hdds=student.hdds
        try:
            for disk in hdds:
                if disk["name"] == self.diskName:
                    pttype = disk["pttype"]
                    break
        except:
            return ResultatTest(0, self.target, "No disc", self.noDiskErrorMsg)
        
        if pttype==self.target:
            return ResultatTest(1, self.target, pttype, self.okComment)
        
        return ResultatTest(0, self.target, pttype, self.otherComment)


class CheckDiskSize(Test):

    noDiskErrorMsg = "Disk "+self.diskName+" not found."
    otherComment = "Disk size too far from required."

    def __init__(self, target: int, targets: list[{}], diskName: str):
        super().__init__("Number of partitions", target)
        self.targets = targets
        self.target=target
        self.diskName=diskName

    def run(self, student:Student) -> ResultatTest:
        diskSize=-1
        hdds=student.hdds
        try:
            for disk in hdds:
                if disk["name"] == self.diskName:
                    diskSize = disk["size"]
                    break
        except:
            return ResultatTest(0, self.target, "No disc", self.noDiskErrorMsg)

        (grade, comment)=gradeSizes(diskSize, targets)

        if grade == None:
            return ResultatTest(0, self.target, diskSize, self.otherComment)

        return ResultatTest(grade, self.target, diskSize, comment)

class CheckPartitionData(Test):

    noDiskErrorMsg = "Disk "+self.diskName+" not found."

    def __init__(self, target, targets, diskName:str, partitionName:str):
        """
        Checks partition attributes defined in the target argument.

        Arguments:
            - target: a dictionary of the form {"attribute_name1": value, "attribute_name2":value, ...}
            - targets: a dictionary of the form 
                {
                    "attribute_name1": {"weight": attributeWeight, "test": TestPartitionClass }
                }
            - diskName: name of the blockdevice that contains the partition to check.
            - partitionName: name of the partition to check.
        """
        super().__init__("Checks a partition attributes", target)
        self.targets=target
        self.diskName=diskName
        self.partitionName=partitionName

    def run(self, student:Student)->ResultatTest:
        partitionData=None
        hdds=student.hdds
        try:
            for disk in hdds:
                if disk["name"] == self.diskName:
                    for partition in disk["children"]:
                        if partition["name"]==self.partitionName:
                            partitionData=partition
                            break
                    break
        except:
            return ResultatTest(0, self.target, "No disc", self.noDiskErrorMsg)

        grade=0
        for attribute,value in target.items():
            grade+=self.targets[attribute]["weight"]*self.targets[attribute]["test"].checkPartition(partitionData)

    


def gradeSizes(size, listOfSizeRanges)->(float,str):
    """
    Returns the tuple (grade, comment) corresponding to the range to which
    the size corresponds.
    If size is outside of any range, the tuple (None, None) is returned.

    Arguments:
    - size: actual size to be graded.
    - listOfSizeRanges: a list of dictionaries of the form 
        { 
            "grade": float,
            "range": [maxSizeValue, minSizeValue],
            "comment": str
        }
        """
    for range in listOfSizeRanges:
        if size<=range["range"][0] and size>=range["range"][1]:
            return (range["grade"], range["comment"])
    
    return (None, None)



rubrica = {
    "RA1.1": [
        {
            "weight": 0.1,
            "test": CheckNumberPartitions( 6,
                                     [
                                         {"grade": 1, "target": 6,
                                             "comment": "Ok."},
                                         {"grade": 0.8, "target": 5,
                                             "comment": "1 partition is missing."},
                                         {"grade": 0.6, "target": 4,
                                             "comment": "2 partitions are missing."},
                                         {"grade": 0.4, "target": 3,
                                             "comment": "Too few partitions."},
                                         {"grade": 0.7, "target": 7,
                                             "comment": "Too many partitions."}
                                     ],
                                     "sdb")

        },
        {
            "weight": 0.01,
            "test": CheckHDDPtTableType("gpt", "sdb")
        },
        {
            "weight": 0.1,
            "test": CheckDiskSize( 21474836480,
                                     [
                                         {"grade": 1, "range": [21474836480, 21474836480],
                                             "comment": "Ok."},
                                         {"grade": 0, "range": [21474836480*10000000, 0],
                                             "comment": "Not the original disk."}
                                     ],
                                     "sdb")

        },

    ]
}

parser = argparse.ArgumentParser(
    formatter_class=argparse.ArgumentDefaultsHelpFormatter)

parser.add_help = True
parser.add_argument('-r', '--student-records',
                    default=recordsFile,
                    help='JSON file with students records. It is generated running the script with the --assign option.')


args = parser.parse_args()

if args.student_records != None and args.student_records != "":
    recordsFile = args.student_records


studentRecords = readStudentsJSON(recordsFile)

for aStudent in studentRecords.keys():
    print()
    print("*"*30)
    print(("Student: "+aStudent))
    for ra in rubrica.keys():
        for aTest in rubrica[ra]:
            print("-"*25)
            print(aTest["test"].description)
            print()
            resultat=aTest["test"].run(studentRecords[aStudent])
            print("Grade: "+str(resultat.nota*10))
            print("Resultat: "+str(resultat.resultat))
            print("Comment: "+str(resultat.comentari))
            print()
    print("*"*30)

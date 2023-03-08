#!/bin/python3

import argparse
from analisisvmlib import *
import traceback
import csv

recordsFile = "data/records.json"
moodleCsvPath = "data/moodle.csv"

class ResultTest:
    """
    This class groups data of a test result:
    - grade: grade result between 0 and 1
    - target: the expected result of the test
    - result: the real result of the test
    - comment: a comment to the student about the result
    """

    def __init__(self, grade: str, target: str, result: float, comment: str):
        self.grade = grade
        self.target = target
        self.result = result
        self.comment = comment


class Test:
    """
    Base class of test classes.
    Childs of Test must have a description and a target (expected result of the test).
    They must implement a run method which takes a student record and returns a ResultTest.
    """

    def __init__(self, description: str, target):
        self.description = description
        self.target = target

    def run(self, student: Student) -> ResultTest:
        pass


class TestDefinition:
    """
    Groups the data of a test that must be run.
    """

    seq = 1

    def __init__(self, id: str, title: str, test: Test):
        if id == "":
            self.id = "T"+str(self.seq)
        else:
            self.id = id
        self.title = title
        # self.weight = weight
        self.test = test
        self.seq += 1


class CheckNumberPartitions(Test):

    noDiskErrorMsg = "No such disk."
    otherComment = "Partitions number too distinct from required."

    def __init__(self, target: int, targets: list[{}], diskName: str):
        super().__init__("Number of partitions", target)
        self.targets = targets
        self.target = target
        self.diskName = diskName

    def run(self, student: Student) -> ResultTest:
        numPartitions = -1
        hdds = student.hdds
        try:
            for disk in hdds:
                if disk["name"] == self.diskName:
                    numPartitions = len(disk["children"])
                    break
        except:
            return ResultTest(0, self.target, "No disc", self.noDiskErrorMsg)

        for aTarget in self.targets:
            if aTarget["target"] == numPartitions:
                return ResultTest(aTarget["grade"], self.target, numPartitions, aTarget["comment"])

        return ResultTest(0, self.target, numPartitions, self.otherComment)


class CheckNumberPartitionsOfType(Test):
    """
    Checks the number of partitions of a given type.
    In 'pttypename' you have to pass a list of possible partitions name.
    In 'ptTypeWeigths' you have to pass a weight for each of the possible partitions name.
    The final grade is the grade defined in targets (dependent of the number of partitions found),
    weighted by each of the weights given ( [target grade]*sum(weights)/number_partitions).

    For example, if pttypename=['Microsoft Basic Data','Microsoft Reserved Data'], and ptTypeWeights=[1,0.8],
    then, if grade for target=2 is 1, and one partition 'Microsoft Basic Data' is found, and another partition 
    'Microsoft Reserved Data' is also found, the final grade will be 1*(1+0.8)/2=0.9
    """

    noDiskErrorMsg = "No such disk."
    otherComment = "Partitions number too distinct from required."

    def __init__(self, target: int, targets: list[{}], pttypename: list[str], ptTypeWeights: list[float], diskName: str):
        super().__init__("Number of partitions", target)
        self.targets = targets
        self.target = target
        self.diskName = diskName
        self.pttypename = pttypename
        self.ptTypeWeights = ptTypeWeights

    def run(self, student: Student) -> ResultTest:
        numPartitions = 0
        weightedNumPartitions = 0
        hdds = student.hdds
        try:
            for disk in hdds:
                if disk["name"] == self.diskName:
                    for partition in disk["children"]:
                        if partition["parttypename"] in self.pttypename:
                            numPartitions += 1
                            weightedNumPartitions += self.ptTypeWeights[self.pttypename.index(
                                partition["parttypename"])]
                    break
        except:
            return ResultTest(0, self.target, "No disc", self.noDiskErrorMsg)

        for aTarget in self.targets:
            if aTarget["target"] == numPartitions:
                return ResultTest(aTarget["grade"]*(weightedNumPartitions/numPartitions if numPartitions != 0 else 1), self.target, numPartitions, aTarget["comment"])

        return ResultTest(0, self.target, numPartitions, self.otherComment)


class CheckHDDPtTableType(Test):

    noDiskErrorMsg = "No such disk."
    otherComment = "Partition table type is not as expected."
    okComment = "Ok"

    def __init__(self, target: str, diskName: str):
        super().__init__("Disk partition table type", target)
        self.diskName = diskName

    def run(self, student: Student) -> ResultTest:
        pttype = ""
        hdds = student.hdds
        try:
            for disk in hdds:
                if disk["name"] == self.diskName:
                    pttype = disk["pttype"]
                    break
        except:
            return ResultTest(0, self.target, "No disc", self.noDiskErrorMsg)

        if pttype == self.target:
            return ResultTest(1, self.target, pttype, self.okComment)

        return ResultTest(0, self.target, pttype, self.otherComment)


class CheckDiskSize(Test):

    def __init__(self, target: int, targets: list[{}], diskName: str):
        super().__init__("Number of partitions", target)
        self.targets = targets
        self.target = target
        self.diskName = diskName
        self.noDiskErrorMsg = "Disk "+self.diskName+" not found."
        self.otherComment = "Disk size too far from required."

    def run(self, student: Student) -> ResultTest:
        diskSize = -1
        hdds = student.hdds
        try:
            for disk in hdds:
                if disk["name"] == self.diskName:
                    diskSize = disk["size"]
                    break
        except:
            return ResultTest(0, self.target, "No disc", self.noDiskErrorMsg)

        (grade, comment) = gradeSizes(diskSize, self.targets)

        if grade == None:
            return ResultTest(0, self.target, diskSize, self.otherComment)

        return ResultTest(grade, self.target, diskSize, comment)


class CheckPartitionsNumberOfSize(Test):
    """
    Checks how many partitions are sized in the given range.
    """

    def __init__(self, target: int, targets: list[{}], minSize, maxSize, diskName: str):
        super().__init__("Number of partitions with size between " +
                         str(minSize)+" and "+str(maxSize)+" bytes.", target)
        self.maxSize = maxSize
        self.target = target
        self.targets = targets
        self.diskName = diskName
        self.noDiskErrorMsg = "Disk "+self.diskName+" not found."
        self.minSize = minSize
        self.otherComment = "Number of partitions too far from required"

    def run(self, student: Student) -> ResultTest:
        numPartitions = 0
        hdds = student.hdds
        try:
            for disk in hdds:
                if disk["name"] == self.diskName:
                    for partition in disk["children"]:
                        if self.minSize <= partition["size"] <= self.maxSize:
                            numPartitions += 1
                    break
        except:
            return ResultTest(0, self.target, "No disc", self.noDiskErrorMsg)

        for aTarget in self.targets:
            if numPartitions == aTarget["target"]:
                return ResultTest(aTarget["grade"], self.target, numPartitions, aTarget["comment"])

        return ResultTest(0, self.target, numPartitions, self.otherComment)


class FindSystem(Test):
    """
    Searches for a bootable system with a required distribution name. If more
    than one system is found, then assigns the system which best fits the expected size.

    If the system is found, it changes the systems key in the student record for the
    systemId
    """

    def __init__(self, target, distributionName: str, size: int, systemId: str):
        super().__init__("Checks system attributes", target)
        self.distributionName = distributionName
        self.size = size
        self.systemId = systemId
        self.noSystemErrorMsg = "No system found."

    def searchSystem(self, systems: {}) -> {}:
        """
        Searches and assigns the boot system that fits with distribution name and size.
        """
        possibleSystems = []
        for system in systems.values():
            try:
                if system["distribution"] == self.distributionName:
                    possibleSystems.append(system)
            except Exception as e:
                print("Error in system "+str(system))
                print(str(e))
                traceback.print_exc()

        assignedSystem = None
        sizeError = 2**31
        for system in possibleSystems:
            try:
                if abs(system["root_data"]["size"]-self.size) < sizeError:
                    sizeError = abs(system["root_data"]["size"]-self.size)
                    assignedSystem = system
            except Exception as e:
                print("Error in system "+str(system))
                print(str(e))
                traceback.print_exc()

        return assignedSystem

    def run(self, student: Student) -> ResultTest:
        system = self.searchSystem(student.systems)
        if system == None:
            return ResultTest(0, self.target, "", self.noSystemErrorMsg)

        if system["root_dev"] in student.systems:
            student.systems.pop(system["root_dev"])
        student.systems[self.systemId] = system
        return ResultTest(1, self.target, system["root_dev"], "System found on "+system["root_dev"])


class CheckRootPassword(Test):
    """
    Checks if password of root user is correct.

    You should probably have to run FindSystem test before this test.
    """

    def __init__(self, target, systemId: str):
        super().__init__("Checks system attributes", target)
        self.systemId = systemId
        self.noSystemErrorMsg = "No system found."

    def run(self, student: Student) -> ResultTest:

        if self.systemId not in student.systems:
            return ResultTest(0, self.target, "", self.noSystemErrorMsg)

        if "users" not in student.systems[self.systemId]:
            return ResultTest(0, self.target, "No users info", "Could'nt find users info.")

        if "root" not in student.systems[self.systemId]["users"]:
            return ResultTest(0, self.target, "No root user", "Could'nt find root user info.")

        if "usr_password" not in student.systems[self.systemId]["users"]["root"]:
            return ResultTest(0, self.target, "No root password", "Could'nt check root password.")

        if student.systems[self.systemId]["users"]["root"]["usr_password"] == 0:
            return ResultTest(0, self.target, "Wrong password", "root password is not as required.")

        return ResultTest(1, self.target, self.target, "Ok")


class CheckUserHome(Test):
    """
    Checks if home folder of user exists.

    You should probably have to run FindSystem test before this test.
    """

    def __init__(self, target, systemId: str, userName: str):
        super().__init__("Checks system attributes", target)
        self.systemId = systemId
        self.noSystemErrorMsg = "No system found."
        self.userName = userName

    def run(self, student: Student) -> ResultTest:

        if self.systemId not in student.systems:
            return ResultTest(0, self.target, "", self.noSystemErrorMsg)

        if "users" not in student.systems[self.systemId]:
            return ResultTest(0, self.target, "No users info", "Could'nt find users info.")

        if self.userName not in student.systems[self.systemId]["users"]:
            return ResultTest(0, self.target, "No "+self.userName+" user", "Could'nt find "+self.userName+" user info.")

        if "usr_home" not in student.systems[self.systemId]["users"][self.userName]:
            return ResultTest(0, self.target, "No "+self.userName+" home folder", "Could'nt check "+self.userName+" home folder.")

        if student.systems[self.systemId]["users"][self.userName]["usr_home"] == 0:
            return ResultTest(0, self.target, "No user home", self.userName+" home folder not found.")

        return ResultTest(1, self.target, self.target, "Ok")


class CheckUserPassword(Test):
    """
    Checks if password of user is correct.

    You should probably have to run FindSystem test before this test.
    """

    def __init__(self, target, systemId: str, userName: str):
        super().__init__("Checks system attributes", target)
        self.systemId = systemId
        self.noSystemErrorMsg = "No system found."
        self.userName = userName

    def run(self, student: Student) -> ResultTest:

        if self.systemId not in student.systems:
            return ResultTest(0, self.target, "", self.noSystemErrorMsg)

        if "users" not in student.systems[self.systemId]:
            return ResultTest(0, self.target, "No users info", "Could'nt find users info.")

        if self.userName not in student.systems[self.systemId]["users"]:
            return ResultTest(0, self.target, "No "+self.userName+" user", "Could'nt find "+self.userName+" user info.")

        if "usr_password" not in student.systems[self.systemId]["users"][self.userName]:
            return ResultTest(0, self.target, "No "+self.userName+" password", "Could'nt check "+self.userName+" password.")

        if student.systems[self.systemId]["users"][self.userName]["usr_password"] == 0:
            return ResultTest(0, self.target, "Wrong password", self.userName+" password is not as required.")

        return ResultTest(1, self.target, self.target, "Ok")


class CheckMountDiff(Test):
    """
    Checks if two folders of a system are mounted in diferent devices.
    As of now, folder must be one of 'root_data','home_data', 'opt_data' or 'efi_data' 
    (corresponding to /root , /home, /opt and /boot/efi folders).

    You should probably have to run FindSystem test before this test.
    """

    def __init__(self, target, systemId: str, folder1: str, folder2: str):
        super().__init__("Checks system attributes", target)
        self.systemId = systemId
        self.noSystemErrorMsg = "No system found."
        self.folder1 = folder1
        self.folder2 = folder2

    def run(self, student: Student) -> ResultTest:

        if self.systemId not in student.systems:
            return ResultTest(0, self.target, "", self.noSystemErrorMsg)

        if self.folder1 not in student.systems[self.systemId]:
            return ResultTest(0, self.target, "No "+self.folder1+" info", "Could'nt find "+self.folder1+" info.")

        if self.folder2 not in student.systems[self.systemId]:
            return ResultTest(0, self.target, "No "+self.folder2+" info", "Could'nt find "+self.folder2+" info.")

        if student.systems[self.systemId][self.folder1]["dev"] == "" or student.systems[self.systemId][self.folder2]["dev"] == "" or student.systems[self.systemId][self.folder1]["dev"] == student.systems[self.systemId][self.folder2]["dev"]:
            return ResultTest(0, self.target, "Same partition", "Both folders, "+self.folder1+" and "+self.folder2+", are in the same partition.")

        return ResultTest(1, self.target, self.target, "Ok")


class CheckSharedPartition(Test):
    """
    Checks if two systems share the same partition for a folder.
    As of now, folder must be one of 'root_data','home_data', 'opt_data' or 'efi_data' 
    (corresponding to /root , /home, /opt and /boot/efi folders).

    You should probably have to run FindSystem test before this test.
    """

    def __init__(self, target, systemId1: str, systemId2: str, folder: str):
        super().__init__("Checks system attributes", target)
        self.systemId1 = systemId1
        self.systemId2 = systemId2
        self.noSystemErrorMsg = "No system found."
        self.folder = folder

    def run(self, student: Student) -> ResultTest:

        if self.systemId1 not in student.systems:
            return ResultTest(0, self.target, "", "System "+self.systemId1+" not found.")

        if self.systemId2 not in student.systems:
            return ResultTest(0, self.target, "", "System "+self.systemId2+" not found.")

        if self.folder not in student.systems[self.systemId1]:
            return ResultTest(0, self.target, "No "+self.folder+" info on system "+self.systemId1, "Could'nt find "+self.folder+" info on system "+self.systemId1)

        if self.folder not in student.systems[self.systemId2]:
            return ResultTest(0, self.target, "No "+self.folder+" info on system "+self.systemId2, "Could'nt find "+self.folder+" info on system "+self.systemId2)

        if student.systems[self.systemId1][self.folder]["dev"] == "" or student.systems[self.systemId2][self.folder]["dev"] == "" or student.systems[self.systemId1][self.folder]["dev"] != student.systems[self.systemId2][self.folder]["dev"]:
            return ResultTest(0, self.target, "Not shared", "System "+self.systemId1+" and "+self.systemId2+", are not sharing "+self.folder)

        return ResultTest(1, self.target, self.target, "Ok")


class CheckSystemAttribute(Test):
    """
    Checks if the system has an attribute with the given value.

    You should probably have to run FindSystem test before this test.
    """

    def __init__(self, target, systemId: str, attribute: str, targets: list[{}]):
        super().__init__("Checks system attributes", target)
        self.systemId = systemId
        self.noSystemErrorMsg = "No system found."
        self.attribute = attribute
        self.targets = targets
        self.otherComment = "Value out of requirements"

    def run(self, student: Student) -> ResultTest:

        if self.systemId not in student.systems:
            return ResultTest(0, self.target, "", self.noSystemErrorMsg)

        if self.attribute not in student.systems[self.systemId]:
            return ResultTest(0, self.target, "No "+self.folder1+" info", "Could'nt find "+self.attribute+" info.")

        for aTarget in self.targets:
            if student.systems[self.systemId][self.attribute] == aTarget["target"]:
                return ResultTest(aTarget["grade"], self.target, aTarget["target"], aTarget["comment"])

        return ResultTest(0, self.target, student.systems[self.systemId][self.attribute], self.otherComment)


class CheckPartitionData(Test):
    """
    UNDER CONSTRUCTION
    """

    def __init__(self, target, targets, diskName: str, partitionName: str):
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
        self.targets = target
        self.diskName = diskName
        self.partitionName = partitionName
        noDiskErrorMsg = "Disk "+self.diskName+" not found."

    def run(self, student: Student) -> ResultTest:
        partitionData = None
        hdds = student.hdds
        try:
            for disk in hdds:
                if disk["name"] == self.diskName:
                    for partition in disk["children"]:
                        if partition["name"] == self.partitionName:
                            partitionData = partition
                            break
                    break
        except:
            return ResultTest(0, self.target, "No disc", self.noDiskErrorMsg)

        grade = 0
        for attribute, value in target.items():
            grade += self.targets[attribute]["weight"] * \
                self.targets[attribute]["test"].checkPartition(partitionData)


def gradeSizes(size, listOfSizeRanges) -> (float, str):
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
        if size <= range["range"][0] and size >= range["range"][1]:
            return (range["grade"], range["comment"])

    return (None, None)


def runChecksStudent(studentRecord: {}) -> dict[str, ResultTest]:
    results = {}
    for ra in checks.keys():
        aTest: TestDefinition
        for aTest in checks[ra]:
            results[aTest.id] = aTest.test.run(studentRecord)
    return results


def gradeStudent(studentRecord: {}, testsResult: dict[str, ResultTest]):
    grades = {}
    for ra in rubrica:
        grade = 0
        sumOfWeights = 0
        for aGrade in ra["grades"]:
            grade += testsResult[aGrade["test"]].grade*aGrade["weight"]
            sumOfWeights += aGrade["weight"]
        grades[ra["id"]] = grade/sumOfWeights
    return grades


def studentTestsReport(testsResult: dict[str, ResultTest], checks):
    testsReport = {}
    for group in checks.keys():
        for check in checks[group]:
            checkResult = None
            if check.id in testsResult:
                checkResult = testsResult[check.id]
            testsReport[check.id] = {
                "testId": check.id,
                "desc": check.title,
                "group": group,
                "result": checkResult.__dict__
            }
    return testsReport


def listGrades(student: Student):
    for ra, grade in student.grades.items():
        print(ra+" : "+"{:.2f}".format(grade*10))

def moodleCSV(studentRecords,moodleCsvPath):
    # Writes header
    writer=csv.writer(open(moodleCsvPath,"w"))
    writer.writerow(["student","mail"]+[ra["id"] for ra in rubrica])

    student:Student
    for student in studentRecords.values():
        # writer.writerow([str(student),student.email]+[student.grades[ra]*10 for ra in student.grades ])
        writer.writerow([str(student),student.email]+["{:.2f}".format(student.grades[ra]*10) for ra in student.grades ])


checks = {
    "Disk partitioning": [
        TestDefinition("HDD01", "Disk size", CheckDiskSize(21474836480,
                                                           [
                                                               {"grade": 1, "range": [21474836480, 21474836480],
                                                                "comment": "Ok."},
                                                               {"grade": 0, "range": [21474836480*10000000, 0],
                                                                   "comment": "Not the original disk."}
                                                           ],
                                                           "sdb")),
        TestDefinition("HDD02", "Partition table type",
                       CheckHDDPtTableType("gpt", "sdb")),
        TestDefinition("HDD03", "Partitions number", CheckNumberPartitions(6,
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
                                                                           "sdb")),
        TestDefinition("HDD04", "Number of partitions for EFI boot (between 80 and 500 Mb)", CheckPartitionsNumberOfSize(1, [
            {"grade": 1, "target": 1, "comment": "Ok."},
            {"grade": 0, "target": 0,
                "comment": "No partition with correct size for EFI found."}
        ], 75*(1024**2), 510*(1024**2), "sdb")),
        TestDefinition("HDD05", "Debian partition size must be 2999975936 bytes", CheckPartitionsNumberOfSize(1, [
            {"grade": 1, "target": 1, "comment": "Ok."},
            {"grade": 0, "target": 0,
                "comment": "Debian partition not found or it has been modified."}
        ], 2999975930, 2999975940, "sdb")),
        TestDefinition("HDD06", "Number of partitions of 3Gb (Alpine and win data)", CheckPartitionsNumberOfSize(2, [
            {"grade": 1, "target": 2, "comment": "Ok."},
            {"grade": 0.8, "target": 4,
                "comment": "More partitions found than required."},
            {"grade": 0.4, "target": 5, "comment": "Too many 3Gb partitions found."},
            {"grade": 0.4, "target": 3,
                "comment": "More partitions found than required."},
            {"grade": 0.2, "target": 1, "comment": "1 partition missing."},
            {"grade": 0, "target": 0, "comment": "No partition of 3Gb found."}
        ], 2.8*(1024**3), 3.2*(1024**3), "sdb")),
        TestDefinition("HDD07", "Number of partitions bigger than 8G (user data - /home)", CheckPartitionsNumberOfSize(1, [
            {"grade": 1, "target": 1, "comment": "Ok."},
            {"grade": 0.4, "target": 2,
                "comment": "Too many partitions bigger than 8Gb found, you are wasting disk space."},
            {"grade": 0, "target": 0, "comment": "No partition bigger than 8Gb found."}
        ], 7.9*(1024**3), 510*(1024**3), "sdb")),
        TestDefinition("HDD08", "EFI partition", CheckNumberPartitionsOfType(1, [
            {"grade": 1, "target": 1, "comment": "Ok."},
            {"grade": 0, "target": 0, "comment": "No EFI partition found."}
        ], ["EFI System"], [1], "sdb")),
        TestDefinition("HDD09", "'Linux filesystem' partitions", CheckNumberPartitionsOfType(3, [
            {"grade": 1, "target": 3, "comment": "Ok."},
            {"grade": 0.8, "target": 4, "comment": "Too many partitions."},
            {"grade": 0.5, "target": 5, "comment": "Too many partitions."},
            {"grade": 0.6, "target": 2, "comment": "Missing 1 partition."},
            {"grade": 0.3, "target": 1, "comment": "Missing 2 partitions."},
            {"grade": 0, "target": 0, "comment": "No 'Linux filesystem' partition found."}
        ], ["Linux filesystem"], [1], "sdb")),
        TestDefinition("HDD10", "'Microsoft Basic Data' partition", CheckNumberPartitionsOfType(1, [
            {"grade": 1, "target": 1, "comment": "Ok."},
            {"grade": 0.4, "target": 2, "comment": "Too many partitions."},
            {"grade": 0, "target": 0, "comment": "No Microsoft partition found."}
        ], ["Microsoft basic data", "Microsoft reserved", "Microsoft Storage Spaces"], [1, 0.8, 0.7], "sdb")),
        TestDefinition("HDD11", "'Linux swap' partition", CheckNumberPartitionsOfType(1, [
            {"grade": 1, "target": 1, "comment": "Ok."},
            {"grade": 0.3, "target": 2, "comment": "Too many swap partitions."},
            {"grade": 0, "target": 0, "comment": "No swap partition found."}
        ], ["Linux swap", "Linux swap / Solaris"], [1, 0.8], "sdb")),
    ],
    "Debian System": [
        TestDefinition("DEB01", "Debian system", FindSystem(
            "/dev/sd*", "debian", 3021608, "debian")),
        TestDefinition("DEB02", "root password",
                       CheckRootPassword("ASdqwe!23", "debian")),
        TestDefinition("DEB03", "alumno home folder",
                       CheckUserHome("/home/alumno", "debian", "alumno")),
        TestDefinition("DEB04", "alumno password",
                       CheckUserPassword("ASdqwe!23", "debian", "alumno")),
        TestDefinition("DEB05", "Home partition mounted", CheckMountDiff(
            "home and root partitions are diferent", "debian", "root_data", "home_data")),
        TestDefinition("DEB06", "Spanish keyboard", CheckSystemAttribute(1, "debian", "spanish_kbd", [
                       {"grade": 1, "target": 1, "comment": "ok"}, {"grade": 0, "target": 0, "comment": "Not Spanish keyboard"}])),
        TestDefinition("DEB07", "Spanish time", CheckSystemAttribute(1, "debian", "spanish_time", [
                       {"grade": 1, "target": 1, "comment": "ok"}, {"grade": 0, "target": 0, "comment": "Not Spanish time"}])),
    ],
    "Alpine System": [
        TestDefinition("ALP01", "Alpine system", FindSystem(
            "/dev/sd*", "alpine", 3021608, "alpine")),
        TestDefinition("ALP02", "Alpine root password",
                       CheckRootPassword("ASdqwe!23", "alpine")),
        TestDefinition("ALP03", "Alpine alumno home folder",
                       CheckUserHome("/home/alumno", "alpine", "alumno")),
        TestDefinition("ALP04", "Alpine alumno password",
                       CheckUserPassword("ASdqwe!23", "alpine", "alumno")),
        TestDefinition("ALP05", "Alpine home partition mounted", CheckMountDiff(
            "home and root partitions are diferent", "alpine", "root_data", "home_data")),
        TestDefinition("ALP06", "Home partition shared with Debian", CheckSharedPartition(
            "shared", "alpine", "debian", "home_data")),
        TestDefinition("ALP07", "Alpine Spanish keyboard", CheckSystemAttribute(1, "alpine", "spanish_kbd", [
                       {"grade": 1, "target": 1, "comment": "ok"}, {"grade": 0, "target": 0, "comment": "Not Spanish keyboard"}])),
        TestDefinition("ALP08", "Alpine Spanish time", CheckSystemAttribute(1, "alpine", "spanish_time", [
                       {"grade": 1, "target": 1, "comment": "ok"}, {"grade": 0, "target": 0, "comment": "Not Spanish time"}])),
    ]
}

rubrica = [
    {
        "id": "RA1.1",
        "desc": "Instal·la sistemes operatius, analitzant les seves característiques i interpretant la documentació tècnica.",
        "grades": [
            {"test": "HDD01", "weight": 1},  # disk size
            {"test": "HDD02", "weight": 1},  # partitions table type
            {"test": "HDD03", "weight": 3},  # partitions number
            {"test": "HDD04", "weight": 1},
            {"test": "HDD05", "weight": 1},
            {"test": "HDD06", "weight": 6},
            {"test": "HDD07", "weight": 5},
            {"test": "HDD08", "weight": 1},
            {"test": "HDD09", "weight": 6},
            {"test": "HDD10", "weight": 4},
            {"test": "HDD11", "weight": 4},
            {"test": "DEB01", "weight": 4},
            {"test": "ALP01", "weight": 6},
        ]
    },
    {
        "id": "RA1.2",
        "desc": "Configura el programari de base, atenent a les necessitats d'explotació del sistema informàtic.",
        "grades": [
            {"test": "DEB02", "weight": 1},
            {"test": "DEB03", "weight": 2},
            {"test": "DEB04", "weight": 2},
            {"test": "DEB05", "weight": 4},
            {"test": "DEB06", "weight": 1},
            {"test": "DEB07", "weight": 1},
            {"test": "ALP02", "weight": 3},
            {"test": "ALP03", "weight": 5},
            {"test": "ALP04", "weight": 5},
            {"test": "ALP05", "weight": 8},
            {"test": "ALP06", "weight": 8},
            {"test": "ALP07", "weight": 3},
            {"test": "ALP08", "weight": 3},
        ]
    }
]

parser = argparse.ArgumentParser(
    formatter_class=argparse.ArgumentDefaultsHelpFormatter)

parser.add_help = True
parser.add_argument('-r', '--student-records',
                    default=recordsFile,
                    help='JSON file with students records.')
parser.add_argument(
    '--student', help="Runs the option only for the given student.")
parser.add_argument(
    '--moodle-csv', help="Generates the csv file to import grades to Moodle.")
parser.add_argument('--no-checks', action='store_true',
    help="Avoid to run check tests. Use if you only want to list actual resutls.")
parser.add_argument('--ls-grades', action='store_true',
    help="Prints the grades of the students.")


args = parser.parse_args()

if args.student_records != None and args.student_records != "":
    recordsFile = args.student_records


studentRecords = readStudentsJSON(recordsFile)

if args.student != None and args.student != "":
    print()
    print("*"*30)
    print(("Student: "+str(studentRecords[args.student])))
    if not args.no_checks:
        print("Running checks")
        testsResult = runChecksStudent(studentRecords[args.student])
        studentRecords[args.student].tests = studentTestsReport(
            testsResult, checks)
        studentRecords[args.student].grades = gradeStudent(
            studentRecords[args.student], testsResult)
        saveStudentRecords(studentRecords, recordsFile)
    if args.ls_grades:
        listGrades(studentRecords[args.student])
    print("*"*30)

else:
    for aStudent in studentRecords.keys():
        print()
        print("*"*30)
        print(("Student: "+str(studentRecords[aStudent])))
        if not args.no_checks:
            print("Running checks")
            testsResult = runChecksStudent(studentRecords[aStudent])
            studentRecords[aStudent].tests = studentTestsReport(
                testsResult, checks)
            studentRecords[aStudent].grades = gradeStudent(
                studentRecords[aStudent], testsResult)
            saveStudentRecords(studentRecords, recordsFile)
        if args.ls_grades:
            listGrades(studentRecords[aStudent])
        print("*"*30)

if args.moodle_csv != None:
    if args.moodle_csv != "":
        moodleCsvPath=args.moodle_csv
    moodleCSV(studentRecords,moodleCsvPath)
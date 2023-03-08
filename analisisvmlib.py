
import json

class Student:


    def __init__(self, name: str, surname: str, email: str):
        self.name = name
        self.surname = surname
        self.email = email
        self.ovafile = ""
        self.vmName = ""
        self.hdds = []
        self.systems = {}
        self.tests = {}
        self.grades = {}

    @classmethod
    def fromJSON(cls, jsonData):
        newStudent = cls(jsonData["name"],
                         jsonData["surname"], jsonData["email"])
        if "ovafile" in jsonData:
            newStudent.ovafile = jsonData["ovafile"]
        if "vmName" in jsonData:
            newStudent.vmName = jsonData["vmName"]
        if "hdds" in jsonData:
            newStudent.hdds = jsonData["hdds"]
        if "systems" in jsonData:
            newStudent.systems = jsonData["systems"]
        if "tests" in jsonData:
            newStudent.tests = jsonData["tests"]
        if "grades" in jsonData:
            newStudent.grades = jsonData["grades"]

        return newStudent

    def __str__(self):
        return self.surname+", "+self.name

    def toJSON(self):
        return {
            "name": self.name,
            "surname": self.surname,
            "email": self.email,
            "ovafile": self.ovafile,
            "vmName": self.vmName,
            "hdds": self.hdds,
            "systems": self.systems,
            "tests" : self.tests,
            "grades" : self.grades
        }



def readStudentsJSON(recordsFile: str):
    data = json.load(open(recordsFile, "r"))
    return {id: Student.fromJSON(student) for id, student in data.items()}


def saveStudentRecords(students, recordsFile):
    json.dump({id: student.toJSON() for id, student in students.items()}, open(
        recordsFile, 'w'), indent=3, ensure_ascii=False)


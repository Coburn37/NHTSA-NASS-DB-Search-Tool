import json

from nassDB import NASSDB, NASSDBData

#Go into each file and get column info on each db
#Present this to user and let them form a search
#Take this search back to the database and search

#Search
#Find relative database for search
#Search those databases to find the caseids of all relevant data
#Take those caseids and search all other databases for their information

'''class SearchTerm():
    def __init__(self, dbName, colName, searchValue, compareFunc):
        self.dbName = dbName
        self.colName = colName
        self.searchValue = searchValue
        self.compareFunc = compareFunc
    
    def compare(self, value):
        return self.compareFunc(value, self.searchValue)

'''

if __name__ == "__main__":
    print("NASS Search Tool (c) Peter Fornari 2015\nMilestone 1: Print all records, output as unstructured JSON\n")
    
    rootPath = "./nassDB/2011/"
    fDBInfo = open("nassDBInfo.json", "r")
    dbInfo = json.loads(fDBInfo.read())
    
    casesFound = {}
    for db in dbInfo["dbs"]:
        print("Loading up " + db["prettyName"] + "...")
        data = NASSDBData(rootPath + db["fileName"])
        nassDB = NASSDB(data)
        cases = nassDB.getCases()
        for caseNum, case in cases.items():
            if not caseNum in casesFound:
                casesFound[caseNum] = case
            else:
                casesFound[caseNum].update(case)
    
    
    print("Outputting matches")
    f = open("output.txt", "w")
    for caseNum, case in casesFound.items():
        s = "\n------CASEID: " + caseNum + "--------\n"
        substr = ""
        for k, v in case.items():
            substr += "[" + str(k) + " = " + str(v) + "]     "
            if len(substr) > 200:
                s += substr + "\n"
                substr = ""
        s += substr
        
        f.write(s)

    print("Success!")




    '''print("Searching DBs")
    def matchIt(src, test):
        return test in src

    searchTerms = [
        SearchTerm("acc_desc", "TEXT71", "dog", matchIt),
        SearchTerm("typ_acc", "TEXT66", "dog", matchIt),
        SearchTerm("veh_pro", "TEXT81", "dog", matchIt),
        SearchTerm("pers_pro", "TEXT91", "dog", matchIt)
    ]

    matches = []
    for dbName, db in dbs.items():
        sts = []
        for st in searchTerms:
            if st.dbName == dbName:
                sts.append(st)
        
        if not sts:
            continue
        
        print("Searching: " + dbName)    
        matches += db.search(sts)

    print("Getting relevant records")
    rows = {}
    for dbName, db in dbs.items():
        print("Searching: " + dbName)
        kvs = db.getCaseIDs(matches)
        for kv in kvs:
            caseID = kv["CASEID"]
            if not caseID in rows:
                rows[caseID] = kv
            else:
                for kNew, vNew in kv.items():
                    if kNew in rows[caseID]:
                        if vNew and rows[caseID][kNew]:
                            rows[caseID][kNew] += vNew
                    else:
                        rows[caseID][kNew] = vNew
                #rows[caseID].update(kv)'''
import fitz  # this is pymupdf
import sys
import csv
import re

VALUE_INDX_IN_BLOCK = 4
FLATS_BY_ENTRANCE = [321, 598, 902, 1223]

srcFileName = sys.argv[1]


allBlocks = []
allUsers = {}

def getValueFromBlock(targetText, startIndx):      
    i = startIndx
    listLen = len(allBlocks)
    while i < listLen:
        curBlock = allBlocks[i]
        if targetText in curBlock[VALUE_INDX_IN_BLOCK]:
            valueStart = curBlock[VALUE_INDX_IN_BLOCK].find("\n", len(targetText))
            value = curBlock[VALUE_INDX_IN_BLOCK][valueStart:]
            value = value.replace("\n"," ").strip()
            return (i + 1, value)
        i += 1
    return (-1, "not found")  

def getObjectFieldValue(startIndx):
    return getValueFromBlock("объект долевого строительства:", startIndx)

def getAgreementFieldValue(startIndx):
    return getValueFromBlock("еквизиты договора:", startIndx)

def getDateFieldValue(startIndx):
    return getValueFromBlock("дата государственной регистрации:", startIndx)

def getNameFieldValue(startIndx):      
    (i, name) = getValueFromBlock("участники долевого строительства:", startIndx)
    while "сведения о залоге прав требования" not in allBlocks[i][VALUE_INDX_IN_BLOCK] and "полное наименование должности" not in allBlocks[i][VALUE_INDX_IN_BLOCK]:
        name += f", {allBlocks[i][VALUE_INDX_IN_BLOCK]}"
        i+=1

    name = name.replace("«","\"").replace("»","\"")
    return i, name

def getObjectArea(object):
    areaMatch = re.search('(\d+\.\d+) кв\.м', object, re.IGNORECASE)
    if areaMatch:
        return float(areaMatch.group(1))
    return float(0)

def fixFlatNum(entrance, flatNum):
    #if defined wrong entrance, fix it
    if entrance == 1 and flatNum > FLATS_BY_ENTRANCE[0]:
        while FLATS_BY_ENTRANCE[entrance] <= flatNum:
            entrance += 1
    #if we found num in "old" style, convert it to new style
    if entrance > 1 and flatNum < FLATS_BY_ENTRANCE[entrance - 1]:
        flatNum += FLATS_BY_ENTRANCE[entrance - 2]
    #dont know why, but all flats num increased by one
    flatNum += 1
    return entrance, flatNum

def getFlatInfo(object):
    flatInfoMatch = re.search('.*квартира.*(\d)-(\d+).*этаж.*?(\d+)', object, re.IGNORECASE)
    if flatInfoMatch:
        entrance = int(flatInfoMatch.group(1))
        flatNumOldStyle = int(flatInfoMatch.group(2))
        floorNumber = int(flatInfoMatch.group(3))
        (fixedEntrance, flatNumNewStyle) = fixFlatNum(entrance, flatNumOldStyle)
        return (fixedEntrance, flatNumNewStyle, floorNumber)
    return (None, None, None)

def parseUser(startIndx):
    (curBlockIndex, agreement) = getAgreementFieldValue(startIndx)
    if curBlockIndex == -1:
        return -1
    (curBlockIndex, date) = getDateFieldValue(startIndx)
    (curBlockIndex, object) = getObjectFieldValue(startIndx)
    area = getObjectArea(object)  
    (entrance, flatNum, floorNumber) = getFlatInfo(object)
    (curBlockIndex, name) = getNameFieldValue(startIndx)

    newUser = {
        'FIO':name, 
        'Agreements':[agreement], 
        'Objects' : [object], 
        'Date' : date, 
        'Area' : area,
        'Entrance' : entrance,
        'FlatNum' : flatNum,
        'FloorNumber' : floorNumber        
        }
    if name in allUsers:
        allUsers[name]['Agreements'] += newUser['Agreements']
        #fix double counting of area on assignment
        if newUser['Objects'][0] not in allUsers[name]['Objects']:
            allUsers[name]['Objects'] += newUser['Objects']        
            allUsers[name]['Area'] += newUser['Area']
    else:
        allUsers[newUser['FIO']] = newUser
    return curBlockIndex + 1


with fitz.open(srcFileName) as doc:
    for page in doc:                     
        allBlocks += page.getText("blocks")

curBlockIndex = 0

while curBlockIndex >= 0:
    curBlockIndex = parseUser(curBlockIndex)        

with open('result.csv', 'w') as csvfile:    
    fieldNames = ['FIO', 'Area', 'Entrance', 'FlatNum', 'FloorNumber', 'Objects', 'Date', 'Agreements']
    writer = csv.DictWriter(csvfile, fieldnames = fieldNames)

    writer.writeheader()
    for key, user in allUsers.items():
        writer.writerow(user)

print(f"The end. Parsed {len(allUsers.items())} users")
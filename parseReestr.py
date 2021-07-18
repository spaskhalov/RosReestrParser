import fitz  # this is pymupdf
import sys
import csv
import re
from transliterate import translit
from progress.bar import Bar


VALUE_INDX_IN_BLOCK = 4
FLATS_BY_ENTRANCE = [321, 598, 902, 1223]

srcFileName = sys.argv[1]
domovoiFileName = None
if len(sys.argv) > 2:
    domovoiFileName = sys.argv[2]

allBlocks = []
allUsers = {}
allDomovoiUsers = []

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

def fixFlatNum(entrance, flatNum, forceOldStyle = True):
    #if defined wrong entrance, fix it
    if entrance == 1 and flatNum > FLATS_BY_ENTRANCE[0]:
        while FLATS_BY_ENTRANCE[entrance] <= flatNum:
            entrance += 1
    #if we found num in "old" style, convert it to new style
    if (entrance > 1 and flatNum < FLATS_BY_ENTRANCE[entrance - 2]) or forceOldStyle:
        flatNum += FLATS_BY_ENTRANCE[entrance - 2] if entrance > 1 else 0        
        flatNum += 1 #dont know why, but all flats num increased by one
    return entrance, flatNum

def getFlatInfo(object):
    flatInfoMatch = re.search('.*(?:квартира|студия).*(\d)-(\d+).*этаж.*?(\d+)', object, re.IGNORECASE)
    if flatInfoMatch:
        entrance = int(flatInfoMatch.group(1))
        flatNumOldStyle = int(flatInfoMatch.group(2))
        floorNumber = int(flatInfoMatch.group(3))
        (fixedEntrance, flatNumNewStyle) = fixFlatNum(entrance, flatNumOldStyle)
        return (fixedEntrance, flatNumNewStyle, floorNumber)
    return (None, None, None)

def findFirst(a, f):
  return next((i for i in a if f(i)), None)

def matchWithDomovoiData(user):    
    #match by flat
    domovoiUser = findFirst(allDomovoiUsers, lambda u: u['FlatNum'] == user['FlatNum'])
    #match by name
    if not domovoiUser:
        domovoiUser = matchUserWithDomovoiByName(user)
    if domovoiUser:
        user['PhoneNumber'] = domovoiUser['PhoneNumber']
        user['TGLogin'] = domovoiUser['TGLogin']
        user['FIOinTG'] = domovoiUser['FIOinTG']
        user['CarNum'] = domovoiUser['CarNum']
        user['ParkingNum'] = domovoiUser['ParkingNum'] 

def matchByName(targetFIO, srcName, srcSurName):
    if len(srcSurName) > 3 and srcSurName != srcName:
        srcName = translit(srcName, 'ru')
        srcSurName = translit(srcSurName, 'ru')
        return srcSurName in targetFIO and srcName in targetFIO
    return False

def matchUserWithDomovoiByName(user):
    domovoiUser = findFirst(allDomovoiUsers, lambda u: matchByName(user['FIO'], u['NameInTG'], u['SurNameInTG'])) 
    return domovoiUser       

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
        if not allUsers[name]['FlatNum'] and newUser['FlatNum']:
            allUsers[name]['FlatNum'] = newUser['FlatNum']
            allUsers[name]['FloorNumber'] = newUser['FloorNumber']
            allUsers[name]['Entrance'] = newUser['Entrance']
    else:
        matchWithDomovoiData(newUser)
        allUsers[newUser['FIO']] = newUser
    return curBlockIndex + 1

def parse_int(s, default=None):
 if s.isdigit():
  return int(s)
 else:
  return default

def parseDomovoiUser(row):
    FIO = f"{row['Имя в базе']} {row['Фамилия в базе']}"    
    FIOinTG = f"{row['Имя в Telegram']} {row['Фамилия в Telegram']}"
    TGLogin = row['Логин в Telegram']
    PhoneNumber = row['Номер телефона']    
    Entrance = parse_int(row['Подъезд'],1) 
    FlatNum = parse_int(row['Квартира'],0)
    (Entrance, FlatNum) = fixFlatNum(Entrance, FlatNum, False)
    CarNum = row['Номер машины']
    ParkingNum = row['Парковочное место']

    domovoiUser = {
                'FIO' : FIO,
                'NameInTG' : row['Имя в Telegram'],
                'SurNameInTG' : row['Фамилия в Telegram'],
                'FIOinTG' : FIOinTG,
                'TGLogin' : TGLogin,
                'PhoneNumber' : PhoneNumber,
                'Entrance' : Entrance,
                'FlatNum' : FlatNum,
                'CarNum' : CarNum,
                'ParkingNum' : ParkingNum,                
            }
    
    return domovoiUser

if domovoiFileName:
    with open(domovoiFileName, 'r') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            domovoiUser = parseDomovoiUser(row)
            allDomovoiUsers.append(domovoiUser)

with fitz.open(srcFileName) as doc:
    for page in doc:                     
        allBlocks += page.getText("blocks")

curBlockIndex = 0
bar = Bar('Processing', max = len(allBlocks))
while curBlockIndex >= 0:
    curBlockIndex = parseUser(curBlockIndex)
    bar.goto(curBlockIndex)    
bar.goto(len(allBlocks))
bar.finish()

with open('result.csv', 'w') as csvfile:    
    TargetHeaders = {
        'FIO': 'Фамилия',
        'Area': 'Общая площадь',
        'Entrance' : 'Корпус',
        'FlatNum' : 'Номер квартиры',
        'FloorNumber' : 'Этаж',
        'Date' : 'Дата договора',
        'PhoneNumber' : 'Номер телефона',
        'TGLogin' : 'Логин в Телеграм',
        'CarNum' : 'Номер машины',
        'ParkingNum' : 'Парковка',
        'FIOinTG' : 'Имя в Телаграм',
        'Objects' : 'Объекты в собственности',
        'Agreements' : 'Договоры'
    }

    fieldNames = ['FIO', 'Area', 'Entrance', 'FlatNum', 'FloorNumber', 
    'Date', 'PhoneNumber', 'TGLogin', 'CarNum', 'ParkingNum', 'FIOinTG', 'Objects', 'Agreements']
    writer = csv.DictWriter(csvfile, fieldnames = TargetHeaders)

    #writer.writeheader()
    writer.writerow(TargetHeaders)
    for key, user in allUsers.items():
        writer.writerow(user)

print(f"The end. Parsed {len(allUsers.items())} users")
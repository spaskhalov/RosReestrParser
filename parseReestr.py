import fitz  # this is pymupdf
import sys

VALUE_INDX_IN_BLOCK = 4
srcFileName = sys.argv[1]

def getValueFromCurBlock(blocks, targetText, startIndx):      
    i = startIndx
    listLen = len(blocks)
    while i < listLen:
        curBlock = blocks[i]
        if targetText in curBlock[VALUE_INDX_IN_BLOCK]:
            name = curBlock[VALUE_INDX_IN_BLOCK].split("\n")[1]            
            return (i, name)
        i += 1
    return (-1, "not found")  

def getValueFromNextBlock(blocks, targetText, startIndx):      
    i = startIndx
    listLen = len(blocks)
    while i < listLen:
        curBlock = blocks[i]
        if targetText in curBlock[VALUE_INDX_IN_BLOCK]:
            nextBlock = blocks[i + 1]            
            return (i + 1, nextBlock[VALUE_INDX_IN_BLOCK])
        i += 1
    return (-1, "not found") 

def getObject(blocks, startIndx):
    return getValueFromCurBlock(blocks, "объект долевого строительства:", startIndx)

def getName(blocks, startIndx):      
    return getValueFromCurBlock(blocks, "участники долевого строительства:", startIndx)


text = []
with fitz.open(srcFileName) as doc:
    for page in doc:                     
        text += page.getText("blocks")

currentIndx = 0

(newIndx, object) = getObject(text, 0)
(newIndx, name) = getName(text, newIndx)

print(object, name)

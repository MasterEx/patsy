import socket
import _thread as thread
import mimetypes
import os.path

CONFIGURATION = { 
	'HOST' : '127.0.0.1' , 
	'PORT' : 31338 , 
	'MAX_REQUEST' : 1024 * 2,  # 2 MB
	'DOCUMENT_ROOT' : 'htdocs', # should use full path
	'HTTP_VERSION' : 'HTTP/1.0'
}

STATUS_CODES = {
	'OK' : '200 OK',
	'NOT_FOUND' : '404 Not Found'
}

def handleRequest(clientSocket, address):
	request = clientSocket.recv(CONFIGURATION['MAX_REQUEST']).decode("utf-8")
	lines = list(request.splitlines())
	method = ""
	target = ""
	headers = {}
	for i in range(0, len(lines)):
		if method == "" and (lines[i] == b'\r\n'.decode("utf-8") or lines[i] == b'\n'.decode("utf-8")):
			continue
		elif method == "":
			args = lines[i].replace(b'\t'.decode("utf-8"), '').split(' ')
			method = args[0]
			target = args[1]
		elif not (lines[i] == '' or lines[i] == b'\r\n'.decode("utf-8") or lines[i] == b'\n'.decode("utf-8")):
			#print("LINE : "+lines[i])
			header, value = lines[i].split(':',1)
			headers[header] = value
			#print("header "+header+" "+headers[header])
		elif lines[i] == b'\r\n'.decode("utf-8") or lines[i] == b'\n'.decode("utf-8"):
			break
	requestHandler[method](clientSocket, address, target, headers)
		
def handleGet(clientSocket, address, target, headers):
	#print("INTO GET!")
	#print("**START**")
	uri = getUriName(target)
	retmsg = """HTTP/1.0 200 OK
Date: Fri, 31 Dec 1999 23:59:59 GMT
Content-Type: text/html

THIS IS A FULL MESSAGE
"""
	filePath, mime, status = getResource(target)
	clientSocket.send(bytes(CONFIGURATION['HTTP_VERSION']+" "+status,'utf-8'))
	clientSocket.send(b'\n')
	clientSocket.send(bytes("Content-Type: "+mime,'utf-8'))
	clientSocket.send(b'\r\n\n')
	if mime[:4] == "text":
		with open(filePath, 'r') as f:
			for line in f:
				clientSocket.send(bytes(line,'utf-8'))
	else:
		with open(filePath, 'rb') as f:
			for line in f:
				clientSocket.send(line)
	clientSocket.send(b'\r\n')
	#print("**END**")

def getUriName(target):
	# TO IMPLEMENT
	return target
	
def getResource(uri):
	# return mime type and file descriptor
	filePath = CONFIGURATION['DOCUMENT_ROOT']+getUriName(uri)
	status = STATUS_CODES['OK']
	mime = 'text/html'
	(a, b) = mimetypes.guess_type(uri)
	mime = a
	if not (os.path.isfile(filePath) or os.path.isdir(filePath)):
		status = STATUS_CODES['NOT_FOUND']
	#fileD = open(CONFIGURATION['DOCUMENT_ROOT']+uri, 'r')
	return  filePath, mime, status

requestHandler = {
	'GET' : handleGet
}

if __name__ == '__main__':
	# initialize document root
	
	# initialize server socket
	server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	server.bind((CONFIGURATION['HOST'], CONFIGURATION['PORT']))
	server.listen(5)
	server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
	
	# main loop that accepts http requests
	while True:
		#print("** LOOP **")
		thread.start_new_thread(handleRequest, server.accept())

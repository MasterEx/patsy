# An HTTP 1.0 webserver
import socket
import _thread as thread
import mimetypes
import os.path
import time

TAB = b'\t'.decode("utf-8")
CRLF = b'\r\n'.decode("utf-8")
LF = b'\n'.decode("utf-8")

CONFIGURATION = { 
	'HOST' : '127.0.0.1' , 
	'PORT' : 31338 , 
	'MAX_REQUEST' : 1024 * 2,  # 2 MB
	'DOCUMENT_ROOT' : 'htdocs', # should use full path
	'HTTP_VERSION' : 'HTTP/1.0',
	'MESSAGES_PATH' : 'messages', # use full path
	'SERVER' : 'patsy/0.1'
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
		
def handleGet(clientSocket, address, target, headers, onlyHead=False):
	#print("INTO GET!")
	#print("**START**")
	uri = getUriName(target)
	retHeaders = {}
	status, ftype, filePath, mime = getResource(target)
	clientSocket.send(bytes(CONFIGURATION['HTTP_VERSION']+" "+status,'utf-8'))
	sendGenericHeaders(clientSocket)
	if status == STATUS_CODES['OK'] and ftype:
		# SEND A (TEXT OR BINARY) FILE - NO ERROR
		retHeaders['Content-Type'] = mime
		retHeaders['Content-Length'] = os.path.getsize(filePath)
		sendSpecialHeaders(clientSocket, retHeaders)
		if not onlyHead:
			sendMessageBody(clientSocket, status, filePath, mime, ftype)
	elif status == STATUS_CODES['OK']:
		# DIRECTORY LISTING
		print("DIRECTORY LISTING NOT YET IMPLEMENTED")
	else:
		# SOME KIND OF ERROR OR STATUS CODE
		print("ERROR")
		if not onlyHead:
			sendStatusBody(clientSocket, status, filePath)
	clientSocket.send(b'\r\n')
	#print("**END**")

def handleHead(clientSocket, address, target, headers):
	handleGet(clientSocket, address, target, headers, True)

def getUriName(target):
	# TO IMPLEMENT
	return target

def getResource(uri):
	# return mime type and file descriptor
	filePath = CONFIGURATION['DOCUMENT_ROOT']+getUriName(uri)
	status = STATUS_CODES['OK']
	mime = 'text/html'
	ftype = True
	if not (os.path.isfile(filePath) or os.path.isdir(filePath)):
		status = STATUS_CODES['NOT_FOUND']
	elif os.path.isdir(filePath):
		#it's a dir, return file listing
		mime = 'text/html'
		ftype = False	
	else:
		(a, b) = mimetypes.guess_type(uri)
		mime = a
	#fileD = open(CONFIGURATION['DOCUMENT_ROOT']+uri, 'r')
	return  status, ftype, filePath, mime

def sendGenericHeaders(socket):
	socket.send(b'\n')
	socket.send(bytes("Date: "+time.strftime("%a, %m %b %Y %H:%M:%S %Z", time.gmtime()),'utf-8'))
	socket.send(b'\n')
	socket.send(bytes("Server: "+CONFIGURATION['SERVER'],'utf-8'))

def sendSpecialHeaders(socket, headers):
	for k, v in headers.items():
		socket.send(b'\n')
		socket.send(bytes(k+" : "+str(v),'utf-8'))

def sendMessageBody(socket, status, path, mime, ftype):
	socket.send(b'\r\n\n')
	with open(path, 'rb') as f:
		for line in f:
			socket.send(line)

def sendStatusBody(socket, status, originalFilePath):
	filePath = CONFIGURATION['MESSAGES_PATH']+'/'+status[:3]+'.html'
	sendMessageBody(socket, status, filePath, "text/html", 1)

requestHandler = {
	'GET' : handleGet,
	'HEAD' : handleHead
}

if __name__ == '__main__':
	# initialize server socket
	server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	server.bind((CONFIGURATION['HOST'], CONFIGURATION['PORT']))
	server.listen(5)
	server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
	
	# main loop that accepts http requests
	while True:
		#print("** LOOP **")
		thread.start_new_thread(handleRequest, server.accept())

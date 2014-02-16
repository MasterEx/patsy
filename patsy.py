# An HTTP 1.0 webserver
import socket, mimetypes, os, time, json, base64
import _thread as thread

TAB = b'\t'.decode("utf-8")
GMT = "%a, %m %b %Y %H:%M:%S %Z"

CONFIGURATION = { 
	'HOST' : '0.0.0.0', # bind to all available interfaces
	'PORT' : 31338,
	'MAX_REQUEST' : 1024 * 1,  # 1 MB, more than enough!
	'DOCUMENT_ROOT' : 'htdocs', # should use full path
	'HTTP_VERSION' : 'HTTP/1.0',
	'MESSAGES_PATH' : 'messages', # use full path
	'SERVER' : 'patsy/0.1',
	'FROM' : '', # if empty or None don't send
	'DEFAULT_INDEX' : ('index.html',), # can specify more than one, live the tuple empty if don't want any
	'ACCESSLIST' : 'accesslist.json' # full path
}

STATUS_CODES = {
	'OK' : '200 OK',
	'NOT_FOUND' : '404 Not Found',
	'MOVED_PERMANENTLY' : '301 Moved Permanently',
	'NOT_MODIFIED' : '304 Not Modified',
	'AUTHORIZATION' : '401 Authorization',
	'FORBIDDEN' : '403 Forbidden',
	'NOT_IMPLEMENTED' : '501 Not Implemented'
}

GLOBAL_REPLACES = {
	'HTTP_VERSION' : CONFIGURATION['HTTP_VERSION'],
	'SERVER' : CONFIGURATION['SERVER'],
	'FROM' : CONFIGURATION['FROM']
}

def handleRequest(clientSocket, address):
	request = clientSocket.recv(CONFIGURATION['MAX_REQUEST']).decode('utf8')
	lines = list(request.splitlines())
	method = ''
	target = ''
	mainBody = False
	body = {} # message body in case of POST, not used yet
	headers = {}
	for line in lines:
		if method == '' and line == '':
			continue
		elif method == '':
			args = line.replace(TAB, '').split(' ')
			method = args[0]
			target = args[1]
		elif not line == '' and not mainBody:
			header, value = line.split(':',1)
			headers[header.strip()] = value.strip()
		elif line == '' and method == 'POST':
			mainBody = True
		elif mainBody:
			for l in line.split('&'):
				k, v = l.split('=')
				body[k] = v
		else:
			break
	try:
		requestHandler[method](clientSocket, address, target, headers)
	except KeyError:
		try:
			notImplemented(clientSocket)
		except BrokenPipeError:
			print('BROKEN PIPE - DO NOTHING')
		
def handleGet(clientSocket, address, target, headers, onlyHead=False):
	# parse GET url arguments for future usage
	arguments = {}
	try:
		target, args = target.split('?',1)
		for i in args.split('&'):
			param, val = i.split('=',1)
			arguments[param] = val
	except ValueError:
		print('GET url doesn\'t contain arguments')
	retHeaders = {}
	status, ftype, filePath, mime = getResource(target)
	fullFilePath = CONFIGURATION['DOCUMENT_ROOT']+filePath
	# check (for) authorization credentials
	authorization = checkAuthorization(target)
	if authorization:
		try:
			user, password = base64.b64decode(headers['Authorization'].split()[1]).decode('utf8').split(':',1)
			if authorization['username'] == user and authorization['password'] == password:
				authorization = None
			else:
				status = STATUS_CODES['AUTHORIZATION']				
		except (KeyError, ValueError) as ex:
			status = STATUS_CODES['AUTHORIZATION']
	if status == STATUS_CODES['OK']:
		try:
			lastModTime = time.gmtime(os.path.getmtime(fullFilePath))
			modSinceTime = time.mktime(time.strptime(headers['If-Modified-Since'], GMT))
			if modSinceTime > time.mktime(lastModTime):
				status = STATUS_CODES['NOT_MODIFIED']
		except KeyError:
			print("headers['If-Modified-Since'] not defined")
		# check if dir/file is forbidden
		if not ftype:
			try:
				os.listdir(CONFIGURATION['DOCUMENT_ROOT']+filePath)
			except PermissionError:
				status = STATUS_CODES['FORBIDDEN']
		else:
			try:
				f = open(CONFIGURATION['DOCUMENT_ROOT']+filePath, 'r')
				f.close()
			except PermissionError:
				status = STATUS_CODES['FORBIDDEN']
	clientSocket.send(bytes(CONFIGURATION['HTTP_VERSION']+" "+status,'utf-8'))
	sendGenericHeaders(clientSocket)
	if status == STATUS_CODES['OK'] and ftype:
		# SEND A (TEXT OR BINARY) FILE - NO ERROR
		retHeaders['Content-Type'] = mime
		retHeaders['Content-Length'] = os.path.getsize(fullFilePath)
		retHeaders['Last-Modified'] = time.strftime(GMT, lastModTime)
		sendSpecialHeaders(clientSocket, retHeaders)
		if not onlyHead:
			sendMessageBody(clientSocket, fullFilePath)
	elif status == STATUS_CODES['OK']:
		# DIRECTORY LISTING
		retHeaders['Content-Type'] = 'text/html; charset=iso-8859-1'
		retHeaders['Content-Length'] = getDirectoryListSize(filePath, headers['Host'])
		sendSpecialHeaders(clientSocket, retHeaders)
		sendDirectoryListing(clientSocket, filePath, headers['Host'])
	elif status != STATUS_CODES['NOT_MODIFIED']:
		# SOME KIND OF ERROR OR STATUS CODE
		retHeaders['Content-Type'] = 'text/html; charset=iso-8859-1'
		if authorization:
			retHeaders['WWW-Authenticate'] = 'Basic realm="'+authorization['authname']+'"'
		t = time.strftime(GMT, time.gmtime())
		host, port = headers['Host'].split(':')
		replaces = {
			'DATE' : t,
			'CLIENT_ADDRESS' : address,
			'HOST' : host,
			'PORT' : port,
			'TARGET' : filePath
		}
		replaces.update(GLOBAL_REPLACES)
		if not onlyHead:
			retHeaders['Content-Length'] = getStatusMsgSize(status, replaces)
		if status[0] == '2' or status[0] == '3':
			retHeaders['Location'] = 'http://'+headers['Host']+filePath
		sendSpecialHeaders(clientSocket, retHeaders)
		if not onlyHead:
			sendStatusBody(clientSocket, status, replaces, fullFilePath)
	clientSocket.send(b'\r\n')

def handleHead(clientSocket, address, target, headers):
	handleGet(clientSocket, address, target, headers, True)
	
def handlePost(clientSocket, address, target, headers):
	status = STATUS_CODES['NOT_IMPLEMENTED']
	t = time.strftime(GMT, time.gmtime())
	host, port = headers['Host'].split(':')
	replaces = {
		'DATE' : t,
		'CLIENT_ADDRESS' : address,
		'HOST' : host,
		'PORT' : port,
		'TARGET' : target
	}
	replaces.update(GLOBAL_REPLACES)
	retHeaders = {}
	retHeaders['Content-Type'] = 'text/html; charset=iso-8859-1'
	retHeaders['Content-Length'] = getStatusMsgSize(status, replaces)
	sendGenericHeaders(clientSocket)
	sendSpecialHeaders(clientSocket, retHeaders)
	sendStatusBody(clientSocket, status, replaces)

def getResource(uri):
	# return mime type and file descriptor
	filePath = uri
	tmpPath = CONFIGURATION['DOCUMENT_ROOT']+uri
	status = STATUS_CODES['OK']
	mime = 'text/html'
	ftype = True	
	if tmpPath[-1] != '/' and os.path.isdir(tmpPath):
		# it's a dir -> move to path/
		filePath = filePath+'/'
		ftype = False
		for index in CONFIGURATION['DEFAULT_INDEX']:
			if os.path.isfile(tmpPath+index):
				filePath = filePath+index
				ftype = True
				break
		mime = 'text/html'
		status = STATUS_CODES['MOVED_PERMANENTLY']		
	elif not (os.path.isfile(tmpPath) or os.path.isdir(tmpPath)):
		status = STATUS_CODES['NOT_FOUND']
	elif os.path.isdir(tmpPath):
		#it's a dir, return file listing
		mime = 'text/html'
		ftype = False
		for index in CONFIGURATION['DEFAULT_INDEX']:
			if os.path.isfile(tmpPath+index):
				filePath = filePath+index
				ftype = True
				break
	else:
		(a, b) = mimetypes.guess_type(uri)
		mime = a
	return  status, ftype, filePath, mime

def sendGenericHeaders(socket):
	socket.send(b'\n')
	socket.send(bytes("Date: "+time.strftime(GMT, time.gmtime()),'utf-8'))
	socket.send(b'\n')
	socket.send(bytes("Server: "+CONFIGURATION['SERVER'],'utf-8'))
	try:
		if not (CONFIGURATION['FROM'] == None or CONFIGURATION['FROM'] == ''):
			socket.send(b'\n')
			socket.send(bytes("From: "+CONFIGURATION['FROM'],'utf-8'))
	except KeyError:
		print("CONFIGURATION['FROM'] not defined")

def sendSpecialHeaders(socket, headers):
	for k, v in headers.items():
		socket.send(b'\n')
		socket.send(bytes(k+": "+str(v),'utf-8'))

def sendMessageBody(socket, path):
	socket.send(b'\r\n\n')
	sendBinaryFile(socket, path)
			
def sendBinaryFile(socket, path):
	with open(path, 'rb') as f:
		for line in f:
			socket.send(line)

def sendStatusBody(socket, status, replaces, originalFilePath=''):
	socket.send(b'\r\n\n')
	filePath = CONFIGURATION['MESSAGES_PATH']+'/'+status[:3]+'.html'
	with open(filePath, 'rb') as f:
		for line in f:
			l = replaceLine(line, replaces)
			socket.send(l)
	
def sendDirectoryListing(socket, filePath, host):
	socket.send(b'\n\r\n')
	sendBinaryFile(socket, CONFIGURATION['MESSAGES_PATH']+'/dir-list-top.html')
	if not filePath[-1] == '/':
		filePath = filePath + '/'
	if filePath != '/':
		socket.send(bytes('<li><a href=..>PARENT DIR</a></li>','utf-8'))
	for file in os.listdir(CONFIGURATION['DOCUMENT_ROOT']+filePath):
		if os.path.isdir(CONFIGURATION['DOCUMENT_ROOT']+filePath+file):			
			socket.send(bytes('<li><a href="'+file+'/">'+file+'</a></li>','utf-8'))
		else:
			socket.send(bytes('<li><a href="'+file+'">'+file+'</a></li>','utf-8'))
	sendBinaryFile(socket, CONFIGURATION['MESSAGES_PATH']+'/dir-list-bottom.html')
	
def getDirectoryListSize(filePath, host):
	counter = os.path.getsize(CONFIGURATION['MESSAGES_PATH']+'/dir-list-top.html') + os.path.getsize(CONFIGURATION['MESSAGES_PATH']+'/dir-list-bottom.html')
	if not filePath[-1] == '/':
		filePath = filePath + '/'
	if filePath != '/':
		counter = counter + len(bytes('<li><a href=..>PARENT DIR</a></li>','utf-8'))
	for file in os.listdir(CONFIGURATION['DOCUMENT_ROOT']+filePath):
		if os.path.isdir(CONFIGURATION['DOCUMENT_ROOT']+filePath+file):			
			counter = counter + len(bytes('<li><a href="'+file+'/">'+file+'</a></li>','utf-8'))
		else:
			counter = counter + len(bytes('<li><a href="'+file+'">'+file+'</a></li>','utf-8'))
	return counter
	
def getStatusMsgSize(status, replaces):
	filePath = CONFIGURATION['MESSAGES_PATH']+'/'+status[:3]+'.html'
	counter = 0
	with open(filePath, 'rb') as f:
		for line in f:
			counter = counter + len(replaceLine(line, replaces))
	return counter

def replaceLine(line, replaces):
	for key, replace in replaces.items():
		line = bytes(line.decode('utf8').replace('**'+str(key)+'**', str(replace)), 'utf8') # that seems prety slow :/
	return line
	
def checkAuthorization(filePath):
	for entry in ACCESSLIST['accesslist']:
		if entry['relative_path'] == filePath:
			return entry			
		elif entry['recursive'] and entry['relative_path']+'/' in filePath:
			return entry
	return None
	
def notImplemented(socket):
	retHeaders = {}
	retHeaders['Content-Type'] = 'text/html'
	retHeaders['Content-Length'] = os.path.getsize(CONFIGURATION['MESSAGES_PATH']+'/501.html') # in future, wrong cause of substitutions!
	sendSpecialHeaders(socket, retHeaders)
	sendStatusBody(socket, STATUS_CODES['NOT_IMPLEMENTED'])

requestHandler = {
	'GET' : handleGet,
	'HEAD' : handleHead,
	'POST' : handlePost
}

if __name__ == '__main__':
	ACCESSLIST = json.load(open(CONFIGURATION['ACCESSLIST'], 'r'))
	# initialize server socket
	server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	server.bind((CONFIGURATION['HOST'], CONFIGURATION['PORT']))
	server.listen(5)
	# main loop that accepts http requests
	while True:
		thread.start_new_thread(handleRequest, server.accept())

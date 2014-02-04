import socket
import _thread as thread

CONFIGURATION = { 
	'HOST' : '127.0.0.1' , 
	'PORT' : 31338 , 
	'MAX_REQUEST' : 1024 * 2,  # 2 MB
	'DOCUMENT_ROOT' : 'htdocs'
}

def handleRequest(clientSocket, address):
	request = clientSocket.recv(CONFIGURATION['MAX_REQUEST']).decode("utf-8")
	lines = list(request.splitlines())
	method = ""
	target = ""
	headers = {}
	for i in range(0, len(lines)):
		#print("line: "+lines[i])
		if method == "" and (lines[i] == b'\r\n'.decode("utf-8") or lines[i] == b'\n'.decode("utf-8")):
			continue
		elif method == "":			
			#print("HERE")
			args = lines[i].replace(b'\t'.decode("utf-8"), '').split(' ')
			method = args[0]
			target = args[1]
		#print("Method: "+method+" and target "+target)
		requestHandler[method](clientSocket, address, target, headers)
		
def handleGet(clientSocket, address, target, headers):
	#print("INTO GET!")
	retmsg = """HTTP/1.0 200 OK
Date: Fri, 31 Dec 1999 23:59:59 GMT
Content-Type: text/html
Content-Length: 2

OK"""
	clientSocket.send(bytes(retmsg,'utf-8'))
	return False

requestHandler = {
	'GET' : handleGet
}

if __name__ == '__main__':
	# initialize document root
	
	# initialize server socket
	server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	server.bind((CONFIGURATION['HOST'], CONFIGURATION['PORT']))
	server.listen(5)
	
	# main loop that accepts http requests
	while True:
		#print("** LOOP **")
		thread.start_new_thread(handleRequest, server.accept())

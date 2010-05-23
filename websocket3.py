from socket import *
import threading
import time

class WebSocketException(Exception):
	def __init__(self,message):
		self.msg = message
	def __str__(self):
		return repr(self.msg)

class WebSocket:
	def __init__(self,uri):
		self.uri = uri #urlparse(uri)
		protocol = self.uri.scheme
		
		if not( protocol=='ws' or protocol=='wss' ):
			raise WebSocketException('Unsupported protocol: '+protocol)

		self.headers = {}
		self.handshakecompleted = False
	
	def setHeaders(self,headers):
		self.headers = headers
	
	def connect(self):
		host = self.uri.hostname
		path = self.uri.path
		if path == '':
			path = '/'
		
		query = self.uri.query
		if query != '':
			path += query
		
		origin = 'http://' + host
		port = self.uri.port
		
		if port != 80:
			host += ":" + repr(port)
		
		extraheaders = ''
		for k,v in self.headers:
			extraheaders += k + ': ' + v + '\r\n'
		
		request =  'GET ' + path + ' HTTP/1.1\r\n'
		request += 'Upgrade: WebSocket\r\n'
		request += 'Connection: Upgrade\r\n'
		request += 'Host: ' + host + '\r\n'
		request += 'Origin: ' + origin + '\r\n'
		request += extraheaders
		request += '\r\n'
		
		self.socket = self.createSocket()
		self.sockfile = self.socket.makefile(mode='rwb')
		
		self.sockfile.write(request.encode('utf-8'))
		self.sockfile.flush()
		
		header = self.sockfile.readline().strip()
		if header != b'HTTP/1.1 101 Web Socket Protocol Handshake':
			raise WebSocketException('Invalid handshake response: '+str(header))
		
		header = self.sockfile.readline().strip()
		if header != b'Upgrade: WebSocket':
			raise WebSocketException('Invalid handshake response: '+str(header))

		header = self.sockfile.readline().strip()
		if header != b'Connection: Upgrade':
			raise WebSocketException('Invalid handshake response: '+str(header))
		
		while True:
			header = self.sockfile.readline().strip()
			print ('skipping header: ' + str(header))
			if len(header) == 0:
				break
		
		print ('handshake completed.')
		self.handshakecompleted = True
	
	def createSocket(self):
		scheme = self.uri.scheme
		host = self.uri.hostname
		
		port = self.uri.port
		if port == -1:
			if scheme == 'ws':
				port = 80
			elif scheme == 'wss':
				port = 443
		
		if scheme == 'ws':
			s = socket(AF_INET,SOCK_STREAM)
			s.connect( (host,port) )
			return s
		else:
			raise WebSocketException('uops..wss protocol not supported yet :p')
	
	def send(self,message):
		if False == self.handshakecompleted:
			raise WebSocketException('handshake is not completed yet, cannot send!')
		
		self.sockfile.write(b'\x00')
		self.sockfile.write( (message).encode('utf-8') )
		self.sockfile.write(b'\xff')
		self.sockfile.flush()
	
	def recv(self):
		if False == self.handshakecompleted:
			raise WebSocketException('handshake is not completed yet, cannot receive!')
		
		ret = bytearray()
		
		b = self.sockfile.read(1)
		if (b[0]&0x80) == 0x80:
			length = 0
			while True:
				b = (self.sockfile.read(1)[0]) & 0x7f
				length = b * 128 + length
				if (b&0x80) == 0x80:
					break
			print ('reading ' + length + ' bytes..')
			garbage = self.sockfile.read(length)
			print (garbage)
		
		while True:
			b = self.sockfile.read(1)
			if b[0] == 0xff:
				break
			ret += b
		return ret.decode('utf-8') #str(ret,'utf-8').encode('utf-8')
	
	def close(self):
		self.socket.close()
		self.sockfile.close()
		del self.socket
		del self.sockfile

class WebSocketReader(threading.Thread):
	def __init__(self,websocket,messagehandler):
		self.ws = websocket
		self.msgh = messagehandler
		self.running = True
		threading.Thread.__init__(self)
		
	def run(self):
		while(self.running):
			try:
				self.msgh( self.ws.recv() )
			except Exception as e:
				print (e)
	
	def close(self):
		self.running = False
	
class Uri:
	def __init__(self,scheme,host,port,path,query = ''):
		self.scheme = scheme
		self.hostname = host
		self.port = port
		self.path = path
		self.query = query

if __name__ == "__main__":
#	ws = WebSocket('ws://localhost:8000/wstest')
	tosend = 'foobåar æø Ø'
	print (tosend)
	ws = WebSocket( Uri('ws','10.211.55.2',8000,'/wstest') )
	def handler(m):
		print (m)
	wsr = WebSocketReader(ws,handler)
	ws.connect()
	wsr.start()
	ws.send( tosend )
	
	print ('sleeping...')
#	print( ws.recv() )
	time.sleep(2)
	print ('ok, slept')

	ws.close()
	wsr.close()
	print ('websocket and reader closed!')

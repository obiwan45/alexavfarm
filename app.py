import websockets
import asyncio
import json
import time, os


class HttpWSSProtocol(websockets.WebSocketServerProtocol):
    rwebsocket = None
    rddata = None

    async def handler(self):
        try:
            #while True:
            request_line, headers = await websockets.http.read_message(self.reader)
            #print(headers)
            method, path, version = request_line[:-2].decode().split(None, 2)
            #print(self.reader)
        except Exception as e:
            #print(e.args)
            self.writer.close()
            self.ws_server.unregister(self)

            raise

        # TODO: Check headers etc. to see if we are to upgrade to WS.
        if path == '/ws':
            # HACK: Put the read data back, to continue with normal WS handling.
            self.reader.feed_data(bytes(request_line))
            self.reader.feed_data(headers.as_bytes().replace(b'\n', b'\r\n'))

            return await super(HttpWSSProtocol, self).handler()
        else:
            try:
                return await self.http_handler(method, path, version)
            except Exception as e:
                print(e)
            finally:

                self.writer.close()
                self.ws_server.unregister(self)


    async def http_handler(self, method, path, version):
        response = ''
        try :
            alexaRequest = self.reader._buffer.decode('utf-8')
            #print("Req-->"+alexaRequest)
            RequestJson = json.loads(alexaRequest)['request']['intent']['slots']
            IntentName = json.loads(alexaRequest)['request']['intent']

            if 'WaterThePlant' in IntentName['name']:
                print({"cmd":"execute","param":"water","value":"null","target":"all"})
                jsonRequest = {"cmd": "execute", "param": "water","value": "null", "target": "all"}
            # elif 'SoilMoisture' in IntentName['name']:
            #     print({"object":obj,"value":value,"query":"cmd"})
            #     jsonRequest = {"object": obj.lower(), "value": value, "query": "cmd"}
            # elif 'TempHumidity' in IntentName['name']:
            #     print({"object":obj,"value":value,"query":"cmd"})
            #     jsonRequest = {"object": obj.lower(), "value": value, "query": "cmd"}

            with open('data.json', 'w') as outfile:
                json.dump(json.dumps(jsonRequest), outfile)
                #await self.rwebsocket.send(alexaRequest)
            await self.rwebsocket.send(json.dumps(jsonRequest))

            # #wait for response and send it back to IFTTT
            self.rddata = await self.rwebsocket.recv()
            #
            #val ='{"version": "1.0","sessionAttributes": {},"response": {"outputSpeech": {"type": "PlainText","text": "It is done"},"shouldEndSession": true}}'
            response = '\r\n'.join([
                'HTTP/1.1 200 OK',
                'Content-Type: text/json',
                '',
                '' + self.rddata,
            ])
        except Exception as e:
            print(e)
        self.writer.write(response)
        with open('sendToAlexa.txt', 'w') as outfile:
            outfile.write(response.encode())
            outfile.close()




def updateData(data):
    HttpWSSProtocol.rddata = data

async def ws_handler(websocket, path):
    game_name = 'g1'
    try:
        with open('data.json') as data_file:
            data = json.load(data_file)
        HttpWSSProtocol.rwebsocket = websocket
        await websocket.send(data)
        data ='{"empty":"empty"}'
        while True:
            data = await websocket.recv()
            updateData(data)
    except Exception as e:
        print(e)
    finally:
        print("")

def _read_ready(self):
    if self._conn_lost:
        return
    try:
        time.sleep(.10)
        data = self._sock.recv(self.max_size)
    except (BlockingIOError, InterruptedError):
        pass
    except Exception as exc:
        self._fatal_error(exc, 'Fatal read error on socket transport')
    else:
        if data:
            self._protocol.data_received(data)
        else:
            if self._loop.get_debug():
                print("%r received EOF")
            keep_open = self._protocol.eof_received()
            if keep_open:
                # We're keeping the connection open so the
                # protocol can write more, but we still can't
                # receive more, so remove the reader callback.
                self._loop._remove_reader(self._sock_fd)
            else:
                self.close()

asyncio.selector_events._SelectorSocketTransport._read_ready = _read_ready

port = int(os.getenv('PORT', 5687))#5687
start_server = websockets.serve(ws_handler, '', port, klass=HttpWSSProtocol)
# logger.info('Listening on port %d', port)
print("Server Started")
asyncio.get_event_loop().run_until_complete(start_server)
asyncio.get_event_loop().run_forever()


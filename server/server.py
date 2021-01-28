
import asyncio
import websockets
import json


import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "homeactivity.settings")
import django
django.setup()

from activities.models import Category, Activity, Member, ActivityLog

class Server:
    def __init__(self, host="localhost", port="8811"):

        print(f"Starting websocket server on {host}:{port}")

        self.CONNS = set()

        self.start_server = websockets.serve(self.change_status, host, port)

        asyncio.get_event_loop().run_until_complete(self.start_server)
        asyncio.get_event_loop().run_forever()
    
    async def register(self, websocket):
        self.CONNS.add(websocket)
    async def unregister(self, websocket):
        self.CONNS.remove(websocket)
    

    async def change_status(self, websocket, path):
        await self.register(websocket)
        try:
            await websocket.send(json.dumps({test: 'connected'}))

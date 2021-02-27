
import asyncio
import asyncpg
import json
import time
import websockets



import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "homeactivity.settings")
import django
django.setup()

from activities.models import Category, Activity, Member, ActivityLog

class Server:
    def __init__(self, host="localhost", port="8811", db_host="localhost", db_user="postgres", db_password="postgres", db_name="postgres"):

        print(f"Starting websocket server on {host}:{port}")

        self.CONNS = set()

        self.last_id = None

        self.start_server = websockets.serve(self.change_status, host, port)

        tasks = set()

        self.start_db = self.get_new_rows(db_user, db_password, db_name, db_host)

        tasks.add(self.start_db)

        self.periodic = self.routine_send()

        tasks.add(self.periodic)

        asyncio.get_event_loop().run_until_complete(self.start_server)

        await asyncio.gather(*tasks)

        asyncio.get_event_loop().run_forever()


    async def get_new_rows(self, db_user, db_password, db_name, db_host):
        print(f"connecting to {db_name} @ {db_host}")
        conn = await self.connect_db(db_user, db_password, db_name, db_host)
        # note, we should set this up as a notify/listen with triggers on update and insert
        # i have other things i need to do, so im just going to mash postgres by querying a bunch
        # this is still a much better solution than multiple hosts mashing http endpoints doing the same thing
        # still an improvement, and hopefully making my network a bit better
        
        # pull in the initial id
        latest = await conn.fetchrow('SELECT id FROM activities_activitylog order by id desc limit 1')
        self.last_row = latest['id']
        print(f"last_row: {self.last_row}")

        while True:
            new_rows = await conn.fetch('SELECT id, activity_id FROM activities_activitylog where id > $1 order by id desc', self.last_row)
            for row in new_rows:
                print(f"new row: {row}")
                await self.send_update(row['activity_id'])
                if row['id'] > self.last_row:
                    self.last_row = row['id']
            await asyncio.sleep(0.5)
    
    async def connect_db(self, db_user, db_password, db_name, db_host):
        return await asyncpg.connect(user=db_user, password=db_password, database=db_name, host=db_host)

    async def send_update(self, pk):
        if self.CONNS:
            activity = Activity.objects.get(pk=pk)
            items = []
            item = {}
            item['pk'] = activity.pk
            item['activity_text'] = activity.activity_text
            item['category'] = activity.category.pk
            last_checkin = activity.log.order_by('-date')
            if (len(last_checkin) > 0):
                item['last_checkin'] = last_checkin[0].date.timestamp()
                item['next_checkin'] = last_checkin[0].date.timestamp() + (activity.hours * 60*60)
            else:
                item['next_checkin'] = 0
            items.append(item)
            for conn in self.CONNS:
                await conn.send(json.dumps(items))

    async def get_state(self):
        activities = Activity.objects.filter(enabled=True).order_by('pk')
        parsed = []
        for activity in activities:
            item = {}
            item['pk'] = activity.pk
            item['activity_text'] = activity.activity_text
            item['category'] = activity.category.pk

            last_checkin = activity.log.order_by('-date')
            if (len(last_checkin) > 0):
                item['last_checkin'] = last_checkin[0].date.timestamp()
                item['next_checkin'] = last_checkin[0].date.timestamp() + (activity.hours * 60*60)
            else:
                item['next_checkin'] = 0

            parsed.append(item)
        return json.dumps(parsed)

    async def initial_state(self, websocket):
        state = await self.get_state()
        await websocket.send(state)
    
    async def routine_send(self):
        while 1:
            if self.CONNS:
                state = await self.get_state()
                for conn in self.CONNS:
                    await conn.send(state)
            await asyncio.sleep(60)

    
    async def register(self, websocket):
        self.CONNS.add(websocket)
    async def unregister(self, websocket):
        self.CONNS.remove(websocket)

    async def change_status(self, websocket, path):
        await self.register(websocket)
        try:
            # await websocket.send(json.dumps({'test': 'connected'}))
            await self.initial_state(websocket)
            async for message in websocket:
                data = json.loads(message)
                print(f"message: {data}")
        finally:
            await self.unregister(websocket)


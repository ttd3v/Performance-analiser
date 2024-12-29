from fastapi import FastAPI
from fastapi.responses import HTMLResponse,JSONResponse
import sqlite3,psutil,threading,uvicorn,os
from threading import Thread
from time import time,sleep

app = FastAPI()
PATH = "./data.db"
DATA_DURATION = 3600 * 24 * 32 # time in seconds that the data will remain stored
GAP = 1
RANGE = 60 ** 2 # range of calculation
HOST = "0.0.0.0"
PORT = 46401

if not os.path.exists(PATH):
    connection = sqlite3.connect(PATH,autocommit=True)
    connection.execute("""--sql
        CREATE TABLE analysis(
            ram SMALLINT DEFAULT 0,
            cpu SMALLINT DEFAULT 0,
            "disk" SMALLINT DEFAULT 0,
            network SMALLINT DEFAULT 0,
            "time" INT DEFAULT 0
        )
    """)
    connection.close()


def get_system_usage():
    cpu_usage = psutil.cpu_percent(interval=1) / 100.0
    ram_usage = psutil.virtual_memory().percent / 100.0
    disk_usage = psutil.disk_usage('/').percent / 100.0
    net_io_start = psutil.net_io_counters()
    net_io_start_bytes = net_io_start.bytes_sent + net_io_start.bytes_recv
    psutil.cpu_percent(interval=1)  
    net_io_end = psutil.net_io_counters()
    net_io_end_bytes = net_io_end.bytes_sent + net_io_end.bytes_recv
    max_throughput = 125 * 1024 * 1024 
    network_usage = (net_io_end_bytes - net_io_start_bytes) / max_throughput
    network_usage = min(network_usage, 1.0) 
    return (min(cpu_usage,1.0),min(ram_usage,1.0),min(network_usage,1),min(disk_usage,1),time()//1)

def store(clock):
    data = []
    for i in range(RANGE):
        data.append(get_system_usage())
        sleep(GAP)
    gi = [0,0,0,0,0]
    for item in data:
        gi[0] += item[0]
        gi[1] += item[1]
        gi[2] += item[2]
        gi[3] += item[3]
        gi[4] += item[4]
    gi[0] = gi[0]/len(data)
    gi[1] = gi[1]/len(data)
    gi[2] = gi[2]/len(data)
    gi[3] = gi[3]/len(data)
    gi[4] = gi[4]/len(data)
    

    connection = sqlite3.connect(PATH)
    cursor = connection.cursor()
    cursor.execute("""INSERT INTO analysis(ram,cpu,"disk",network,"time") VALUES(?,?,?,?,?)""",gi)
    connection.commit()
    cursor.execute('DELETE FROM analysis WHERE "time" < %s'%(clock-DATA_DURATION//1))    
    cursor.close()
    connection.close()

def auto_store():
    while True:
        store(time()//1)
        print('store')
    
Thread(target=auto_store,daemon=True).start()

@app.get("/data")
async def get_Data():
    connection = sqlite3.connect(PATH)
    cursor = connection.cursor()
    data = {}
    for x in cursor.execute("""SELECT ram,cpu,"disk",network,"time" FROM analysis""").fetchall():
        data[len(data)] = [y for y in x]
    connection.close()
    return JSONResponse(data)
    

@app.get("/")
async def index():
    with open('./index.html') as file:
        return HTMLResponse(file.read())
    
if __name__ == "__main__":
    uvicorn.run(app,host=HOST,port=PORT)
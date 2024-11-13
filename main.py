import asyncio
import json
import uuid
import ssl
import random
import sys
import time  # Added import for time module
from datetime import datetime, timedelta

from loguru import logger
import aiohttp

logger.remove()
logger.add(
    sys.stderr,
    format="<white>{time:HH:mm:ss}</white> | {message}",
    level="INFO",
    colorize=True
)

RATE_LIMIT = {
    'requests_per_connection': 50, 
    'min_request_delay': 5,
    'max_request_delay': 20,
    'cooldown_time': 300,     
}

async def connect_to_wss(user_id):
    device_id = str(uuid.uuid3(uuid.NAMESPACE_DNS, "no_proxy"))
    logger.info(f"[*] Connecting with Device ID: {device_id}")

    request_count = 0
    last_request = time.time()

    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE

    urilist = ["wss://proxy.wynd.network:4444/", "wss://proxy.wynd.network:4650/"]
    uri = random.choice(urilist)
    server_hostname = "proxy.wynd.network"

    async with aiohttp.ClientSession() as session:
        async with session.ws_connect(uri, ssl=ssl_context) as websocket:
            logger.success("[+] Connected to WebSocket")

            async def send_ping():
                nonlocal request_count, last_request
                while True:
                    if request_count >= RATE_LIMIT['requests_per_connection']:
                        logger.warning("[!] Connection reached request limit, cooling down...")
                        await asyncio.sleep(RATE_LIMIT['cooldown_time'])
                        request_count = 0
                        continue

                    delay = random.uniform(
                        RATE_LIMIT['min_request_delay'], 
                        RATE_LIMIT['max_request_delay']
                    )
                    await asyncio.sleep(delay)

                    send_message = json.dumps(
                        {"id": str(uuid.uuid4()), "version": "1.0.0", "action": "PING", "data": {}}
                    )
                    await websocket.send_str(send_message)
                    request_count += 1
                    last_request = time.time()

                    logger.success(f"[+] PING sent [{request_count}/{RATE_LIMIT['requests_per_connection']}]")
                    if request_count % 10 == 0:
                        cool_time = random.randint(30, 60)
                        logger.info(f"[~] Mini cooling down {cool_time}s after 10 requests")
                        await asyncio.sleep(cool_time)

            asyncio.create_task(send_ping())

            while True:
                response = await websocket.receive()
                message = json.loads(response.data)
                logger.info(f"[+] Received message: {message}")

async def main():
    user_id = "test_user"
    await connect_to_wss(user_id)

if __name__ == '__main__':
    asyncio.run(main())
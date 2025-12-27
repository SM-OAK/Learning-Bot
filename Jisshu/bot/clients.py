import asyncio
import logging
import info  # Changed to import module to update global variables
from pyrogram import Client
from Jisshu.util.config_parser import TokenParser
from . import multi_clients, work_loads, JisshuBot

async def initialize_clients():
    multi_clients[0] = JisshuBot
    work_loads[0] = 0
    all_tokens = TokenParser().parse_from_env()
    
    if not all_tokens:
        print("No additional clients found, using default client")
        return
    
    async def start_client(client_id, token):
        try:
            print(f"Starting - Client {client_id}")
            if client_id == len(all_tokens):
                await asyncio.sleep(2)
                print("This will take some time, please wait...")
            
            client = await Client(
                name=str(client_id),
                api_id=info.API_ID,
                api_hash=info.API_HASH,
                bot_token=token,
                sleep_threshold=info.SLEEP_THRESHOLD,
                no_updates=True,
                in_memory=True
            ).start()
            
            work_loads[client_id] = 0
            return client_id, client
        except Exception:
            logging.error(f"Failed starting Client - {client_id} Error:", exc_info=True)
            return None # Return None on failure to avoid crashing

    # Gather all clients and filter out failed ones (None)
    results = await asyncio.gather(*[start_client(i, token) for i, token in all_tokens.items()])
    valid_clients = {res[0]: res[1] for res in results if res is not None}
    
    multi_clients.update(valid_clients)
    
    if len(multi_clients) > 1:
        info.MULTI_CLIENT = True # Correctly update global config
        print(f"Multi-Client Mode Enabled with {len(multi_clients)} clients.")
    else:
        print("No additional clients were initialized, using default client")
        

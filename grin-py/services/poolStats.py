#!/usr/bin/python

# Copyright 2018 Blade M. Doyle
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# Add a pool stats record ~per block


import sys
import requests
import json
from time import sleep
import traceback


from grinbase.dbaccess import database

from grinlib import lib
from grinlib import grin
#from grinlib import grinstats
from grinlib import poolstats

from grinbase.model.blocks import Blocks
from grinbase.model.pool_stats import Pool_stats
#from grinbase.model.worker_shares import Worker_shares
#from grinbase.model.pool_blocks import Pool_blocks

PROCESS = "poolStats"
LOGGER = None
CONFIG = None

# XXX TODO: Move to config
BATCHSZ = 100


def main():
    CONFIG = lib.get_config()
    LOGGER = lib.get_logger(PROCESS)
    LOGGER.warn("=== Starting {}".format(PROCESS))
    # Connect to DB
    database = lib.get_db()

    # Get config
    check_interval = float(CONFIG[PROCESS]["check_interval"])
    avg_over_range = int(CONFIG[PROCESS]["avg_over_range"])

    # Find the height of the latest stats record
    last_height = 0
    latest_stat = Pool_stats.get_latest()
    if latest_stat is None:
        # Special case for new pool startup
        poolstats.initialize()
        last_height = 0
    else:
        last_height = latest_stat.height
    height = last_height + 1
    LOGGER.warn("Starting at height: {}".format(height))

    # Generate pool stats records - one per grin block
    while True:
        try:
            # latest = grin.blocking_get_current_height()
            latest = Blocks.get_latest().height
            while latest > height:
                new_stats = poolstats.calculate(height, avg_over_range)
                # Batch new stats when possible, but commit at reasonable intervals
                database.db.getSession().add(new_stats)
                if( (height % BATCHSZ == 0) or (height >= (latest-10)) ):
                    database.db.getSession().commit()
                LOGGER.warn("Added Pool_stats for block: {} - {} {} {}".format(new_stats.height, new_stats.gps, new_stats.active_miners, new_stats.shares_processed))
                height = height + 1
                sys.stdout.flush()
        except Exception as e:  # AssertionError as e:
            LOGGER.error("Something went wrong: {} - {}".format(e, traceback.print_stack()))
            sleep(check_interval)
        sleep(check_interval)
    LOGGER.warn("=== Completed {}".format(PROCESS))

if __name__ == "__main__":
    main()

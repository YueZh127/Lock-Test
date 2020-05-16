import logging
from datetime import datetime

logfile = f'logs/log-{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}.log'
logging.basicConfig(filename=logfile,
                            filemode='a',
                            format='%(asctime)s,%(msecs)d %(name)s %(levelname)s %(message)s',
                            datefmt='%H:%M:%S',
                            level=logging.INFO)

logger = logging.getLogger('swap-test')

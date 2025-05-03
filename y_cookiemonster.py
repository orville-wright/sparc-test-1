#!/home/orville/venv/devel/bin/python3
import requests
from bs4 import BeautifulSoup
import pandas as pd
import logging
import argparse

# logging setup
logging.basicConfig(level=logging.INFO)

from requests_html import HTMLSession

class y_cookiemonster:
    """
    Class to provide 2 utility methos that will...
    - Open a Yahoo Finaince webpage
    - Porcess is as BASIC HTML or Rendered Javascript
    WARN: These methods do NOT data processing
    """

    # global accessors
    yti = 0             # instance identifier
    cycle = 0           # class thread loop counter

    yahoo_headers = { \
                            'authority': 'finance.yahoo.com', \
                            'path': '/screener/predefined/day_gainers/', \
                            'referer': 'https://finance.yahoo.com/screener/', \
                            'sec-ch-ua': '"Google Chrome";v="123", "Not:A-Brand";v="8", "Chromium";v="123"', \
                            'sec-ch-ua-mobile': '"?0"', \
                            'sec-fetch-mode': 'navigate', \
                            'sec-fetch-user': '"?1', \
                            'sec-fetch-site': 'same-origin', \
                            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.131 Safari/537.36' }
        
    # ----------------- 0 --------------------=
    def __init__(self, yti):
        cmi_debug = __name__+"::"+self.__init__.__name__
        logging.info( f'%s - Instantiate.#{yti}' % cmi_debug )
        # init empty DataFrame with present colum names
        self.yti = yti
        return

    # ----------------- 1 --------------------=
    def get_html_data(self, html_url):
        """
        Connect to finance.yahoo.com and open te page only.

        Return: Handle of opened URL

        WARN: This functon does NO data processing or HTML/Javascript rendering.
        """

        cmi_debug = __name__+"::"+self.get_html_data.__name__+".#"+str(self.yti)
        logging.info('%s - IN' % cmi_debug )
        ht_url = "https://" + html_url

        logging.info('%s - read html stream' % cmi_debug )

        logging.info( f"%s - HTML get request..." % cmi_debug )
        logging.info( f"%s - URL: {ht_url}" % cmi_debug )

        session = HTMLSession()
        self.r = session.get(ht_url)
        logging.info('%s - close url handle' % cmi_debug )
        self.r.close()
        return self.r

    # ----------------- 2 --------------------
    def get_js_data(self, js_url):
        """
        Connect to finance.yahoo.com and open a  Webpage as Javascript object
        Process with Javascript render engine and return JS webpage handle
        """

        cmi_debug = __name__+"::"+self.get_js_data.__name__+".#"+str(self.yti)
        logging.info('%s - IN' % cmi_debug )
        js_url = "https://" + js_url

        #test_url = "https://www.whatismybrowser.com/detect/is-javascript-enabled"
        #test_url = "https://www.javatester.org/javascript.html"
        #test_url = "https://finance.yahoo.com/screener/predefined/small_cap_gainers/"

        logging.info( f"%s - Javascript engine setup..." % cmi_debug )
        logging.info( f"%s - URL: {js_url}" % cmi_debug )
        logging.info( f"%s - Init JS_session HTMLsession() setup" % cmi_debug )

        js_session = HTMLSession()
        with js_session.get( js_url ) as self.js_resp0:
        
            logging.info( f"%s - JS_session.get() sucessful !" % cmi_debug )
        
        logging.info( f"%s - JS html.render()... diasbled" % cmi_debug )
        hot_cookies = requests.utils.dict_from_cookiejar(self.js_resp0.cookies)
        logging.info( f"%s - Swap in JS reps0 cookies into js_session yahoo_headers" % cmi_debug )
        js_session.cookies.update(self.yahoo_headers)

        return self.js_resp0
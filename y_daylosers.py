#!/home/orville/venv/devel/bin/python3
import requests
from bs4 import BeautifulSoup
from requests_html import HTMLSession, HTML  # Added for JavaScript rendering
import pandas as pd
import numpy as np
import re
import logging
import argparse
import time
from rich import print

logging.basicConfig(level=logging.INFO)

#####################################################
class y_daylosers:
    """Class to extract Top Losers data set from finance.yahoo.com"""
    # global accessors
    tl_df0 = ""          # DataFrame - Full list of top loserers
    tl_df1 = ""          # DataFrame - Ephemerial list of top 10 loserers. Allways overwritten
    tl_df2 = ""          # DataFrame - Top 10 ever 10 secs for 60 secs
    all_tag_tr = ""      # BS4 handle of the <tr> extracted data
    rows_extr = 0        # number of rows of data extracted
    ext_req = ""         # request was handled by y_cookiemonster
    yti = 0
    cycle = 0            # class thread loop counter

    dummy_url = "https://finance.yahoo.com/screener/predefined/day_losers"

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

    # ----------------- 1 --------------------
    def __init__(self, yti):
        cmi_debug = __name__+"::"+self.__init__.__name__
        logging.info( f'%s - Instantiate.#{yti}' % cmi_debug )
        # init empty DataFrame with present colum names
        self.tl_df0 = pd.DataFrame(columns=[ 'Row', 'Symbol', 'Co_name', 'Cur_price', 'Prc_change', 'Pct_change', 'Mkt_cap', 'M_B', 'Time'] )
        self.tl_df1 = pd.DataFrame(columns=[ 'ERank', 'Symbol', 'Co_name', 'Cur_price', 'Prc_change', 'Pct_change' 'Mkt_cap', 'M_B', 'Time'] )
        self.tl_df2 = pd.DataFrame(columns=[ 'ERank', 'Symbol', 'Co_name', 'Cur_price', 'Prc_change', 'Pct_change' 'Mkt_cap', 'M_B', 'Time'] )
        self.yti = yti
        return

    # ----------------- 2 --------------------    def init_dummy_session(self):
    def init_dummy_session(self, yti):
        """Initialize a session with Yahoo Finance using requests-html"""

        cmi_debug = __name__+"::"+self.init_dummy_session.__name__+".#"+str(self.yti)
        logging.info( f'%s Instance.#{yti}' % cmi_debug )                                                                            
        try:
            # Create a requests-html session instead of requests
            session = HTMLSession()
            self.dummy_resp0 = session.get(self.dummy_url, headers=self.yahoo_headers, timeout=5)
            hot_cookies = self.dummy_resp0.cookies.get_dict()
            logging.info(f"Successfully initialized dummy session with requests-html")
            return True
        except Exception as e:
            logging.error(f"Failed to initialize dummy session: {e}")
            return False

        """
        self.dummy_resp0 = requests.get(self.dummy_url, stream=True, headers=self.yahoo_headers, cookies=self.yahoo_headers, timeout=5 )
        hot_cookies = requests.utils.dict_from_cookiejar(self.dummy_resp0.cookies)
        #self.js_session.cookies.update({'A1': self.js_resp0.cookies['A1']} )    # yahoo cookie hack
        return
        """

    # ----------------- 3 --------------------
    def ext_get_data(self, yti, js_render):
        """
        Connect to finance.yahoo.com and extract (scrape) the raw string data out of
        the webpage data tables. Returns a requests-html handle.
        
        Uses requests-html to render JavaScript content, ensuring dynamic data
        is properly loaded before extraction.
        
        WARRN: URL must have been pre-opened & pre-processed by cookiemonster

        Parameters:
            yti: Instance identifier
            js_render: use JAVASCRIPT render engine or not
            
        Returns:
            None, but populates self.tr_rows with requests-html Elements
        """
        self.yti = yti
        cmi_debug = __name__+"::"+self.ext_get_data.__name__+".#"+str(self.yti)
        logging.info('%s     - IN' % cmi_debug )
        logging.info(f"%s     - JS engine request: {js_render}" % cmi_debug )
        
        # use preexisting response from managed req (handled by cookie monster) 
        r = self.ext_req
        
        if js_render:   # should we render page with  JAVASCRIPT engine?
            try:
                # If ext_req is a standard requests Response object, convert to requests-html
                if not hasattr(r, 'html'):
                    logging.info(f"%s     - Convert Resp to requests-html..." % cmi_debug)
                    # Create HTML object from response text
                    html = HTML(html=r.text, url=r.url)
                    # Store HTML object on response for consistency
                    r.html = html
                
                # Try to render JavaScript if available, but make it optional
                try:
                    logging.info(f"%s     - Attempt to render JS content..." % cmi_debug)
                    r.html.render(timeout=20, sleep=1)
                    logging.info(f"%s     - JavaScript render successful" % cmi_debug)
                except Exception as e:
                    logging.warning(f"%s     - JavaScript rendering fail (this is okay): {e}" % cmi_debug)
                    logging.info(f"%s - Fallback to non-rendered content" % cmi_debug)
            except Exception as e:
                logging.error(f"%s     - Failed to process HTML: {e}" % cmi_debug)
                # Create a basic HTML object as fallback
                r.html = HTML(html=r.text, url=r.url)
                logging.warning(f"%s     - FALLBACK to basic HTML mode mode" % cmi_debug)
        else:
            logging.info(f"%s     - Use Basic HTML mode / JS engine: {js_render}" % cmi_debug)
        
        # Try to find tbody using CSS selector
        logging.info(f"%s     - HTML CSS Selector processing..." % cmi_debug)
        self.tag_tbody = r.html.find('tbody', first=True)
        
        if not self.tag_tbody:
            logging.warning(f"%s     - Could not find <tbody> element using HTML CSS" % cmi_debug)
            logging.info(f"%s     - Fall back to BeautifulSoup parsing" % cmi_debug)
            
            # Fallback to BeautifulSoup for parsing
            soup = BeautifulSoup(r.text, 'html.parser')
            bs_tbody = soup.find('tbody')
            
            if not bs_tbody:
                logging.error(f"%s     - Could not find <tbody> element with BeautifulSoup either." % cmi_debug)
                print (f"{r.html}")
                return None
                
            # Convert BeautifulSoup elements to a format compatible with our code
            self.tr_rows = bs_tbody.find_all("tr")
            # Store the BeautifulSoup tbody for compatibility
            self.tag_tbody = bs_tbody
            self.using_bs4 = True
            logging.info(f"%s     - Successfully fell back to BeautifulSoup parsing." % cmi_debug)
        else:
            # Find all tr elements within tbody using requests-html
            self.tr_rows = self.tag_tbody.find("tr")
            self.using_bs4 = False
        
        logging.info(f'%s     - Found {len(self.tr_rows)} rows in the table.' % cmi_debug)
        logging.info('%s     - Page processed by requests-html engine' % cmi_debug)
        return
    

    """
    def ext_get_data(self, yti):
        Connect to finance.yahoo.com and extract (scrape) the raw string data out of
        the webpage data tables. Returns a BS4 handle.
        Send hint which engine processed & rendered the html page
        0. Simple HTML engine
        1. JAVASCRIPT HTML render engine (down redering a complex JS page in to simple HTML)

        self.yti = yti
        cmi_debug = __name__+"::"+self.ext_get_data.__name__+".#"+str(self.yti)
        logging.info('%s - IN' % cmi_debug )
        logging.info('%s - ext request pre-processed by cookiemonster...' % cmi_debug )
        # use an existing resposne from a previously managed req (handled by cookie monster) 
        r = self.ext_req
        logging.info( f"%s - BS4 stream processing..." % cmi_debug )
        self.soup = BeautifulSoup(r.text, 'html.parser')
        self.tag_tbody = self.soup.find('tbody')
        self.tr_rows = self.tag_tbody.find_all("tr")
        logging.info('%s Page processed by BS4 engine' % cmi_debug )
        return
    """

    # ----------------- 4 --------------------
    def build_tl_df0(self):
        """
        Build-out a fully populated Pandas DataFrame containg all the extracted/scraped fields from the
        html/markup table data Wrangle, clean/convert/format the data correctly.
        """

        cmi_debug = __name__+"::"+self.build_tl_df0.__name__+".#"+str(self.yti)
        logging.info('%s - IN' % cmi_debug )
        time_now = time.strftime("%H:%M:%S", time.localtime() )
        logging.info('%s - Create clean NULL DataFrame' % cmi_debug )
        self.tl_df0 = pd.DataFrame()             # new df, but is NULLed
        x = 0
        self.rows_extr = int( len(self.tag_tbody.find_all('tr')) )

        for datarow in self.tr_rows:

            """
            # >>>DEBUG<< for whedatarow.stripped_stringsn yahoo.com changes data model...
            y = 1
            print ( f"===================== Debug =========================" )
            #print ( f"Data {y}: {datarow}" )
            for i in datarow.find_all("td"):
                print ( f"===================================================" )
                if i.canvas is not None:
                    print ( f"Data {y}: Found Canvas, skipping..." )
                else:
                    print ( f"Data {y}: {i.text}" )
                    print ( f"Data g: {next(i.stripped_strings)}" )
                #logging.info( f'%s - Data: {debug_data.strings}' % cmi_debug )
                y += 1
            print ( f"===================== Debug =========================" )
            # >>>DEBUG<< for when yahoo.com changes data model...
            """

            # Data Extractor Generator
            def extr_gen():
                for i in datarow.find_all("td"):
                    if i.canvas is not None:
                        yield ( f"canvas" )
                    else:
                        yield ( f"{next(i.stripped_strings)}" )

            ################################ 1 ####################################
            extr_strs = extr_gen()
            co_sym = next(extr_strs)             # 1 : ticker symbol info / e.g "NWAU"
            co_name = next(extr_strs)            # 2 : company name / e.g "Consumer Automotive Finance, Inc."
            mini_chart = next(extr_strs)         # 3 : embeded mini GFX chart
            price = next(extr_strs)              # 3 : price (Intraday) / e.g "0.0031"

            ################################ 2 ####################################

            change_sign = next(extr_strs)        # 4 : test for dedicated column for +/- indicator
            logging.info( f"{cmi_debug} : {co_sym} : Check dedicated [+-] field for $ CHANGE" )
            if change_sign == "+" or change_sign == "-":    # 4 : is $ change sign [+/-] a dedciated field
                change_val = next(extr_strs)                # 4 : Yes, advance iterator to next field (ignore dedciated sign field)
            else:
                change_val = change_sign                    # 4 : get $ change, but its possibly +/- signed
                if (re.search(r'\+', change_val)) or (re.search(r'\-', change_val)) is not None:
                    logging.info( f"{cmi_debug} : {change_val} : $ CHANGE is signed [+-], stripping..." )
                    change_cl = re.sub(r'[\+\-]', "", change_val)       # remove +/- sign
                    logging.info( f"%s : $ CHANGE +/- cleaned : {change_cl}" % cmi_debug )
                else:
                    logging.info( f"{cmi_debug} : {change_val} : $ CHANGE is NOT signed [+-]" )
                    change_cl = re.sub(r'[\,]', "", change_val)       # remove
                    logging.info( f"%s : $ CHANGE , cleaned : {change_cl}" % cmi_debug )

            pct_sign = next(extr_strs)              # 5 : test for dedicated column for +/- indicator
            logging.info( f"{cmi_debug} : {co_sym} : Check dedicated [+-] field for % CHANGE" )
            if pct_sign == "+" or pct_sign == "-":  # 5 : is %_change sign [+/-] a dedciated field
                pct_val = next(extr_strs)           # 5 : advance iterator to next field (ignore dedciated sign field)
            else:
                pct_val = pct_sign                  # 5 get % change, but its possibly +/- signed
                if (re.search(r'\+', pct_val)) or (re.search(r'\-', pct_val)) is not None:
                    logging.info( f"{cmi_debug} : {pct_val} : % CHANGE is signed [+-], stripping..." )
                    pct_cl = re.sub(r'[\+\-\%]', "", pct_val)       # remove +/-/% signs
                    logging.info( f"{cmi_debug} : % CHANGE cleaned to: {pct_cl}" )
                else:
                    logging.info( f"{cmi_debug} : {pct_val} : % CHANGE is NOT signed [+-]" )
                    change_cl = re.sub(r'[\,\%]', "", pct_val)       # remove
                    logging.info( f"{cmi_debug} : % CHANGE: {pct_val}" )

            ################################ 3 ####################################
            vol = next(extr_strs)            # 6 : volume with scale indicator/ e.g "70.250k"
            avg_vol = next(extr_strs)        # 7 : Avg. vol over 3 months) / e.g "61,447"
            mktcap = next(extr_strs)         # 8 : Market cap with scale indicator / e.g "15.753B"
            peratio = next(extr_strs)        # 9 : PE ratio TTM (Trailing 12 months) / e.g "N/A"
            #mini_gfx = next(extr_strs)      # 10 : IGNORED = mini-canvas graphic 52-week rnage (no TXT/strings avail)

            ################################ 4 ####################################
            # now wrangle the data...
            co_sym_lj = f"{co_sym:<6}"                                   # left justify TXT in DF & convert to raw string
            co_name_lj = np.array2string(np.char.ljust(co_name, 60) )    # left justify TXT in DF & convert to raw string
            co_name_lj = (re.sub(r'[\'\"]', '', co_name_lj) )             # remove " ' and strip leading/trailing spaces     
            price_cl = (re.sub(r'\,', '', price))                         # remove ,
            price_clean = float(price_cl)
            change_clean = float(change_val)

            if pct_val == "N/A":
                pct_val = float(0.0)                               # Bad data. FOund a filed with N/A instead of read num
            else:
                pct_cl = re.sub(r'[\%\+\-,]', "", pct_val )
                pct_clean = float(pct_cl)

            ################################ 5 ####################################
            mktcap = (re.sub(r'[N\/A]', '0', mktcap))               # handle N/A
            TRILLIONS = re.search('T', mktcap)
            BILLIONS = re.search('B', mktcap)
            MILLIONS = re.search('M', mktcap)

            if TRILLIONS:
                mktcap_clean = float(re.sub('T', '', mktcap))
                mb = "LT"
                logging.info( f'%s : #{x} : {co_sym_lj} Mkt Cap: TRILLIONS : T' % cmi_debug )

            if BILLIONS:
                mktcap_clean = float(re.sub('B', '', mktcap))
                mb = "LB"
                logging.info( f'%s : #{x} : {co_sym_lj} Mkt cap: BILLIONS : B' % cmi_debug )

            if MILLIONS:
                mktcap_clean = float(re.sub('M', '', mktcap))
                mb = "LM"
                logging.info( f'%s : #{x} : {co_sym_lj} Mkt cap: MILLIONS : M' % cmi_debug )

            if not TRILLIONS and not BILLIONS and not MILLIONS:
                mktcap_clean = 0    # error condition - possible bad data
                mb = "LZ"           # Zillions
                logging.info( f'%s : #{x} : {co_sym_lj} bad mktcap data N/A : Z' % cmi_debug )
                # handle bad data in mktcap html page field

            ################################ 6 ####################################
            # now construct our list for concatinating to the dataframe 
            logging.info( f"%s ============= Data prepared for DF =============" % cmi_debug )

            self.list_data = [[ \
                       x, \
                       re.sub(r'\'', '', co_sym_lj), \
                       co_name_lj, \
                       price_clean, \
                       change_clean, \
                       pct_clean, \
                       mktcap_clean, \
                       mb, \
                       time_now ]]

            ################################ 7 ####################################
            self.df_1_row = pd.DataFrame(self.list_data, columns=[ 'Row', 'Symbol', 'Co_name', 'Cur_price', 'Prc_change', 'Pct_change', 'Mkt_cap', 'M_B', 'Time' ], index=[x] )
            self.tl_df0 = pd.concat([self.tl_df0, self.df_1_row])
            x+=1

        logging.info('%s - populated new DF0 dataset' % cmi_debug )
        return x        # number of rows inserted into DataFrame (0 = some kind of #FAIL)
                        # sucess = lobal class accessor (y_topgainers.*_df0) populated & updated

    # ----------------- 5 --------------------
    def topg_listall(self):
        """
        Print the full DataFrame table list of Yahoo Finance Top loserers
        Sorted by % Change
        """

        cmi_debug = __name__+"::"+self.topg_listall.__name__+".#"+str(self.yti)
        logging.info('%s - IN' % cmi_debug )
        pd.set_option('display.max_rows', None)
        pd.set_option('max_colwidth', 30)
        print ( self.tl_df0.sort_values(by='Pct_change', ascending=False ) )    # only do after fixtures datascience dataframe has been built
        return

    # ----------------- 6 --------------------
    def build_top10(self):
        """
        Get top 10 loserers from main DF (df0) -> temp DF (df1)
        Number of rows to grab is now set from num of rows that BS4 actually extracted (rows_extr)
        df1 is ephemerial. Is allways overwritten on each run
        """

        cmi_debug = __name__+"::"+self.build_top10.__name__+".#"+str(self.yti)
        logging.info('%s - IN' % cmi_debug )
        logging.info('%s - Drop all rows from DF1' % cmi_debug )
        self.tl_df1.drop(self.tl_df1.index, inplace=True)
        logging.info('%s - Copy DF0 -> ephemerial DF1' % cmi_debug )
        self.tl_df1 = self.tl_df0.sort_values(by='Pct_change', ascending=False ).head(self.rows_extr).copy(deep=True)    # create new DF via copy of top 10 entries
        self.tl_df1.rename(columns = {'Row':'ERank'}, inplace = True)   # Rank is more accurate for this Ephemerial DF
        self.tl_df1.reset_index(inplace=True, drop=True)    # reset index each time so its guaranteed sequential
        return

    # ----------------- 7 --------------------
    def print_top10(self):
        """
        Prints the Top 10 Dataframe
        Number of rows to grab is now set from num of rows that BS4 actually extracted (rows_extr)
        """

        cmi_debug = __name__+"::"+self.print_top10.__name__+".#"+str(self.yti)
        logging.info('%s - IN' % cmi_debug )
        pd.set_option('display.max_rows', None)
        pd.set_option('max_colwidth', 30)
        print ( f"{self.tl_df1.sort_values(by='Pct_change', ascending=False ).head(self.rows_extr)}" )
        return

    # ----------------- 8 --------------------
    def build_tenten60(self, cycle):
        """
        Build-up 10x10x060 historical DataFrame (df2) from source df1
        Generally called on some kind of cycle
        """

        cmi_debug = __name__+"::"+self.build_tenten60.__name__+".#"+str(self.yti)
        logging.info('%s - IN' % cmi_debug )
        self.tl_df2 = self.tl_df2.append(self.tl_df1, ignore_index=False)    # merge top 10 into
        self.tl_df2.reset_index(inplace=True, drop=True)    # ensure index is allways unique + sequential
        return

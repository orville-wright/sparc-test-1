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

# logging setup
logging.basicConfig(level=logging.INFO)

#####################################################
class y_topgainers:
    """
    Class to extract Top Gainer data set from finance.yahoo.com
    
    Uses requests-html to render JavaScript content and extract data from
    Yahoo Finance tables. Processes the data into pandas DataFrames for
    analysis and display.
    """
    # global accessors
    tg_df0 = ""          # DataFrame - Full list of top gainers
    tg_df1 = ""          # DataFrame - Ephemerial list of top 10 gainers. Allways overwritten
    tg_df2 = ""          # DataFrame - Top 10 ever 10 secs for 60 secs
    rows_extr = 0        # number of rows of data extracted
    ext_req = ""         # request URL open handled externally by y_cookiemonster
    tag_tbody = None     # requests-html Element for tbody
    tr_rows = None       # requests-html Elements for tr rows
    yti = 0
    cycle = 0            # class thread loop counter

    dummy_url = "https://finance.yahoo.com/markets/stocks/most-active/"

    yahoo_headers = { \
                        'authority': 'finance.yahoo.com', \
                        'path': '/markets/stocks/most-active/', \
                        'referer': 'https://finance.yahoo.com/markets/', \
                        'sec-ch-ua': '"Google Chrome";v="123", "Not:A-Brand";v="8", "Chromium";v="123"', \
                        'sec-ch-ua-mobile': '"?0"', \
                        'sec-fetch-mode': 'navigate', \
                        'sec-fetch-user': '"?1', \
                        'sec-fetch-site': 'same-origin', \
                        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.131 Safari/537.36' }

    # ----------------- 1 --------------------
    def __init__(self, yti):
        cmi_debug = __name__+"::"+self.__init__.__name__
        logging.info( f'%s Instance.#{yti}' % cmi_debug )
        # init empty DataFrame with present colum names
        self.tg_df0 = pd.DataFrame(columns=[ 'Row', 'Symbol', 'Co_name', 'Cur_price', 'Prc_change', 'Pct_change', 'Mkt_cap', 'M_B', 'Time'] )
        self.tg_df1 = pd.DataFrame(columns=[ 'ERank', 'Symbol', 'Co_name', 'Cur_price', 'Prc_change', 'Pct_change', 'Mkt_cap', 'M_B', 'Time'] )
        self.tg_df2 = pd.DataFrame(columns=[ 'ERank', 'Symbol', 'Co_name', 'Cur_price', 'Prc_change', 'Pct_change', 'Mkt_cap', 'M_B', 'Time'] )
        self.yti = yti
        return

    # ----------------- 2 --------------------
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
    
    # ----------------- 4 --------------------
    def build_tg_df0(self):
        """
        Build-out a fully populated Pandas DataFrame containg all the extracted/scraped fields from the
        html/markup table data Wrangle, clean/convert/format the data correctly.
        """

        cmi_debug = __name__+"::"+self.build_tg_df0.__name__+".#"+str(self.yti)
        logging.info('%s     - IN' % cmi_debug )
        time_now = time.strftime("%H:%M:%S", time.localtime() )
        logging.info('%s     - Create clean NULL DataFrame' % cmi_debug )
        self.tg_df0 = pd.DataFrame()             # new df, but is NULLed
        x = 0
        
        # Update row count calculation for requests-html
        self.rows_extr = int(len(self.tag_tbody.find('tr')))
        self.rows_tr_rows = int(len(self.tr_rows))
        
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
            try:
                # GENERATOR : Data Extractor that works with both requests-html and BeautifulSoup
                def extr_gen():
                    if hasattr(self, 'using_bs4') and self.using_bs4:
                        # BeautifulSoup version
                        for i in datarow.find_all("td"):
                            if i.canvas is not None:
                                yield ("canvas")
                            else:
                                yield (f"{next(i.stripped_strings)}")
                    else:
                        # requests-html version
                        for i in datarow.find("td"):
                            if i.find('canvas', first=True):
                                yield ("canvas")
                            else:
                                # Get text content - requests-html equivalent of stripped_strings
                                text = i.text.strip() if i.text else ""
                                
                                # Handle multi-line text content (common in newer Yahoo Finance format)
                                if '\n' in text:
                                    # Split by newline and take the first line (usually the main value)
                                    lines = text.split('\n')
                                    logging.info(f"{cmi_debug} GEN - Multi-line text detected: {text}")
                                    
                                    # For price, take the first line
                                    if len(lines) > 0 and all(c.isdigit() or c in '.-,' for c in lines[0].replace(',', '')):
                                        yield lines[0].strip()
                                    # For change values with +/- signs
                                    elif len(lines) > 1 and ('+' in lines[1] or '-' in lines[1]):
                                        yield lines[1].strip()
                                    # For percentage values with % sign
                                    elif len(lines) > 2 and '%' in lines[2]:
                                        yield lines[2].strip().strip('()')
                                    else:
                                        # Default to first line if we can't determine the format
                                        yield lines[0].strip()
                                else:
                                    yield text

                try:
                    ################################ 1 ####################################
                    extr_strs = extr_gen()
                    co_sym = next(extr_strs)             # 1 : ticker symbol info / e.g "NWAU"
                    co_name = next(extr_strs)            # 2 : company name / e.g "Consumer Automotive Finance, Inc."
                    mini_chart = next(extr_strs)         # 3 : embeded mini GFX chart
                    price = next(extr_strs)              # 3 : price (Intraday) / e.g "0.0031"
                    
                    logging.info(f"{cmi_debug} : Symbol: {co_sym}, Price: {price}")

                    ################################ 2 ####################################
                    # Handle change value
                    change_sign = next(extr_strs)        # 4 : test for dedicated column for +/- indicator
                    logging.info(f"{cmi_debug} : {co_sym} : Check $ CHANGE dedicated [+-] field...")
                    
                    # Clean up change value
                    change_val = change_sign
                    if change_val.startswith('+') or change_val.startswith('-'):
                        logging.info(f"{cmi_debug} : $ CHANGE: {change_val} [+-], stripping...")
                        change_cl = re.sub(r'[\+\-]', "", change_val)       # remove +/- sign
                        logging.info(f"{cmi_debug} : $ CHANGE cleaned to: {change_cl}")
                    else:
                        logging.info(f"{cmi_debug} : {change_val} : $ CHANGE is NOT signed [+-]")
                        change_cl = re.sub(r'[\,]', "", change_val)       # remove commas
                        logging.info(f"{cmi_debug} : $ CHANGE: {change_cl}")
                    
                    # Handle percentage value
                    pct_sign = next(extr_strs)              # 5 : test for dedicated column for +/- indicator
                    logging.info(f"{cmi_debug} : {co_sym} : Check % CHANGE dedicated [+-] field...")
                    
                    # Clean up percentage value
                    pct_val = pct_sign
                    if '%' in pct_val:
                        # Remove parentheses if present
                        pct_val = pct_val.strip('()')
                        
                    if (re.search(r'\+', pct_val)) or (re.search(r'\-', pct_val)) is not None:
                        logging.info(f"{cmi_debug} : % CHANGE {pct_val} [+-], stripping...")
                        pct_cl = re.sub(r'[\+\-\%]', "", pct_val)       # remove +/-/% signs
                        logging.info(f"{cmi_debug} : % CHANGE cleaned to: {pct_cl}")
                    else:
                        logging.info(f"{cmi_debug} : {pct_val} : % CHANGE is NOT signed [+-]")
                        pct_cl = re.sub(r'[\,\%]', "", pct_val)       # remove commas and % sign
                        logging.info(f"{cmi_debug} : % CHANGE: {pct_cl}")
 
                    ################################ 3 ####################################
                    try:
                        vol = next(extr_strs)            # 6 : volume with scale indicator/ e.g "70.250k"
                        avg_vol = next(extr_strs)        # 7 : Avg. vol over 3 months) / e.g "61,447"
                        mktcap = next(extr_strs)         # 8 : Market cap with scale indicator / e.g "15.753B"
                        peratio = next(extr_strs)        # 9 : PE ratio TTM (Trailing 12 months) / e.g "N/A"
                    except StopIteration:
                        # Handle case where some columns might be missing
                        logging.warning(f"{cmi_debug} : Not all expected columns found, using defaults for missing values")
                        vol = "0"
                        avg_vol = "0"
                        mktcap = "0"
                        peratio = "N/A"

                    ################################ 4 ####################################
                    # now wrangle the data...
                    co_sym_lj = f"{co_sym:<6}"                                   # left justify TXT in DF & convert to raw string
                    co_name_lj = np.array2string(np.char.ljust(co_name, 60) )    # left justify TXT in DF & convert to raw string
                    co_name_lj = (re.sub(r'[\'\"]', '', co_name_lj) )             # remove " ' and strip leading/trailing spaces
                    
                    # Clean price and convert to float
                    price_cl = (re.sub(r'[\,]', '', price))                      # remove commas
                    try:
                        price_clean = float(price_cl)
                    except ValueError:
                        logging.warning(f"{cmi_debug} : Could not convert price '{price_cl}' to float, using 0.0")
                        price_clean = 0.0
                    
                    # Clean change value and convert to float
                    try:
                        change_clean = float(re.sub(r'[\,]', '', change_cl))
                    except ValueError:
                        logging.warning(f"{cmi_debug} : Could not convert change '{change_cl}' to float, using 0.0")
                        change_clean = 0.0

                    # Clean percentage value and convert to float
                    if pct_val == "N/A":
                        pct_clean = float(0.0)                               # Bad data. Found a field with N/A instead of real num
                    else:
                        try:
                            pct_clean = float(re.sub(r'[\%\+\-,]', "", pct_val))
                        except ValueError:
                            logging.warning(f"{cmi_debug} : Could not convert percentage '{pct_val}' to float, using 0.0")
                            pct_clean = 0.0

                    ################################ 5 ####################################
                    # Clean market cap and determine scale (T, B, M)
                    mktcap = (re.sub(r'[N\/A]', '0', mktcap))               # handle N/A
                    TRILLIONS = re.search('T', mktcap)
                    BILLIONS = re.search('B', mktcap)
                    MILLIONS = re.search('M', mktcap)
                    mb = "LZ"  # Default to "Zillions" (unknown scale)
                    
                    try:
                        if TRILLIONS:
                            mktcap_clean = float(re.sub('T', '', mktcap))
                            mb = "LT"
                            logging.info(f'%s : #{x} : {co_sym_lj} Mkt Cap: TRILLIONS : T' % cmi_debug)
                        elif BILLIONS:
                            mktcap_clean = float(re.sub('B', '', mktcap))
                            mb = "LB"
                            logging.info(f'%s : #{x} : {co_sym_lj} Mkt cap: BILLIONS : B' % cmi_debug)
                        elif MILLIONS:
                            mktcap_clean = float(re.sub('M', '', mktcap))
                            mb = "LM"
                            logging.info(f'%s : #{x} : {co_sym_lj} Mkt cap: MILLIONS : M' % cmi_debug)
                        else:
                            # Try to convert directly to float if no scale indicator
                            try:
                                mktcap_clean = float(re.sub(r'[\,]', '', mktcap))
                                mb = "LZ"  # Unknown scale
                            except ValueError:
                                mktcap_clean = 0    # error condition - possible bad data
                                mb = "LZ"           # Zillions
                                logging.info(f'%s : #{x} : {co_sym_lj} bad mktcap data N/A : Z' % cmi_debug)
                    except ValueError:
                        mktcap_clean = 0    # error condition - possible bad data
                        mb = "LZ"           # Zillions
                        logging.info(f'%s : #{x} : {co_sym_lj} bad mktcap data, could not convert to float: {mktcap}' % cmi_debug)
                        
                except Exception as e:
                    logging.error(f"{cmi_debug} : Error processing row: {e}")
                    continue  # Skip this row and move to the next one

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
                self.tg_df0 = pd.concat([self.tg_df0, self.df_1_row])  
                x+=1
            except StopIteration:
                logging.error(f"{cmi_debug} : StopIteration error - not enough cells in row")
                continue
            except Exception as e:
                logging.error(f"{cmi_debug} : Error processing row: {e}")
                continue

        logging.info('%s - populated new DF0 dataset' % cmi_debug )
        return x        # number of rows inserted into DataFrame (0 = some kind of #FAIL)
                        # sucess = lobal class accessor (y_toplosers.tg_df0) populated & updated

    # ----------------- 5 --------------------
    def topg_listall(self):
        """Print the full DataFrame table list of Yahoo Finance Top Gainers"""
        """Sorted by % Change"""

        cmi_debug = __name__+"::"+self.topg_listall.__name__+".#"+str(self.yti)
        logging.info('%s - IN' % cmi_debug )
        pd.set_option('display.max_rows', None)
        pd.set_option('max_colwidth', 30)
        print ( self.tg_df0.sort_values(by='Pct_change', ascending=False ) )    # only do after fixtures datascience dataframe has been built
        return

    # ----------------- 6 --------------------
    def build_top10(self):
        """
        Get top gainers from main DF (df0) -> temp DF (df1)
        Number of rows to grab is now set from num of rows that BS4 actually extracted (rows_extr)
        df1 is ephemerial. Is allways overwritten on each run
        """

        cmi_debug = __name__+"::"+self.build_top10.__name__+".#"+str(self.yti)
        logging.info('%s - IN' % cmi_debug )
        logging.info('%s - Drop all rows from DF1' % cmi_debug )
        self.tg_df1.drop(self.tg_df1.index, inplace=True)
        logging.info('%s - Copy DF0 -> ephemerial DF1' % cmi_debug )
        self.tg_df1 = self.tg_df0.sort_values(by='Pct_change', ascending=False ).head(self.rows_extr).copy(deep=True)    # create new DF via copy of top 10 entries
        self.tg_df1.rename(columns = {'Row':'ERank'}, inplace = True)    # Rank is more accurate for this Ephemerial DF
        self.tg_df1.reset_index(inplace=True, drop=True)    # reset index each time so its guaranteed sequential
        return

    # ----------------- 7 --------------------
    def print_top10(self):
        """
        Prints the Top 10 Dataframe
        Number of rows to print is now set from num of rows that BS4 actually extracted (rows_extr)
        """

        cmi_debug = __name__+"::"+self.print_top10.__name__+".#"+str(self.yti)
        logging.info('%s - IN' % cmi_debug )
        pd.set_option('display.max_rows', None)
        pd.set_option('max_colwidth', 30)
        self.tg_df1.style.set_properties(**{'text-align': 'left'})
        print ( f"{self.tg_df1.sort_values(by='Pct_change', ascending=False ).head(self.rows_extr)}" )
        return

    # ----------------- 8 --------------------
    def build_tenten60(self, cycle):
        """Build-up 10x10x060 historical DataFrame (df2) from source df1"""
        """Generally called on some kind of cycle"""

        cmi_debug = __name__+"::"+self.build_tenten60.__name__+".#"+str(self.yti)
        logging.info('%s - IN' % cmi_debug )
        # Updated from append (deprecated) to pd.concat
        self.tg_df2 = pd.concat([self.tg_df2, self.tg_df1], ignore_index=False)    # merge top 10 into
        self.tg_df2.reset_index(inplace=True, drop=True)    # ensure index is allways unique + sequential
        return

    # ----------------- 9 --------------------
    def safe_render(self, response, max_retries=3, initial_timeout=20):
        """Safely render JavaScript content with retries"""
        timeout = initial_timeout
        for attempt in range(1, max_retries + 1):
            try:
                logging.info(f"Rendering attempt {attempt}/{max_retries} with timeout {timeout}s")
                response.html.render(timeout=timeout, sleep=1)
                return True
            except Exception as e:
                logging.error(f"Render attempt {attempt} failed: {e}")
                timeout = timeout * 1.5  # Increase timeout for next attempt
                if attempt == max_retries:
                    logging.warning("All rendering attempts failed, falling back to non-rendered content")
                    return False

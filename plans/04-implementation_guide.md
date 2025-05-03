# Implementation Guide: BeautifulSoup to requests-html Migration

This guide provides concrete code examples and step-by-step instructions for implementing each phase of the refactoring plan.

## Phase 1: Environment Setup and Imports

### 1.1 Install requests-html

```bash
pip install requests-html
```

### 1.2 Update Imports

```python
# Before
import requests
from bs4 import BeautifulSoup
import pandas as pd
import numpy as np
import re
import logging
import argparse
import time
from rich import print

# After
import requests
from requests_html import HTMLSession, HTML
import pandas as pd
import numpy as np
import re
import logging
import argparse
import time
from rich import print
```

## Phase 2: Class Attribute Updates

### 2.1 Update Class Attributes

```python
# Before
class y_topgainers:
    """Class to extract Top Gainer data set from finance.yahoo.com"""
    # global accessors
    tg_df0 = ""          # DataFrame - Full list of top gainers
    tg_df1 = ""          # DataFrame - Ephemerial list of top 10 gainers. Allways overwritten
    tg_df2 = ""          # DataFrame - Top 10 ever 10 secs for 60 secs
    all_tag_tr = ""      # BS4 handle of the <tr> extracted data
    soup = ""            # BeautifulSoup object
    rows_extr = 0        # number of rows of data extracted
    ext_req = ""         # request was handled by y_cookiemonster
    yti = 0
    cycle = 0            # class thread loop counter

# After
class y_topgainers:
    """Class to extract Top Gainer data set from finance.yahoo.com"""
    # global accessors
    tg_df0 = ""          # DataFrame - Full list of top gainers
    tg_df1 = ""          # DataFrame - Ephemerial list of top 10 gainers. Allways overwritten
    tg_df2 = ""          # DataFrame - Top 10 ever 10 secs for 60 secs
    rows_extr = 0        # number of rows of data extracted
    ext_req = ""         # request was handled by y_cookiemonster
    tag_tbody = None     # requests-html Element for tbody
    tr_rows = None       # requests-html Elements for tr rows
    yti = 0
    cycle = 0            # class thread loop counter
```

## Phase 3: Update External Request Handling

### 3.1 Update init_dummy_session Method

```python
# Before
def init_dummy_session(self):
    self.dummy_resp0 = requests.get(self.dummy_url, stream=True, headers=self.yahoo_headers, cookies=self.yahoo_headers, timeout=5)
    hot_cookies = requests.utils.dict_from_cookiejar(self.dummy_resp0.cookies)
    return

# After
def init_dummy_session(self):
    session = HTMLSession()
    self.dummy_resp0 = session.get(self.dummy_url, headers=self.yahoo_headers, timeout=5)
    hot_cookies = self.dummy_resp0.cookies.get_dict()
    return
```

### 3.2 Update ext_get_data Method

```python
# Before
def ext_get_data(self, yti):
    """
    Connect to finance.yahoo.com and extract (scrape) the raw string data out of
    the webpage data tables. Returns a BS4 handle.
    Send hint which engine processed & rendered the html page
    not implimented yet...
        0. Simple HTML engine
        1. JAVASCRIPT HTML render engine (down redering a complex JS page in to simple HTML)
    """
    self.yti = yti
    cmi_debug = __name__+"::"+self.ext_get_data.__name__+".#"+str(self.yti)
    logging.info('%s - IN' % cmi_debug )
    logging.info('%s - ext request pre-processed by cookiemonster...' % cmi_debug )
    # use preexisting resposne from  managed req (handled by cookie monster) 
    r = self.ext_req
    logging.info( f"%s - BS4 stream processing..." % cmi_debug )
    self.soup = BeautifulSoup(r.text, 'html.parser')
    self.tag_tbody = self.soup.find('tbody')
    self.tr_rows = self.tag_tbody.find_all("tr")
    logging.info('%s Page processed by BS4 engine' % cmi_debug )
    return

# After
def ext_get_data(self, yti):
    """
    Connect to finance.yahoo.com and extract (scrape) the raw string data out of
    the webpage data tables. Returns a requests-html handle.
    Send hint which engine processed & rendered the html page
    not implemented yet...
        0. Simple HTML engine
        1. JAVASCRIPT HTML render engine (down rendering a complex JS page into simple HTML)
    """
    self.yti = yti
    cmi_debug = __name__+"::"+self.ext_get_data.__name__+".#"+str(self.yti)
    logging.info('%s - IN' % cmi_debug )
    logging.info('%s - ext request pre-processed by cookiemonster...' % cmi_debug )
    
    # use preexisting response from managed req (handled by cookie monster) 
    r = self.ext_req
    
    # Add JavaScript rendering capability
    try:
        # If ext_req is a requests-html Response object, render JavaScript
        if hasattr(r, 'html') and hasattr(r.html, 'render'):
            logging.info(f"%s - Rendering JavaScript content..." % cmi_debug)
            r.html.render(timeout=20, sleep=1)
        # If ext_req is a standard requests Response object, convert to requests-html
        else:
            logging.info(f"%s - Converting requests Response to requests-html..." % cmi_debug)
            # Create HTML object from response text
            html = HTML(html=r.text, url=r.url)
            # Store HTML object on response for consistency
            r.html = html
            logging.info(f"%s - Rendering JavaScript content..." % cmi_debug)
            r.html.render(timeout=20, sleep=1)
    except Exception as e:
        logging.error(f"%s - Failed to render JavaScript: {e}" % cmi_debug)
        # Continue with non-rendered content
        if not hasattr(r, 'html'):
            r.html = HTML(html=r.text, url=r.url)
    
    logging.info(f"%s - requests-html processing..." % cmi_debug)
    
    # Find tbody using CSS selector
    self.tag_tbody = r.html.find('tbody', first=True)
    
    if not self.tag_tbody:
        logging.error(f"%s - Could not find the <tbody> element." % cmi_debug)
        return None
        
    # Find all tr elements within tbody
    self.tr_rows = self.tag_tbody.find("tr")
    
    logging.info(f'%s - Found {len(self.tr_rows)} rows in the table.' % cmi_debug)
    logging.info('%s - Page processed by requests-html engine' % cmi_debug)
    return
```

## Phase 4: Update Data Extraction Logic

### 4.1 Update build_tg_df0 Method

```python
# Before (extraction generator part)
def extr_gen(): 
    for i in datarow.find_all("td"):
        if i.canvas is not None:
            yield ( f"canvas" )
        else:
            yield ( f"{next(i.stripped_strings)}" )

# After (extraction generator part)
def extr_gen(): 
    for i in datarow.find("td"):
        if i.find('canvas', first=True):
            yield ("canvas")
        else:
            # Get text content - requests-html equivalent of stripped_strings
            text = i.text.strip() if i.text else ""
            yield text
```

### 4.2 Update Row Count Calculation

```python
# Before
self.rows_extr = int(len(self.tag_tbody.find_all('tr')))
self.rows_tr_rows = int(len(self.tr_rows))

# After
self.rows_extr = int(len(self.tag_tbody.find('tr')))
self.rows_tr_rows = int(len(self.tr_rows))
```

## Phase 5: Update Remaining Methods

### 5.1 Update build_tenten60 Method

```python
# Before
def build_tenten60(self, cycle):
    """Build-up 10x10x060 historical DataFrame (df2) from source df1"""
    """Generally called on some kind of cycle"""

    cmi_debug = __name__+"::"+self.build_tenten60.__name__+".#"+str(self.yti)
    logging.info('%s - IN' % cmi_debug )
    self.tg_df2 = self.tg_df2.append(self.tg_df1, ignore_index=False)    # merge top 10 into
    self.tg_df2.reset_index(inplace=True, drop=True)    # ensure index is allways unique + sequential
    return

# After
def build_tenten60(self, cycle):
    """Build-up 10x10x060 historical DataFrame (df2) from source df1"""
    """Generally called on some kind of cycle"""

    cmi_debug = __name__+"::"+self.build_tenten60.__name__+".#"+str(self.yti)
    logging.info('%s - IN' % cmi_debug )
    self.tg_df2 = pd.concat([self.tg_df2, self.tg_df1], ignore_index=False)    # merge top 10 into
    self.tg_df2.reset_index(inplace=True, drop=True)    # ensure index is allways unique + sequential
    return
```

## Phase 6: Error Handling Enhancements

### 6.1 Add Robust Error Handling to Data Extraction

```python
# Add to build_tg_df0 method
try:
    # Extraction logic here
    extr_strs = extr_gen()
    co_sym = next(extr_strs)
    co_name = next(extr_strs)
    # ...
except StopIteration:
    logging.error(f"{cmi_debug} : StopIteration error - not enough cells in row")
    continue
except Exception as e:
    logging.error(f"{cmi_debug} : Error processing row: {e}")
    continue
```

### 6.2 Add Fallback for JavaScript Rendering

```python
# Add to ext_get_data method
try:
    r.html.render(timeout=20, sleep=1)
except Exception as e:
    logging.error(f"{cmi_debug} - Failed to render JavaScript: {e}")
    logging.info(f"{cmi_debug} - Continuing with non-rendered content")
    # Continue with non-rendered content
```

## Phase 7: Testing Implementation

### 7.1 Unit Test for JavaScript Rendering

```python
def test_js_rendering():
    """Test JavaScript rendering with requests-html"""
    session = HTMLSession()
    r = session.get("https://finance.yahoo.com/gainers?count=100")
    r.html.render(timeout=30)
    
    # Verify rendered content contains expected elements
    tbody = r.html.find('tbody', first=True)
    assert tbody is not None, "Could not find tbody element after rendering"
    
    tr_rows = tbody.find('tr')
    assert len(tr_rows) > 0, "No table rows found after rendering"
    
    # Check for expected columns
    for row in tr_rows[:1]:  # Check first row
        td_cells = row.find('td')
        assert len(td_cells) >= 8, "Not enough columns in rendered table"
```

### 7.2 Compare Output with Original Implementation

```python
def compare_implementations():
    """Compare BeautifulSoup and requests-html implementations"""
    # Original implementation
    from bs4 import BeautifulSoup
    import requests
    
    # Get data with standard requests/BS4
    r_bs4 = requests.get("https://finance.yahoo.com/gainers?count=100", headers=yahoo_headers)
    soup = BeautifulSoup(r_bs4.text, 'html.parser')
    tbody_bs4 = soup.find('tbody')
    rows_bs4 = tbody_bs4.find_all("tr") if tbody_bs4 else []
    
    # Get data with requests-html
    session = HTMLSession()
    r_html = session.get("https://finance.yahoo.com/gainers?count=100", headers=yahoo_headers)
    r_html.html.render(timeout=30)
    tbody_html = r_html.html.find('tbody', first=True)
    rows_html = tbody_html.find('tr') if tbody_html else []
    
    print(f"BS4 found {len(rows_bs4)} rows")
    print(f"requests-html found {len(rows_html)} rows")
    
    # Compare first row data
    if rows_bs4 and rows_html:
        bs4_cells = [cell.text.strip() for cell in rows_bs4[0].find_all('td') if cell.text.strip()]
        html_cells = [cell.text.strip() for cell in rows_html[0].find('td') if cell.text.strip()]
        
        print("BS4 first row:", bs4_cells)
        print("requests-html first row:", html_cells)
```

## Phase 8: Code Cleanup and Documentation

### 8.1 Update Class Docstring

```python
class y_topgainers:
    """
    Class to extract Top Gainer data set from finance.yahoo.com
    
    Uses requests-html to render JavaScript content and extract data from
    Yahoo Finance tables. Processes the data into pandas DataFrames for
    analysis and display.
    """
```

### 8.2 Update Method Docstrings

```python
def ext_get_data(self, yti):
    """
    Connect to finance.yahoo.com and extract data from the webpage tables.
    
    Uses requests-html to render JavaScript content, ensuring dynamic data
    is properly loaded before extraction. Returns a collection of HTML elements
    representing table rows.
    
    Parameters:
        yti: Instance identifier
        
    Returns:
        None, but populates self.tr_rows with requests-html Elements
    """
```

## Phase 9: Deployment Considerations

### 9.1 Add First-Run Warning

```python
# Add to module initialization
import logging

logging.info("First run of requests-html may download Chromium (~150MB)")
```

### 9.2 Add Resource Monitoring

```python
import psutil
import os

def log_resource_usage():
    """Log memory usage during JavaScript rendering"""
    process = psutil.Process(os.getpid())
    mem_before = process.memory_info().rss / 1024 / 1024  # MB
    
    # Perform rendering
    session = HTMLSession()
    r = session.get("https://finance.yahoo.com/gainers")
    r.html.render(timeout=30)
    
    mem_after = process.memory_info().rss / 1024 / 1024  # MB
    logging.info(f"Memory usage: Before rendering: {mem_before:.2f}MB, After: {mem_after:.2f}MB, Difference: {mem_after - mem_before:.2f}MB")
```

## Implementation Checklist

- [ ] Install requests-html
- [ ] Update imports
- [ ] Update class attributes
- [ ] Refactor ext_get_data method
- [ ] Update init_dummy_session method (if needed)
- [ ] Update data extraction generator in build_tg_df0
- [ ] Update row count calculations
- [ ] Update build_tenten60 method to use pd.concat
- [ ] Add enhanced error handling
- [ ] Add fallback for JavaScript rendering failures
- [ ] Implement unit tests
- [ ] Compare output with original implementation
- [ ] Update docstrings and comments
- [ ] Add first-run warning
- [ ] Monitor resource usage

## Troubleshooting Common Issues

### JavaScript Rendering Timeout

If JavaScript rendering times out, try increasing the timeout and adding a sleep parameter:

```python
r.html.render(timeout=30, sleep=2)  # Increase timeout and add sleep
```

### Element Not Found After Rendering

If elements aren't found after rendering, check if the page structure matches expectations:

```python
# Debugging element structure
all_elements = r.html.find('*')
for el in all_elements[:20]:  # Look at first 20 elements
    print(f"Tag: {el.tag}, Classes: {el.attrs.get('class', [])}")
```

### Text Extraction Differences

If text extraction differs between BeautifulSoup and requests-html:

```python
# BeautifulSoup stripped_strings alternative for requests-html
def get_clean_text(element):
    """Get clean text similar to BS4's stripped_strings"""
    text = element.text.strip()
    # Remove excessive whitespace
    text = re.sub(r'\s+', ' ', text)
    return text
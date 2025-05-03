#!/usr/bin/env python3
"""
Test script for the refactored y_topgainers.py module.
This script tests the migration from BeautifulSoup to requests-html.
"""

import logging
import time
import requests
from requests_html import HTMLSession
from y_topgainers import y_topgainers

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_direct_request():
    """Test direct request to Yahoo Finance using requests-html with fallback to BeautifulSoup."""
    logger.info("Testing direct request with requests-html and BeautifulSoup fallback...")
    
    url = "https://finance.yahoo.com/gainers"
    
    # Create headers similar to those in y_topgainers
    headers = {
        'authority': 'finance.yahoo.com',
        'path': '/gainers',
        'referer': 'https://finance.yahoo.com/markets/',
        'sec-ch-ua': '"Google Chrome";v="123", "Not:A-Brand";v="8", "Chromium";v="123"',
        'sec-ch-ua-mobile': '"?0"',
        'sec-fetch-mode': 'navigate',
        'sec-fetch-user': '"?1',
        'sec-fetch-site': 'same-origin',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.131 Safari/537.36'
    }
    
    try:
        # Create session and make request
        session = HTMLSession()
        response = session.get(url, headers=headers, timeout=10)
        
        # Try to render JavaScript (but expect it to fail in this environment)
        logger.info("Attempting JavaScript rendering (may not be available)...")
        try:
            response.html.render(timeout=30, sleep=2)
            logger.info("JavaScript rendering successful")
            js_rendered = True
        except Exception as e:
            logger.warning(f"JavaScript rendering not available (expected): {e}")
            logger.info("Continuing with non-rendered content")
            js_rendered = False
        
        # First try with requests-html
        tbody = response.html.find('tbody', first=True)
        
        # If requests-html can't find tbody, try BeautifulSoup
        if not tbody:
            logger.info("Could not find tbody with requests-html, trying BeautifulSoup...")
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(response.text, 'html.parser')
            bs_tbody = soup.find('tbody')
            
            if bs_tbody:
                rows = bs_tbody.find_all('tr')
                logger.info(f"Found {len(rows)} rows in the table using BeautifulSoup")
                
                # Check if we can extract data from the first row
                if rows and len(rows) > 0:
                    first_row = rows[0]
                    cells = first_row.find_all('td')
                    logger.info(f"First row has {len(cells)} cells")
                    
                    # Extract symbol from first cell
                    if cells and len(cells) > 0 and cells[0].text:
                        symbol = cells[0].text.strip()
                        logger.info(f"First symbol: {symbol}")
                        return True
                    else:
                        logger.error("No text content in the first cell")
                else:
                    logger.error("No rows found in the table")
            else:
                logger.error("Could not find tbody element with BeautifulSoup either")
                return False
        else:
            # requests-html found tbody
            rows = tbody.find('tr')
            logger.info(f"Found {len(rows)} rows in the table using requests-html")
            
            # Check if we can extract data from the first row
            if rows and len(rows) > 0:
                first_row = rows[0]
                cells = first_row.find('td')
                logger.info(f"First row has {len(cells)} cells")
                
                # Extract symbol from first cell
                if cells and len(cells) > 0:
                    symbol = cells[0].text.strip()
                    logger.info(f"First symbol: {symbol}")
                    return True
                else:
                    logger.error("No cells found in the first row")
            else:
                logger.error("No rows found in the table")
        
        return False
    except Exception as e:
        logger.error(f"Direct request test failed: {e}")
        return False

def test_y_topgainers_class():
    """Test the refactored y_topgainers class with fallback to BeautifulSoup."""
    logger.info("Testing refactored y_topgainers class with BeautifulSoup fallback...")
    
    try:
        # Create instance
        ytg = y_topgainers(1)
        logger.info("Created y_topgainers instance")
        
        # Test dummy session
        result = ytg.init_dummy_session()
        logger.info(f"init_dummy_session result: {result}")
        
        # Create a direct request to simulate what y_cookiemonster would do
        url = "https://finance.yahoo.com/gainers"
        
        # Try with requests-html first
        try:
            session = HTMLSession()
            response = session.get(url, headers=ytg.yahoo_headers, timeout=10)
            logger.info("Created requests-html session")
        except Exception as e:
            logger.warning(f"Failed to create requests-html session: {e}")
            logger.info("Falling back to standard requests")
            response = requests.get(url, headers=ytg.yahoo_headers, timeout=10)
            logger.info("Created standard requests session")
        
        # Set the external request
        ytg.ext_req = response
        logger.info("Set external request")
        
        # Test ext_get_data
        ytg.ext_get_data(1)
        logger.info("Called ext_get_data")
        
        # Check if we have rows
        if ytg.tr_rows and len(ytg.tr_rows) > 0:
            logger.info(f"Found {len(ytg.tr_rows)} rows")
            
            # Test build_tg_df0
            rows_inserted = ytg.build_tg_df0()
            logger.info(f"build_tg_df0 inserted {rows_inserted} rows")
            
            # Check if DataFrame has data
            if not ytg.tg_df0.empty:
                logger.info(f"DataFrame has {len(ytg.tg_df0)} rows")
                
                # Test build_top10
                ytg.build_top10()
                logger.info(f"Built top 10 DataFrame with {len(ytg.tg_df1)} rows")
                
                # Test build_tenten60
                ytg.build_tenten60(1)
                logger.info(f"Built tenten60 DataFrame with {len(ytg.tg_df2)} rows")
                
                # Print sample data
                logger.info("Sample data from tg_df1:")
                if len(ytg.tg_df1) > 0:
                    sample = ytg.tg_df1.iloc[0]
                    logger.info(f"Symbol: {sample['Symbol']}, Price: {sample['Cur_price']}, Change: {sample['Pct_change']}%")
                
                # Log which parsing method was used
                if hasattr(ytg, 'using_bs4') and ytg.using_bs4:
                    logger.info("Test used BeautifulSoup fallback for parsing")
                else:
                    logger.info("Test used requests-html for parsing")
                
                return True
            else:
                logger.error("DataFrame is empty")
        else:
            logger.error("No rows found")
        
        return False
    except Exception as e:
        logger.error(f"y_topgainers class test failed: {e}")
        return False

def main():
    """Main test function."""
    logger.info("Starting tests for refactored y_topgainers...")
    
    # Test direct request
    direct_result = test_direct_request()
    logger.info(f"Direct request test {'PASSED' if direct_result else 'FAILED'}")
    
    # Test y_topgainers class
    class_result = test_y_topgainers_class()
    logger.info(f"y_topgainers class test {'PASSED' if class_result else 'FAILED'}")
    
    # Overall result
    if direct_result and class_result:
        logger.info("All tests PASSED!")
    else:
        logger.error("Some tests FAILED!")

if __name__ == "__main__":
    main()
import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta
import os

# Set page configuration
st.set_page_config(
    page_title="שערי חליפין - בנק ישראל",
    page_icon="💱",
    layout="wide"
)

# Main title
st.title("💱 הורדת שערי חליפין מבנק ישראל")
st.markdown("---")

# Sidebar for filters
st.sidebar.header("🔧 הגדרות סינון")

# Base Currency selection
st.sidebar.subheader("בחירת Base Currency")
available_base_currencies = ["ILS", "USD"]
selected_base_currencies = st.sidebar.multiselect(
    "בחר Base Currency:",
    available_base_currencies,
    default=["ILS", "USD"],
    help="בחר את המטבעות הבסיסיים"
)

# Source Currency selection with mapping to SDMX codes
st.sidebar.subheader("בחירת Source Currency")
currency_mapping = {
    "USD": "RER_USD_ILS",
    "EUR": "RER_EUR_ILS", 
    "GBP": "RER_GBP_ILS",
    "CHF": "RER_CHF_ILS",
    "JPY": "RER_JPY_ILS",
    "CAD": "RER_CAD_ILS",
    "AUD": "RER_AUD_ILS",
    "NOK": "RER_NOK_ILS",
    "SEK": "RER_SEK_ILS",
    "DKK": "RER_DKK_ILS"
}

available_currencies = list(currency_mapping.keys())
selected_currencies = st.sidebar.multiselect(
    "בחר מטבעות מקור:",
    available_currencies,
    default=["USD", "EUR", "GBP"],
    help="בחר את המטבעות שברצונך לכלול בקובץ"
)

# Date range selection
st.sidebar.subheader("טווח תאריכים")
col1, col2 = st.sidebar.columns(2)
with col1:
    start_date = st.date_input(
        "מתאריך:",
        datetime.now() - timedelta(days=30),
        help="תאריך התחלה"
    )
with col2:
    end_date = st.date_input(
        "עד תאריך:",
        datetime.now(),
        help="תאריך סיום"
    )

# Download button
download_button = st.sidebar.button("📥 הורד נתונים", type="primary", use_container_width=True)

# Main content area
def fetch_exchange_rates(selected_currencies, start_date, end_date):
    """
    Fetch exchange rates from Bank of Israel SDMX API
    """
    try:
        # Build currency codes for the API
        currency_codes = [currency_mapping[curr] for curr in selected_currencies]
        currencies_str = ",".join(currency_codes)
        
        # Format dates for the API
        start_str = start_date.strftime("%Y-%m-%d")
        end_str = end_date.strftime("%Y-%m-%d")
        
        # Construct the SDMX API URL
        base_url = "https://edge.boi.org.il/FusionEdgeServer/sdmx/v2/data/dataflow/BOI.STATISTICS/EXR/1.0"
        url = f"{base_url}/{currencies_str}?format=csv&startperiod={start_str}&endperiod={end_str}&c%5BDATA_TYPE%5D=OF00"
        
        # Make the request
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        
        # Read CSV data directly
        from io import StringIO
        csv_data = StringIO(response.text)
        df = pd.read_csv(csv_data)
        
        return df, None
    
    except requests.exceptions.RequestException as e:
        return None, f"שגיאה בחיבור לשרת בנק ישראל: {str(e)}"
    except Exception as e:
        return None, f"שגיאה בעיבוד הנתונים: {str(e)}"

def process_exchange_data(df, selected_currencies, selected_base_currencies):
    """
    Process the exchange rates data from SDMX API to create Base/Source currency structure
    """
    try:
        if df.empty:
            return None, "לא התקבלו נתונים"
        
        # Convert TIME_PERIOD to datetime
        df['DATE'] = pd.to_datetime(df['TIME_PERIOD'])
        
        # Extract currency from SERIES_CODE (e.g., RER_USD_ILS -> USD)
        df['SOURCE_CURRENCY'] = df['SERIES_CODE'].str.extract(r'RER_([A-Z]{3})_ILS')
        
        # Rename OBS_VALUE to RATE for clarity
        df['RATE_VS_ILS'] = pd.to_numeric(df['OBS_VALUE'], errors='coerce')
        
        # Filter for selected currencies
        df_filtered = df[df['SOURCE_CURRENCY'].isin(selected_currencies)].copy()
        
        # Create the final structured dataframe
        result_rows = []
        
        # Get USD rates for calculation
        usd_data = df_filtered[df_filtered['SOURCE_CURRENCY'] == 'USD'][['DATE', 'RATE_VS_ILS']].copy()
        usd_data.columns = ['DATE', 'USD_RATE']
        
        # Get unique dates for processing
        unique_dates = df_filtered['DATE'].unique()
        
        # Create all source currencies list (including ILS)
        all_source_currencies = list(set(selected_currencies + ['ILS']))
        
        for date in unique_dates:
            date_data = df_filtered[df_filtered['DATE'] == date]
            
            # Process for each selected base currency
            for base_currency in selected_base_currencies:
                
                # Add base/base = 1.0 row (ILS/ILS or USD/USD)
                result_rows.append({
                    'Effective_Date': date,
                    'Base_Currency': base_currency,
                    'Source_Currency': base_currency,
                    'Exchange_Rate': 1.0
                })
                
                # Process each source currency for this base currency
                for source_currency in all_source_currencies:
                    if source_currency != base_currency:
                        
                        if base_currency == 'ILS':
                            # For ILS base currency
                            if source_currency in selected_currencies:
                                # Find the rate for this source currency
                                source_data = date_data[date_data['SOURCE_CURRENCY'] == source_currency]
                                if not source_data.empty:
                                    rate = source_data['RATE_VS_ILS'].iloc[0]
                                    result_rows.append({
                                        'Effective_Date': date,
                                        'Base_Currency': 'ILS',
                                        'Source_Currency': source_currency,
                                        'Exchange_Rate': rate
                                    })
                        
                        elif base_currency == 'USD' and 'USD' in selected_currencies:
                            # For USD base currency
                            usd_rate_row = usd_data[usd_data['DATE'] == date]
                            if not usd_rate_row.empty:
                                usd_rate = usd_rate_row['USD_RATE'].iloc[0]
                                
                                if source_currency == 'ILS':
                                    # USD/ILS rate (inverse of USD rate)
                                    rate = 1.0 / usd_rate
                                elif source_currency in selected_currencies:
                                    # Other currencies vs USD
                                    source_data = date_data[date_data['SOURCE_CURRENCY'] == source_currency]
                                    if not source_data.empty:
                                        source_rate = source_data['RATE_VS_ILS'].iloc[0]
                                        rate = source_rate / usd_rate
                                    else:
                                        continue
                                else:
                                    continue
                                
                                result_rows.append({
                                    'Effective_Date': date,
                                    'Base_Currency': 'USD',
                                    'Source_Currency': source_currency,
                                    'Exchange_Rate': rate
                                })
        
        # Create final dataframe
        result_df = pd.DataFrame(result_rows)
        
        # Format the date as DD/MM/YYYY
        result_df['Effective_Date'] = pd.to_datetime(result_df['Effective_Date']).dt.strftime('%d/%m/%Y')
        
        # Convert date back to datetime for proper sorting
        result_df['Date_for_sorting'] = pd.to_datetime(result_df['Effective_Date'], format='%d/%m/%Y')
        
        # Sort by date, base currency, then source currency
        result_df = result_df.sort_values(['Date_for_sorting', 'Base_Currency', 'Source_Currency'])
        
        # Drop the sorting column
        result_df = result_df.drop('Date_for_sorting', axis=1)
        
        return result_df, None
    
    except Exception as e:
        return None, f"שגיאה בעיבוד הנתונים: {str(e)}"

def display_current_rates(df, selected_currencies):
    """
    Display current exchange rates in a nice format
    """
    st.subheader("📊 שערי חליפין נוכחיים")
    
    try:
        if df.empty:
            st.warning("אין נתונים להצגה")
            return
            
        # Convert date strings back to datetime for comparison
        latest_date = pd.to_datetime(df['Effective_Date'], format='%d/%m/%Y').max()
        latest_data = df[pd.to_datetime(df['Effective_Date'], format='%d/%m/%Y') == latest_date]
        
        # Get ILS rates
        ils_rates = latest_data[latest_data['Base_Currency'] == 'ILS']
        
        # Display in columns
        cols = st.columns(len(selected_currencies))
        for i, currency in enumerate(selected_currencies):
            if i < len(cols):
                with cols[i]:
                    rate_data = ils_rates[ils_rates['Source_Currency'] == currency]
                    if not rate_data.empty:
                        rate = rate_data['Exchange_Rate'].iloc[0]
                        st.metric(
                            label=f"{currency}/ILS",
                            value=f"{rate:.4f}",
                            help=f"שער חליפין עדכני עבור {currency}"
                        )
                    else:
                        st.metric(
                            label=f"{currency}/ILS",
                            value="לא זמין",
                            help=f"נתונים לא זמינים עבור {currency}"
                        )
    except Exception as e:
        st.error(f"שגיאה בהצגת השערים הנוכחיים: {str(e)}")

# Main application logic
if not selected_currencies:
    st.warning("⚠️ אנא בחר לפחות מטבע מקור אחד")
elif not selected_base_currencies:
    st.warning("⚠️ אנא בחר לפחות מטבע בסיס אחד")
elif start_date > end_date:
    st.error("❌ תאריך התחלה חייב להיות לפני תאריך הסיום")
else:
    # Display instructions
    st.info("💡 בחר מטבעות ותאריכים בסרגל הצד, ולאחר מכן לחץ על 'הורד נתונים'")
    
    # Handle download button click
    if download_button:
        with st.spinner("מוריד נתונים מבנק ישראל..."):
            # Fetch data using the new SDMX API
            df_raw, error = fetch_exchange_rates(selected_currencies, start_date, end_date)
            
            if error:
                st.error(f"❌ {error}")
            elif df_raw is None or df_raw.empty:
                st.error("❌ לא התקבלו נתונים מבנק ישראל")
            else:
                st.success("✅ נתונים הורדו בהצלחה!")
                
                # Process the data
                with st.spinner("מעבד ומסנן נתונים..."):
                    df_processed, process_error = process_exchange_data(df_raw, selected_currencies, selected_base_currencies)
                
                if process_error:
                    st.error(f"❌ {process_error}")
                elif df_processed is None or df_processed.empty:
                    st.warning("⚠️ לא נמצאו נתונים המתאימים לקריטריונים שנבחרו")
                else:
                    st.success(f"✅ נמצאו {len(df_processed)} רשומות")
                    
                    # Display current rates
                    display_current_rates(df_processed, selected_currencies)
                    
                    # Display data preview
                    st.subheader("👀 תצוגה מקדימה של הנתונים")
                    st.dataframe(df_processed.head(10), use_container_width=True)
                    
                    # Prepare CSV for download
                    csv_data = df_processed.to_csv(index=False, encoding='utf-8-sig')
                    
                    # Create filename
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    currencies_str = "_".join(selected_currencies)
                    filename = f"exchange_rates_{currencies_str}_{timestamp}.csv"
                    
                    # Download button
                    st.download_button(
                        label="📥 הורד קובץ CSV",
                        data=csv_data,
                        file_name=filename,
                        mime="text/csv",
                        use_container_width=True,
                        type="primary"
                    )
                    
                    # Display summary
                    st.subheader("📈 סיכום")
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        st.metric("מספר רשומות", len(df_processed))
                    
                    with col2:
                        st.metric("מטבעות נבחרים", len(selected_currencies))
                    
                    with col3:
                        try:
                            date_range = pd.to_datetime(df_processed['Effective_Date'], format='%d/%m/%Y', errors='coerce')
                            days_range = (date_range.max() - date_range.min()).days + 1
                            st.metric("טווח ימים", days_range)
                        except:
                            st.metric("טווח ימים", "לא זמין")

# Footer
st.markdown("---")
st.markdown(
    """
    <div style='text-align: center; color: #666; font-size: 0.8em;'>
    נתונים מתקבלים מבנק ישראל | Bank of Israel Exchange Rates<br>
    © כל הזכויות שמורות ל <a href="https://www.linkedin.com/in/avichay-shani-aa478a34">Avichay Shani</a>, 2025
    </div>
    """,
    unsafe_allow_html=True
)

# Display available columns for debugging (only in development)
if st.sidebar.checkbox("🔍 הצג מידע טכני (לפיתוח)", value=False):
    st.sidebar.markdown("**מידע טכני יוצג לאחר הורדת נתונים**")

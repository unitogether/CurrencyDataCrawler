import streamlit as st
import pandas as pd
import requests
from io import BytesIO
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

# Currency selection
st.sidebar.subheader("בחירת מטבעות")
available_currencies = ["USD", "EUR", "GBP", "CHF", "JPY", "CAD", "AUD", "NOK", "SEK", "DKK"]
selected_currencies = st.sidebar.multiselect(
    "בחר מטבעות:",
    available_currencies,
    default=["USD", "EUR", "GBP"],
    help="בחר את המטבעות שברצונך לכלול בקובץ"
)

# Date range selection
st.sidebar.subheader("טווח תאריכים")
date_option = st.sidebar.radio(
    "בחר טווח תאריכים:",
    ["נתונים יומיים עדכניים", "טווח תאריכים מותאם אישית"],
    help="בחר אם להוריד נתונים יומיים או טווח תאריכים מסוים"
)

start_date = None
end_date = None

if date_option == "טווח תאריכים מותאם אישית":
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
def fetch_exchange_rates(rate_type="Daily", start_date=None, end_date=None):
    """
    Fetch exchange rates from Bank of Israel API
    """
    try:
        # Construct URL based on parameters
        if rate_type == "Daily":
            url = "https://www.boi.org.il/currency-api/ExRatesDownload?type=Daily"
        else:
            # For historical data, we might need to adjust the URL format
            url = "https://www.boi.org.il/currency-api/ExRatesDownload?type=Historical"
        
        # Make the request
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        
        # Read Excel data
        excel_data = BytesIO(response.content)
        df = pd.read_excel(excel_data)
        
        return df, None
    
    except requests.exceptions.RequestException as e:
        return None, f"שגיאה בחיבור לשרת בנק ישראל: {str(e)}"
    except Exception as e:
        return None, f"שגיאה בעיבוד הנתונים: {str(e)}"

def filter_and_process_data(df, selected_currencies, start_date=None, end_date=None):
    """
    Filter and process the exchange rates data
    """
    try:
        # Try different possible column names for currency
        currency_column = None
        possible_currency_columns = ['שם_מטבע', 'מטבע', 'Currency', 'CurrencyCode']
        
        for col in possible_currency_columns:
            if col in df.columns:
                currency_column = col
                break
        
        if currency_column is None:
            # If no standard column found, try to identify by content
            for col in df.columns:
                if df[col].dtype == 'object' and any(curr in df[col].astype(str).values for curr in ['USD', 'EUR', 'GBP']):
                    currency_column = col
                    break
        
        if currency_column is None:
            return None, "לא נמצא עמודת מטבע בנתונים"
        
        # Filter by selected currencies
        df_filtered = df[df[currency_column].isin(selected_currencies)]
        
        # Try to find date column
        date_column = None
        possible_date_columns = ['תאריך', 'Date', 'date', 'DATE']
        
        for col in possible_date_columns:
            if col in df.columns:
                date_column = col
                break
        
        if date_column and start_date and end_date:
            # Convert date column to datetime if it's not already
            df_filtered[date_column] = pd.to_datetime(df_filtered[date_column], errors='coerce')
            
            # Filter by date range
            start_datetime = pd.to_datetime(start_date)
            end_datetime = pd.to_datetime(end_date)
            
            df_filtered = df_filtered[
                (df_filtered[date_column] >= start_datetime) & 
                (df_filtered[date_column] <= end_datetime)
            ]
        
        # Sort by date and currency if possible
        if date_column:
            df_filtered = df_filtered.sort_values(by=[date_column, currency_column])
        else:
            df_filtered = df_filtered.sort_values(by=[currency_column])
        
        return df_filtered, None
    
    except Exception as e:
        return None, f"שגיאה בסינון הנתונים: {str(e)}"

def display_current_rates(df):
    """
    Display current exchange rates in a nice format
    """
    st.subheader("📊 שערי חליפין נוכחיים")
    
    try:
        # Try to find the rate column
        rate_column = None
        possible_rate_columns = ['שער', 'Rate', 'ExchangeRate', 'שער_חליפין']
        
        for col in possible_rate_columns:
            if col in df.columns:
                rate_column = col
                break
        
        if rate_column is None:
            # Look for numeric columns that might be rates
            numeric_columns = df.select_dtypes(include=['float64', 'int64']).columns
            if len(numeric_columns) > 0:
                rate_column = numeric_columns[0]
        
        if rate_column:
            # Get latest rates for each currency
            currency_column = None
            for col in ['שם_מטבע', 'מטבע', 'Currency', 'CurrencyCode']:
                if col in df.columns:
                    currency_column = col
                    break
            
            if currency_column:
                latest_rates = df.groupby(currency_column)[rate_column].last().reset_index()
                
                # Display in columns
                cols = st.columns(len(selected_currencies))
                for i, currency in enumerate(selected_currencies):
                    if i < len(cols):
                        with cols[i]:
                            rate_data = latest_rates[latest_rates[currency_column] == currency]
                            if not rate_data.empty:
                                rate = rate_data[rate_column].iloc[0]
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
    st.warning("⚠️ אנא בחר לפחות מטבע אחד")
else:
    # Display instructions
    st.info("💡 בחר מטבעות ופרמטרים בסרגל הצד, ולאחר מכן לחץ על 'הורד נתונים'")
    
    # Handle download button click
    if download_button:
        with st.spinner("מוריד נתונים מבנק ישראל..."):
            # Determine rate type based on date selection
            rate_type = "Daily" if date_option == "נתונים יומיים עדכניים" else "Historical"
            
            # Fetch data
            df, error = fetch_exchange_rates(rate_type, start_date, end_date)
            
            if error:
                st.error(f"❌ {error}")
            elif df is None or df.empty:
                st.error("❌ לא התקבלו נתונים מבנק ישראל")
            else:
                st.success("✅ נתונים הורדו בהצלחה!")
                
                # Display current rates
                display_current_rates(df)
                
                # Filter and process data
                with st.spinner("מעבד ומסנן נתונים..."):
                    df_filtered, filter_error = filter_and_process_data(
                        df, selected_currencies, start_date, end_date
                    )
                
                if filter_error:
                    st.error(f"❌ {filter_error}")
                elif df_filtered is None or df_filtered.empty:
                    st.warning("⚠️ לא נמצאו נתונים המתאימים לקריטריונים שנבחרו")
                else:
                    st.success(f"✅ נמצאו {len(df_filtered)} רשומות")
                    
                    # Display data preview
                    st.subheader("👀 תצוגה מקדימה של הנתונים")
                    st.dataframe(df_filtered.head(10), use_container_width=True)
                    
                    # Prepare CSV for download
                    csv_data = df_filtered.to_csv(index=False, encoding='utf-8-sig')
                    
                    # Create filename
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = f"exchange_rates_{timestamp}.csv"
                    
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
                        st.metric("מספר רשומות", len(df_filtered))
                    
                    with col2:
                        st.metric("מטבעות נבחרים", len(selected_currencies))
                    
                    with col3:
                        if 'תאריך' in df_filtered.columns or 'Date' in df_filtered.columns:
                            date_col = 'תאריך' if 'תאריך' in df_filtered.columns else 'Date'
                            try:
                                date_range = pd.to_datetime(df_filtered[date_col], errors='coerce')
                                days_range = (date_range.max() - date_range.min()).days + 1
                                st.metric("טווח ימים", days_range)
                            except:
                                st.metric("טווח ימים", "לא זמין")
                        else:
                            st.metric("טווח ימים", "לא זמין")

# Footer
st.markdown("---")
st.markdown(
    """
    <div style='text-align: center; color: #666; font-size: 0.8em;'>
    נתונים מתקבלים מבנק ישראל | Bank of Israel Exchange Rates
    </div>
    """,
    unsafe_allow_html=True
)

# Display available columns for debugging (only in development)
if st.sidebar.checkbox("🔍 הצג מידע טכני (לפיתוח)", value=False):
    if 'df' in locals() and df is not None:
        st.sidebar.subheader("עמודות זמינות בנתונים:")
        st.sidebar.write(list(df.columns))
        st.sidebar.subheader("דוגמת נתונים:")
        st.sidebar.write(df.head(2))

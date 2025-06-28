# replit.md

## Overview

This is a Streamlit web application for downloading and displaying currency exchange rates from the Bank of Israel (בנק ישראל). The application provides a Hebrew-language interface for users to select currencies and date ranges, then retrieve exchange rate data from the Bank of Israel's API.

## System Architecture

### Frontend Architecture
- **Framework**: Streamlit - Python-based web framework for data applications
- **Language**: Hebrew interface with RTL (Right-to-Left) support
- **Layout**: Wide layout configuration with sidebar for filters and main area for data display
- **Components**: 
  - Multi-select currency picker
  - Date range selector with radio button options
  - Data visualization and download capabilities

### Backend Architecture
- **Runtime**: Python application
- **Data Processing**: Pandas for data manipulation
- **HTTP Client**: Requests library for API calls
- **File Handling**: BytesIO for in-memory file operations

### Key Design Decisions
- **Streamlit Choice**: Selected for rapid prototyping and built-in data visualization capabilities
- **Hebrew Localization**: Full Hebrew interface to serve Israeli users
- **Sidebar Layout**: Filters placed in sidebar for clean separation of controls and data display
- **Multi-currency Support**: Supports 10 major currencies (USD, EUR, GBP, CHF, JPY, CAD, AUD, NOK, SEK, DKK)

## Key Components

### 1. Page Configuration
- Sets Hebrew title and currency exchange icon
- Configures wide layout for better data presentation

### 2. Currency Filter System
- Multi-select widget for currency selection
- Default selection of USD, EUR, GBP for common use cases
- Extensible list of supported currencies

### 3. Date Range Management
- Two modes: Daily current data vs. custom date range
- Date input widgets with default 30-day lookback period
- Flexible date handling for different user needs

### 4. Data Processing Pipeline
- Integration with Bank of Israel API
- Pandas-based data manipulation
- Excel file generation for data export

## Data Flow

1. **User Input**: User selects currencies and date range via sidebar controls
2. **API Request**: Application calls Bank of Israel exchange rate API
3. **Data Processing**: Raw API response processed using Pandas
4. **Data Display**: Processed data displayed in Streamlit interface
5. **Export Option**: Users can download data as Excel files

## External Dependencies

### Core Libraries
- **streamlit**: Web application framework
- **pandas**: Data manipulation and analysis
- **requests**: HTTP library for API calls
- **datetime**: Date and time handling

### Data Source
- **Bank of Israel API**: Primary source for exchange rate data
- Real-time and historical exchange rate information

## Deployment Strategy

### Local Development
- Standard Python environment with pip-installed dependencies
- Streamlit's built-in development server

### Production Considerations
- Can be deployed on Streamlit Cloud, Heroku, or similar platforms
- Requires Python 3.7+ environment
- No database dependencies - stateless application architecture

## User Preferences

Preferred communication style: Simple, everyday language.

## Recent Changes

- June 28, 2025: Updated to use Bank of Israel SDMX API for reliable CSV data
- June 28, 2025: Restructured data format with Base_Currency and Source_Currency columns
- June 28, 2025: Added support for both ILS and USD as base currencies
- June 28, 2025: Implemented proper date formatting (DD/MM/YYYY) and sorting
- June 28, 2025: Added Base Currency selection with ILS and USD defaults

## Changelog

- June 28, 2025: Initial setup
- June 28, 2025: Enhanced with SDMX API integration and improved data structure